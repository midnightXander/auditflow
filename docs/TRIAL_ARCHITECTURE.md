# Trial Management - Architecture & Flow Diagrams

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (React/Next.js)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │  Pricing Page    │  │ Billing Settings │  │  Trial Badge     │      │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤      │
│  │ Start Trial      │  │ Trial Status     │  │ Days Remaining   │      │
│  │ Upgrade to Pro   │  │ Subscription Mgr │  │ Expiration Date  │      │
│  │ Upgrade to Agcy  │  │ Cancel Sub       │  │ Active Status    │      │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
│           │                     │                      │                │
└───────────┼─────────────────────┼──────────────────────┼────────────────┘
            │                     │                      │
            └─────────────────────┴──────────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │   FastAPI Backend (8000)  │
                    └─────────────┬─────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
   ┌────▼──────────┐      ┌──────▼────────┐      ┌────────▼──────┐
   │ Trial Endpoints│      │ Auth & User   │      │ Whop Payment  │
   ├────────────────┤      ├───────────────┤      ├───────────────┤
   │ POST /start    │      │ JWT tokens    │      │ Checkout link │
   │ GET /status    │      │ Current user  │      │ Webhooks      │
   │ GET /offer     │      │ Credits       │      │ Subscriptions │
   └────┬───────────┘      └───┬───────────┘      └────┬──────────┘
        │                      │                       │
        │  ┌──────────────┐    │    ┌─────────────┐   │
        └─▶│   Services   │    │    │ Database    │◀──┘
           │ whop_service │◀───┴───▶│ (SQLAlchemy)│
           └──────┬───────┘         └─────────────┘
                  │
        ┌─────────┼─────────┐
        │         │         │
   ┌────▼────┐ ┌─▼─────┐ ┌─▼────────┐
   │ Trial   │ │ Email │ │ Payments │
   │ Logic   │ │ Queue │ │ (Whop)   │
   └─────────┘ └───────┘ └──────────┘
```

---

## User Trial Journey

```
┌─ START
│
├─ User visits pricing page
│  ├─ Frontend calls: GET /api/billing/trial-status
│  ├─ Backend checks if trial already used
│  └─ Display "Start 14-Day Trial" button or current status
│
├─ User clicks "Start 14-Day Trial"
│  ├─ Frontend calls: POST /api/billing/start-trial
│  ├─ Backend validation:
│  │  ├─ Check user exists ✓
│  │  ├─ Check not already in trial ✓
│  │  ├─ Check trial not already used ✓
│  │  └─ Create trial record
│  ├─ Backend updates User:
│  │  ├─ trial_started_at = NOW
│  │  ├─ trial_ends_at = NOW + 14 days
│  │  ├─ trial_used = true
│  │  ├─ subscription_status = "trial"
│  │  ├─ plan = "pro"
│  │  └─ credits_remaining = 10,000
│  ├─ Background job sends email (Day 0):
│  │  └─ "Welcome to your 14-day trial!"
│  └─ Frontend shows: "Trial Active - 14 days remaining"
│
├─ Days 1-2: User explores features, runs audits
│  └─ Credits decrease as audits are run
│
├─ Day 3:
│  ├─ Scheduled task: send_trial_email_reminders()
│  ├─ Check: trial_email_sent_day3 = false
│  ├─ Send email: "Explore these features!"
│  └─ Update: trial_email_sent_day3 = true
│
├─ Days 4-9: User continues using trial
│  └─ Frontend shows trial countdown
│
├─ Day 10:
│  ├─ Scheduled task: send_trial_email_reminders()
│  ├─ Check: trial_email_sent_day10 = false
│  ├─ Send email: "4 days left! Here's what you'll get with Pro..."
│  └─ Update: trial_email_sent_day10 = true
│
├─ Days 11-12: User sees trial expiring
│  ├─ Frontend shows countdown timer
│  ├─ Displays upgrade options
│  └─ Shows regular pricing ($29/month)
│
├─ Day 13:
│  ├─ Scheduled task: send_trial_email_reminders()
│  ├─ Check: trial_email_sent_expiring_soon = false
│  ├─ Send email: "🎁 EXPIRING SOON! Get 30% OFF ($20 instead of $29)"
│  └─ Update: trial_email_sent_expiring_soon = true
│
├─ Day 14: TRIAL EXPIRES
│  ├─ Scheduled task: handle_trial_expirations()
│  ├─ Check: trial_ends_at < NOW
│  ├─ Backend updates User:
│  │  ├─ plan = "free"
│  │  ├─ subscription_status = "expired"
│  │  ├─ credits_remaining = 20
│  │  └─ Trial fields remain populated (audit trail)
│  ├─ Send email: "Your trial ended. Upgrade now with 30% off!"
│  └─ Frontend shows: "Trial Ended - Upgrade Now"
│
├─ Days 14-17: DISCOUNT WINDOW (30% off)
│  ├─ Frontend calls: GET /api/billing/trial-upgrade-offer
│  ├─ Backend checks:
│  │  ├─ subscription_status = "expired" ✓
│  │  ├─ (NOW - trial_ends_at).days <= 3 ✓
│  │  └─ Return: offer_active=true, discount=30%, price=$20
│  └─ Display: "🎉 Limited offer: $20/month (30% OFF)"
│
├─ User clicks "Upgrade Now" (within 3 days)
│  ├─ Frontend calls: POST /api/billing/checkout-link
│  ├─ Backend creates Whop checkout link
│  └─ User redirected to Whop checkout
│
├─ User completes payment on Whop
│  ├─ Whop sends webhook: order.completed
│  ├─ Backend processes webhook:
│  │  ├─ Find user by email
│  │  ├─ Update plan = "pro"
│  │  ├─ subscription_status = "active"
│  │  ├─ credits_remaining = 10,000
│  │  └─ Store subscription metadata
│  └─ User now has active Pro subscription
│
└─ END: User has paid Pro subscription
```

---

## Trial State Machine

```
                    ┌──────────────────┐
                    │  Never Trialed   │
                    │ (trial_used=false)│
                    └────────┬──────────┘
                             │
                             │ [start_trial()]
                             ▼
                    ┌──────────────────┐
                    │  Trial Active    │
                    │ (14 days remain) │
                    │ [DAY 0 - 13]     │
                    └────────┬──────────┘
                             │
                             │ [After 14 days]
                             │ [handle_trial_expiration()]
                             ▼
                    ┌──────────────────┐
                    │  Trial Expired   │
                    │ (reverted to free)│
                    │ [DAY 14 - 17]    │
                    └────────┬──────────┘
                             │
                ┌────────────┴──────────────┐
                │                           │
       ┌────────▼─────────┐      ┌──────────▼──────────┐
       │  Upgrade (w/o    │      │  No Upgrade        │
       │  discount)       │      │  (Offer expired)   │
       │  [DAY 17+]       │      │  [DAY 17+]         │
       └────────┬─────────┘      └──────────┬──────────┘
                │                           │
       ┌────────▼─────────┐      ┌──────────▼──────────┐
       │ Paid Subscription│      │  Free Plan Forever  │
       │ (Pro/Agency)     │      │  (20 credits/month) │
       └──────────────────┘      └─────────────────────┘
```

---

## Email Timeline

```
Timeline:                          Day 0     Day 3    Day 10   Day 13   Day 14+
                                    │         │        │        │        │
Trial Status:        Never → Active → Active → Active → Active → Expired → Offer
                                    │         │        │        │        │
Email Reminders:                    │         │        │        │        │
                                    ▼         ▼        ▼        ▼        ▼
Email 0 (Start):     ────────────→ ✓         -        -        -        -
                     "Welcome!"

Email 1 (Day 3):     ─────────────────────→ ✓        -        -        -
                     "Explore Features"

Email 2 (Day 10):    ──────────────────────────────→ ✓        -        -
                     "10 Days Used, 4 Left"

Email 3 (Expiring):  ───────────────────────────────────────→ ✓        -
                     "Expiring Soon - 30% OFF!"

Email 4 (Expired):   ────────────────────────────────────────────────→ ✓
                     "Trial Ended - Upgrade Now"
```

---

## Database Schema

```
┌─────────────────────────────────────────────────────────┐
│                      users TABLE                         │
├─────────────────────────────────────────────────────────┤
│ id                          [INTEGER, PRIMARY KEY]       │
│ email                       [VARCHAR, UNIQUE]            │
│ plan                        [VARCHAR] ← "free", "pro"   │
│ subscription_status         [VARCHAR] ← "trial", "active"
│ credits_remaining           [INTEGER] ← 10000 for trial │
│                                                           │
│ ┌─ TRIAL FIELDS ────────────────────────────────────┐   │
│ │ trial_started_at         [DateTime, nullable]     │   │
│ │ trial_ends_at            [DateTime, nullable]     │   │
│ │ trial_used               [Boolean] = False        │   │
│ │ trial_plan               [VARCHAR] = "pro"        │   │
│ │                                                    │   │
│ │ Email Tracking:                                  │   │
│ │ trial_email_sent_start   [Boolean] = False       │   │
│ │ trial_email_sent_day3    [Boolean] = False       │   │
│ │ trial_email_sent_day10   [Boolean] = False       │   │
│ │ trial_email_sent_expiring_soon [Boolean] = False │   │
│ └────────────────────────────────────────────────────┘   │
│                                                           │
│ subscription_started_at     [DateTime, nullable]         │
│ subscription_renews_at      [DateTime, nullable]         │
│ whop_subscription_id        [VARCHAR, UNIQUE]            │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## API Call Flow

### Starting a Trial

```
┌─────────────────┐
│   Frontend      │
│  (React/Vue)    │
└────────┬────────┘
         │
         │ POST /api/billing/start-trial
         │ Headers: { Authorization: Bearer <token> }
         │ Body: {}
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│             FastAPI Backend (api.py)                    │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  @app.post("/api/billing/start-trial")                 │
│  async def start_trial_endpoint(                        │
│      current_user = get_current_user(),                │
│      db = get_db()                                      │
│  ):                                                      │
│      ├─ Call whop_service.start_free_trial()           │
│      ├─ Returns (success, message, trial_ends_at)      │
│      └─ Return StartTrialResponse                      │
│                                                           │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│        whop_service.start_free_trial()                  │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  1. Validate:                                           │
│     ├─ user exists?                                    │
│     ├─ trial_used != true?                             │
│     └─ not already in active trial?                    │
│                                                           │
│  2. Set trial dates:                                    │
│     ├─ trial_started_at = NOW                          │
│     ├─ trial_ends_at = NOW + 14 days                   │
│                                                           │
│  3. Update user:                                        │
│     ├─ trial_used = true                               │
│     ├─ trial_plan = "pro"                              │
│     ├─ plan = "pro"                                    │
│     ├─ subscription_status = "trial"                   │
│     ├─ credits_remaining = 10000                       │
│     └─ db.commit()                                     │
│                                                           │
│  4. Return (True, message, trial_ends_at)             │
│                                                           │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│        Background Job (send email)                      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Triggered immediately or via scheduled task:          │
│  ├─ Get user from database                             │
│  ├─ Check trial_email_sent_start == false              │
│  ├─ Send email: "Welcome to your trial!"               │
│  ├─ Update trial_email_sent_start = true               │
│  └─ Log in email queue                                 │
│                                                           │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│          Response to Frontend                           │
├─────────────────────────────────────────────────────────┤
│                                                           │
│ {                                                        │
│   "success": true,                                      │
│   "message": "14-day Pro trial started!...",           │
│   "trial_ends_at": "2024-05-15T10:00:00",             │
│   "credits_granted": 10000                             │
│ }                                                        │
│                                                           │
│ Status: 200 OK                                          │
│                                                           │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│        Frontend Updates UI                              │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ├─ Show success alert                                  │
│  ├─ Disable "Start Trial" button                        │
│  ├─ Show trial countdown: "14 days left"               │
│  ├─ Display: "Trial Active" badge                      │
│  └─ Refresh user context                               │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## Discount Offer Logic

```
IF (
    subscription_status == "expired" AND
    trial_ends_at EXISTS AND
    (NOW - trial_ends_at).days <= 3
)
THEN
    offer_active = true
    discount_percent = 30
    original_price = 29
    discounted_price = int(29 * 0.7) = 20
    offer_expires_at = trial_ends_at + 3 days
ELSE
    offer_active = false
    discount_percent = 0
    discounted_price = 29
END IF
```

---

## Scheduled Tasks

```
┌─────────────────────────────────────────────────────────┐
│        Task 1: Daily at 9 AM                            │
│        send_trial_email_reminders()                     │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  FOR EACH user WHERE subscription_status = "trial":    │
│      │                                                   │
│      └─ reminders = get_trial_email_reminders(user)    │
│         │                                                │
│         ├─ IF reminders["should_send_start"]:          │
│         │  └─ send_trial_start_email()                 │
│         │     mark_trial_email_sent(..., "start")      │
│         │                                                │
│         ├─ IF reminders["should_send_day3"]:           │
│         │  └─ send_trial_day3_email()                  │
│         │     mark_trial_email_sent(..., "day3")       │
│         │                                                │
│         ├─ IF reminders["should_send_day10"]:          │
│         │  └─ send_trial_day10_email()                 │
│         │     mark_trial_email_sent(..., "day10")      │
│         │                                                │
│         └─ IF reminders["should_send_expiring_soon"]:  │
│            └─ send_trial_expiring_email()              │
│               mark_trial_email_sent(..., "expiring")   │
│                                                           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│        Task 2: Daily at Midnight                        │
│        handle_trial_expirations()                       │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  FOR EACH user WHERE:                                  │
│      subscription_status = "trial" AND                 │
│      trial_ends_at <= NOW                              │
│  DO:                                                    │
│      │                                                   │
│      ├─ user.plan = "free"                             │
│      ├─ user.subscription_status = "expired"           │
│      ├─ user.credits_remaining = 20                    │
│      ├─ db.commit()                                    │
│      │                                                   │
│      └─ send_trial_expired_email(user)                 │
│                                                           │
│  ✓ User automatically reverted to free plan           │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## Error Handling

```
POST /api/billing/start-trial
│
├─ [400] "You have already used your free trial"
│  Condition: trial_used == true
│
├─ [400] "You are already in a trial with X days remaining"
│  Condition: trial_active == true
│
├─ [401] "Not authenticated"
│  Condition: No valid JWT token
│
└─ [500] Internal error (log exception)
   Condition: Database or other error
```

---

## Summary

This architecture provides:

✅ **Clean separation of concerns** - Frontend, Backend, Service Layer
✅ **Robust state tracking** - 8 database fields for audit trail
✅ **Automated processes** - Scheduled email and expiration tasks
✅ **User-friendly UX** - Clear countdown, discount offers, email reminders
✅ **Easy integration** - Simple API endpoints, well-documented
✅ **Scalable design** - Can handle thousands of concurrent trials
✅ **Error recovery** - Handles edge cases gracefully
