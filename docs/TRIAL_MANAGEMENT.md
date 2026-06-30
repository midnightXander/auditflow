# Free Trial Management - Complete Implementation Guide

## Overview

The system now supports a **14-day free trial of the Pro plan** with the following features:

✅ **Trial Features:**
- 14-day free access to Pro plan (10,000 credits)
- One trial per user account
- Automatic reversion to Free plan after expiration
- 30% discount offer if user upgrades within 3 days of trial end
- Automated email reminders at day 0, day 3, day 10, and day 13

✅ **User Journey:**
1. User starts trial → gets 10,000 credits for 14 days
2. Day 3: Reminder email to explore features
3. Day 10: Second reminder to start upgrading
4. Day 13: Final "expiring soon" email with discount offer
5. Day 14: Trial expires, user reverts to Free (20 credits)
6. Days 14-17: Can upgrade with 30% discount
7. Day 17+: Discount offer expires, regular pricing applies

---

## Database Schema

### New User Fields (in `db/models.py`)

```python
# Free Trial Management (14-day Pro trial)
trial_started_at: DateTime, nullable     # When trial began
trial_ends_at: DateTime, nullable        # When trial expires (14 days from start)
trial_used: Boolean, default=False       # Has user already used their trial?
trial_plan: String, nullable             # "pro" - the only plan with trial
trial_email_sent_start: Boolean          # Trial start email sent
trial_email_sent_day3: Boolean           # Day 3 reminder sent
trial_email_sent_day10: Boolean          # Day 10 reminder sent
trial_email_sent_expiring_soon: Boolean  # Expiring soon (day 13) sent
```

---

## API Endpoints

### 1. Start Free Trial

**Endpoint:** `POST /api/billing/start-trial`

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{}
```

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "14-day Pro trial started! You now have 10,000 credits.",
  "trial_ends_at": "2024-05-15T10:23:45.123456",
  "credits_granted": 10000
}
```

**Response (Error - 400):**
```json
{
  "detail": "You have already used your free trial"
}
```

**Error Cases:**
- User already used trial → `400 Bad Request`
- User already in active trial → `400 Bad Request` (returns days remaining)
- Invalid user → `401 Unauthorized`

**Example (cURL):**
```bash
curl -X POST http://localhost:8000/api/billing/start-trial \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Example (Frontend/JavaScript):**
```javascript
const response = await fetch(`${API_URL}/api/billing/start-trial`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  }
});

const data = await response.json();
if (data.success) {
  console.log(`Trial starts today, expires: ${data.trial_ends_at}`);
  console.log(`You have ${data.credits_granted} credits`);
}
```

---

### 2. Get Trial Status

**Endpoint:** `GET /api/billing/trial-status`

**Authentication:** Required (Bearer token)

**Response (200):**
```json
{
  "trial_active": true,
  "trial_started_at": "2024-05-01T10:23:45.123456",
  "trial_ends_at": "2024-05-15T10:23:45.123456",
  "trial_used": true,
  "days_remaining": 10,
  "plan": "pro",
  "credits_remaining": 9500
}
```

**Possible States:**
- `trial_active: true` - User is currently in trial
- `trial_active: false, trial_used: true` - Trial expired, user used it before
- `trial_active: false, trial_used: false` - User never started trial

**Example (Frontend):**
```javascript
const response = await fetch(`${API_URL}/api/billing/trial-status`, {
  headers: { 'Authorization': `Bearer ${accessToken}` }
});

const trial = await response.json();

if (trial.trial_active) {
  console.log(`${trial.days_remaining} days left in trial`);
  console.log(`Expires: ${trial.trial_ends_at}`);
} else if (!trial.trial_used) {
  // Show "Start Free Trial" button
  console.log("User can start trial");
} else {
  // Show "Upgrade to Pro" button
  console.log("User already used trial");
}
```

---

### 3. Get Trial Upgrade Offer

**Endpoint:** `GET /api/billing/trial-upgrade-offer`

**Authentication:** Required (Bearer token)

**Response (Trial Active - 200):**
```json
{
  "trial_expired": false,
  "offer_active": false,
  "discount_percent": 0,
  "offer_expires_at": null,
  "plan_tier": "pro",
  "discounted_price": 29,
  "original_price": 29
}
```

**Response (Trial Expired Within 3 Days - 200):**
```json
{
  "trial_expired": true,
  "offer_active": true,
  "discount_percent": 30,
  "offer_expires_at": "2024-05-18T10:23:45.123456",
  "plan_tier": "pro",
  "discounted_price": 20,
  "original_price": 29
}
```

**Response (Trial Expired, Offer Expired - 200):**
```json
{
  "trial_expired": true,
  "offer_active": false,
  "discount_percent": 0,
  "offer_expires_at": null,
  "plan_tier": "pro",
  "discounted_price": 29,
  "original_price": 29
}
```

**Example (Frontend):**
```javascript
const response = await fetch(`${API_URL}/api/billing/trial-upgrade-offer`, {
  headers: { 'Authorization': `Bearer ${accessToken}` }
});

const offer = await response.json();

if (offer.offer_active) {
  console.log(`🎉 ${offer.discount_percent}% OFF! Upgrade now`);
  console.log(`${offer.discounted_price} (was ${offer.original_price})`);
  console.log(`Offer expires: ${offer.offer_expires_at}`);
} else if (offer.trial_expired) {
  console.log("Trial ended. Upgrade to continue.");
}
```

---

## Trial Logic Flow

### Timeline

```
Day 0:   Trial starts
         - Email: "Trial Started" + features overview
         - User gets 10,000 credits
         - Plan changes to "pro"
         - subscription_status = "trial"

Day 3:   
         - Email: "Explore features" + usage tips
         - Only sent if user hasn't used many credits

Day 10:  
         - Email: "10% left!" + upgrade info
         - Show comparison of plans

Day 13:  
         - Email: "EXPIRING SOON" + 30% discount offer
         - Countdown timer: 1 day left

Day 14:  Trial expires
         - Plan reverts to "free"
         - subscription_status = "expired"
         - Credits reset to 20
         - Discount offer becomes active

Days 14-17:
         - User can upgrade with 30% discount
         - Offer is active via /api/billing/trial-upgrade-offer

Day 17+: Discount offer expires
         - Regular pricing applies
         - User can still upgrade anytime
```

### State Machine

```
[No Trial] 
    ↓ (start_trial)
[Active Trial] ← User can perform audits with 10k credits
    ↓ (day 14 passed)
[Expired Trial] ← User reverts to Free plan, 30% discount active
    ↓ (3 days passed)
[Regular Free Plan] ← Standard pricing applies
    ↓ (upgrade)
[Paid Plan] ← Active subscription
```

---

## Trial Service Functions

All trial functions are in `services/whop_service.py`:

### `start_free_trial(user_id: int, db: Session) → tuple[bool, str, Optional[datetime]]`

Starts a 14-day trial for a user.

```python
success, message, trial_end = await whop_service.start_free_trial(
    user_id=1,
    db=db
)

if success:
    print(f"Trial ends: {trial_end}")
else:
    print(f"Error: {message}")
```

**Returns:**
- `success: bool` - Whether trial was started
- `message: str` - Success or error message
- `trial_end: datetime` - When trial expires (None if error)

**Validations:**
- ✅ User exists
- ✅ User hasn't already used trial
- ✅ User isn't already in active trial

---

### `get_trial_status(user: User) → Dict[str, Any]`

Get current trial status without database queries.

```python
status = whop_service.get_trial_status(current_user)

print(f"Trial Active: {status['trial_active']}")
print(f"Days Remaining: {status['days_remaining']}")
print(f"Expires: {status['trial_ends_at']}")
```

**Returns:**
```python
{
    "trial_active": bool,
    "trial_started_at": datetime,
    "trial_ends_at": datetime,
    "trial_used": bool,
    "days_remaining": int,
    "plan": str,
    "credits_remaining": int
}
```

---

### `handle_trial_expiration(user_id: int, db: Session) → bool`

Revert user from trial to free plan. Call via background task.

```python
success = await whop_service.handle_trial_expiration(user_id=1, db=db)
if success:
    print("Trial expired, user reverted to free plan")
```

---

### `get_trial_email_reminders(user: User) → Dict[str, bool]`

Determine which reminder emails should be sent.

```python
reminders = whop_service.get_trial_email_reminders(current_user)

if reminders["should_send_day3"]:
    send_email_reminder_day3(current_user.email)
    
if reminders["should_send_expiring_soon"]:
    send_email_reminder_expiring(current_user.email)
```

**Returns:**
```python
{
    "should_send_start": bool,           # Day 0
    "should_send_day3": bool,            # Day 3
    "should_send_day10": bool,           # Day 10
    "should_send_expiring_soon": bool    # Day 13
}
```

---

### `mark_trial_email_sent(user_id: int, email_type: str, db: Session) → bool`

Mark email as sent to prevent duplicates.

```python
# After sending start email
whop_service.mark_trial_email_sent(
    user_id=1,
    email_type="start",  # "start", "day3", "day10", "expiring_soon"
    db=db
)
```

---

### `get_trial_upgrade_offer(user: User) → Dict[str, Any]`

Get 30% discount offer after trial expires.

```python
offer = whop_service.get_trial_upgrade_offer(current_user)

if offer["offer_active"]:
    print(f"Get {offer['discount_percent']}% OFF!")
    print(f"${offer['discounted_price']} (was ${offer['original_price']})")
```

**Returns:**
```python
{
    "trial_expired": bool,
    "offer_active": bool,
    "discount_percent": int,
    "offer_expires_at": datetime,
    "plan_tier": str,
    "discounted_price": int,
    "original_price": int
}
```

---

### `upgrade_from_trial(user_id: int, plan_tier: str, db: Session) → bool`

Upgrade from trial to paid plan.

```python
success = await whop_service.upgrade_from_trial(
    user_id=1,
    plan_tier="pro",  # or "agency"
    db=db
)
```

---

## Frontend Integration

### Pricing Page

```jsx
import { useState, useEffect } from 'react';

export function PricingPage() {
  const [trialStatus, setTrialStatus] = useState(null);
  const [offer, setOffer] = useState(null);

  useEffect(() => {
    // Check trial status
    fetch(`${API_URL}/api/billing/trial-status`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(data => setTrialStatus(data));

    // Check upgrade offer
    fetch(`${API_URL}/api/billing/trial-upgrade-offer`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(data => setOffer(data));
  }, []);

  async function startTrial() {
    const response = await fetch(`${API_URL}/api/billing/start-trial`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (response.ok) {
      const data = await response.json();
      alert(`Trial started! Expires ${data.trial_ends_at}`);
      window.location.reload();
    } else {
      const error = await response.json();
      alert(`Error: ${error.detail}`);
    }
  }

  return (
    <div className="pricing">
      {/* Free Plan */}
      <div className="plan">
        <h3>Free Plan</h3>
        <p>$0 / month</p>
        <p>20 credits/month</p>
      </div>

      {/* Pro Plan */}
      <div className="plan highlight">
        <h3>Pro Plan</h3>
        <p>$29 / month</p>
        <p>10,000 credits</p>
        
        {/* Show appropriate button based on trial status */}
        {!trialStatus?.trial_used && !trialStatus?.trial_active && (
          <button onClick={startTrial} className="btn-primary">
            Start 14-Day Free Trial
          </button>
        )}
        
        {trialStatus?.trial_active && (
          <button disabled className="btn-success">
            ✓ Trial Active ({trialStatus.days_remaining} days)
          </button>
        )}
        
        {offer?.offer_active && (
          <button onClick={() => handleCheckout('pro')} className="btn-primary">
            🎉 ${offer.discounted_price} - 30% OFF! (Expires soon)
          </button>
        )}
        
        {trialStatus?.trial_used && !offer?.offer_active && (
          <button onClick={() => handleCheckout('pro')} className="btn-primary">
            Upgrade Now - $29/month
          </button>
        )}
      </div>

      {/* Agency Plan */}
      <div className="plan">
        <h3>Agency Plan</h3>
        <p>$99 / month</p>
        <p>50,000 credits</p>
        <button onClick={() => handleCheckout('agency')} className="btn-primary">
          Upgrade Now
        </button>
      </div>
    </div>
  );
}
```

---

### Billing Settings

```jsx
export function BillingSettings() {
  const [trial, setTrial] = useState(null);
  const [subscription, setSubscription] = useState(null);

  useEffect(() => {
    Promise.all([
      fetch(`${API_URL}/api/billing/trial-status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      }).then(r => r.json()).then(setTrial),
      
      fetch(`${API_URL}/api/billing/subscription`, {
        headers: { 'Authorization': `Bearer ${token}` }
      }).then(r => r.json()).then(setSubscription)
    ]);
  }, []);

  if (trial?.trial_active) {
    return (
      <div className="trial-active">
        <h3>🎉 Free Trial Active</h3>
        <p>Plan: <strong>{trial.plan}</strong></p>
        <p>Credits: <strong>{trial.credits_remaining}</strong></p>
        <p>Expires: <strong>{formatDate(trial.trial_ends_at)}</strong></p>
        <p>Days Remaining: <strong>{trial.days_remaining}</strong></p>
        
        <button onClick={() => handleUpgrade('agency')}>
          Upgrade to Agency Plan
        </button>
      </div>
    );
  }

  if (subscription?.subscription_status === 'active') {
    return (
      <div className="subscription-active">
        <h3>Active Subscription</h3>
        <p>Plan: <strong>{subscription.plan}</strong></p>
        <p>Credits: <strong>{subscription.credits_remaining}</strong></p>
        <p>Renews: <strong>{formatDate(subscription.subscription_renews_at)}</strong></p>
        
        <button onClick={cancelSubscription}>
          Cancel Subscription
        </button>
      </div>
    );
  }

  return (
    <div className="no-subscription">
      <p>No active subscription or trial</p>
      <button onClick={() => navigate('/pricing')}>
        View Plans
      </button>
    </div>
  );
}
```

---

## Background Tasks (Recommended)

### Trial Email Reminders (Daily)

Run this task daily via cron or APScheduler:

```python
# In tasks.py or scheduled task file
async def send_trial_reminders():
    """Send trial reminder emails daily"""
    users = db.query(User).filter(
        User.subscription_status == "trial"
    ).all()
    
    for user in users:
        reminders = whop_service.get_trial_email_reminders(user)
        
        # Send start email
        if reminders["should_send_start"]:
            send_trial_start_email(user)
            whop_service.mark_trial_email_sent(user.id, "start", db)
        
        # Send day 3 email
        if reminders["should_send_day3"]:
            send_trial_day3_email(user)
            whop_service.mark_trial_email_sent(user.id, "day3", db)
        
        # Send day 10 email
        if reminders["should_send_day10"]:
            send_trial_day10_email(user)
            whop_service.mark_trial_email_sent(user.id, "day10", db)
        
        # Send expiring soon email
        if reminders["should_send_expiring_soon"]:
            send_trial_expiring_email(user)
            whop_service.mark_trial_email_sent(user.id, "expiring_soon", db)
```

### Trial Expiration Handler (Daily)

```python
# In tasks.py or scheduled task file
async def handle_trial_expirations():
    """Revert users from trial to free plan if expired"""
    users = db.query(User).filter(
        User.subscription_status == "trial",
        User.trial_ends_at <= datetime.utcnow()
    ).all()
    
    for user in users:
        await whop_service.handle_trial_expiration(user.id, db)
        send_trial_expired_email(user)  # Send "trial ended" email
```

---

## Testing

### Manual Test Flow

1. **Create test account** and register
2. **Start trial:**
   ```bash
   curl -X POST http://localhost:8000/api/billing/start-trial \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```
3. **Check trial status:**
   ```bash
   curl http://localhost:8000/api/billing/trial-status \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```
4. **Verify credits (10,000)**
5. **Run audit** to consume some credits
6. **Check remaining credits**
7. **Try starting trial again** (should fail)
8. **Check upgrade offer** (should be inactive)

### Edge Cases to Test

- ✅ User tries to start trial twice → Error
- ✅ User tries to start trial while in active trial → Error with days remaining
- ✅ Trial expires after 14 days → Reverts to Free
- ✅ Trial expired, try to upgrade → Gets 30% discount
- ✅ Trial expired 4+ days ago → Discount expires, regular price
- ✅ User upgrades from trial → Goes to paid plan
- ✅ Trial credits are spent → User can still run audits? (depends on requirements)

---

## Configuration

### Environment Variables

No new environment variables needed! Uses existing:
- `WHOP_API_KEY` - For upgrade process
- `WHOP_PRO_PRODUCT_ID` - For upgrade to Pro
- `WHOP_AGENCY_PRODUCT_ID` - For upgrade to Agency

### Constants (in `services/whop_service.py`)

```python
TRIAL_DAYS = 14                    # Trial duration
TRIAL_CREDITS = 10000              # Credits granted for trial
DISCOUNT_PERCENT = 30              # Discount after trial
DISCOUNT_WINDOW_DAYS = 3           # Days to apply discount after trial ends
```

---

## Support & Troubleshooting

### Trial isn't showing as active

**Check:**
- User's `subscription_status` is "trial"
- `trial_started_at` is not null
- `trial_ends_at` is in the future

```sql
SELECT id, email, plan, subscription_status, trial_started_at, trial_ends_at 
FROM users WHERE id = 1;
```

### User still sees trial button after starting

- Check frontend is calling `/api/billing/trial-status` and caching old data
- Make sure to refresh state after trial starts
- Check Authorization header is correct

### Discount offer not showing

**Check:**
- Trial has expired (`trial_ends_at < now`)
- `subscription_status` is "expired"
- Less than 3 days since expiration

### Credits not resetting to 20 after trial

- Run trial expiration handler manually:
  ```python
  await whop_service.handle_trial_expiration(user_id, db)
  ```

---

## Summary

✅ **Implementation Complete:**
- [x] Database schema updated with trial fields
- [x] Trial service functions implemented
- [x] Three new API endpoints added
- [x] Frontend integration examples provided
- [x] Email reminder tracking implemented
- [x] 30% discount offer after trial ends
- [x] Automatic expiration handling
- [x] One trial per user enforcement
- [x] Full documentation provided

**Next Steps:**
1. Integrate trial endpoints in frontend (pricing page, billing settings)
2. Set up scheduled tasks for daily email reminders and expiration handling
3. Create email templates for trial reminders
4. Test trial flow end-to-end
5. Deploy to production

---

**Questions?** See `WHOP_INTEGRATION.md` for general payment setup or contact team.
