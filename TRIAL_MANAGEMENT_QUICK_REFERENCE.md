# Trial Management - Quick Reference

## What Was Added

### Database (User Model)
```
✅ trial_started_at        - When trial begins
✅ trial_ends_at           - When trial expires (14 days later)
✅ trial_used              - Whether user already used trial
✅ trial_plan              - "pro"
✅ trial_email_sent_*      - Track which emails were sent (4 fields)
```

### API Endpoints (3 New)
```
✅ POST   /api/billing/start-trial            → Start 14-day trial
✅ GET    /api/billing/trial-status           → Check trial status
✅ GET    /api/billing/trial-upgrade-offer    → Get 30% discount offer after trial
```

### Service Functions (whop_service.py)
```
✅ start_free_trial()           - Start trial (validates user/usage)
✅ get_trial_status()           - Get current trial state
✅ handle_trial_expiration()    - Revert to Free plan
✅ get_trial_email_reminders()  - Determine which emails to send
✅ mark_trial_email_sent()      - Prevent duplicate emails
✅ get_trial_upgrade_offer()    - Calculate 30% discount
✅ upgrade_from_trial()         - Convert trial to paid plan
```

### Schemas (payment_schemas.py)
```
✅ TrialStatus               - Response for trial check
✅ StartTrialResponse        - Response when starting trial
✅ TrialUpgradeOffer        - Response for post-trial discount
```

---

## Trial Timeline

```
Day 0:   User clicks "Start Free Trial"
         → 14-day counter starts
         → Gets 10,000 credits
         → subscription_status = "trial"
         → Email 1: "Welcome to trial"

Day 3:   Background task sends reminder
         → Email 2: "Explore features"

Day 10:  Background task sends reminder
         → Email 3: "10 days used, 4 left"

Day 13:  Background task sends reminder
         → Email 4: "EXPIRING SOON - Get 30% off!"

Day 14:  Trial expires
         → subscription_status = "expired"
         → plan reverts to "free"
         → credits reset to 20
         → 30% discount offer becomes active

Days 14-17: Discount valid
         → User can upgrade for $20 instead of $29

Day 17+: Discount expires
         → Regular pricing $29
         → User can still upgrade anytime
```

---

## Frontend Buttons

### On Pricing Page

| State | Button |
|-------|--------|
| Never tried | "Start 14-Day Free Trial" |
| In trial | "✓ Trial Active (X days)" (disabled) |
| Trial expired, offer active | "🎉 $20 (30% OFF!) - Expires Soon" |
| Trial used, offer expired | "Upgrade Now - $29/month" |

### In Billing Settings

| State | Display |
|-------|---------|
| In trial | "🎉 Free Trial Active - Expires [DATE]" |
| Trial expired | "Trial ended. Upgrade to continue." |
| Active subscription | "Active Subscription - Renews [DATE]" |
| Free plan | "No subscription" |

---

## API Usage Examples

### Check if User Can Start Trial
```javascript
const response = await fetch(`${API}/api/billing/trial-status`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
const trial = await response.json();

if (!trial.trial_used && !trial.trial_active) {
  // Show "Start Trial" button
  console.log("User can start trial");
} else if (trial.trial_active) {
  // Show countdown
  console.log(`${trial.days_remaining} days left`);
} else {
  // Show "Upgrade" button
  console.log("Trial already used");
}
```

### Start Trial
```javascript
const response = await fetch(`${API}/api/billing/start-trial`, {
  method: 'POST',
  headers: { 
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

if (response.ok) {
  const data = await response.json();
  alert(`Trial active until ${data.trial_ends_at}`);
} else {
  const error = await response.json();
  alert(`Error: ${error.detail}`);
}
```

### Get Post-Trial Discount
```javascript
const response = await fetch(`${API}/api/billing/trial-upgrade-offer`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
const offer = await response.json();

if (offer.offer_active) {
  console.log(`Save ${offer.discount_percent}%!`);
  console.log(`Pay $${offer.discounted_price} instead of $${offer.original_price}`);
  console.log(`Offer expires: ${offer.offer_expires_at}`);
}
```

---

## Backend Tasks to Set Up

### Daily Email Reminders
```python
# Run daily at 9 AM
@scheduler.scheduled_job('cron', hour=9, minute=0)
async def send_trial_reminders():
    # Get all users in trial
    # Check which emails to send
    # Send emails
    # Mark as sent
```

### Daily Trial Expiration Check
```python
# Run daily at 12 AM
@scheduler.scheduled_job('cron', hour=0, minute=0)
async def check_trial_expirations():
    # Get all users with expired trials
    # Revert to free plan
    # Send "trial ended" email
```

---

## Testing Checklist

### Manual Testing

- [ ] Create test user
- [ ] Call `POST /api/billing/start-trial` → Should succeed
- [ ] Call `GET /api/billing/trial-status` → Should show active
- [ ] Try `POST /api/billing/start-trial` again → Should fail
- [ ] Verify user credits are 10,000
- [ ] Run an audit to use some credits
- [ ] Check `GET /api/billing/trial-upgrade-offer` → Should show inactive
- [ ] Manually set `trial_ends_at` to past date in DB
- [ ] Call `handle_trial_expiration()` 
- [ ] Verify plan reverted to "free" and credits reset to 20
- [ ] Check upgrade offer → Should show active with 30% discount
- [ ] Update `trial_ends_at` to 4+ days ago
- [ ] Check upgrade offer → Should show inactive (discount expired)

### Edge Cases

- [ ] Start trial → Check days_remaining = 14
- [ ] After 1 day → Check days_remaining = 13
- [ ] After 13 days → Check days_remaining = 1
- [ ] After 14 days → Check trial_active = false
- [ ] Email tracking → All 4 emails marked as sent
- [ ] Duplicate prevention → Same email not sent twice
- [ ] Trial only once → Second attempt fails with message

---

## Troubleshooting

### "You already have an active trial"
**Solution:** User already started trial today. Cannot start again.

### "You have already used your free trial"
**Solution:** User used trial before. Show upgrade button instead.

### Trial shows as expired but user still has credits
**Solution:** Run `handle_trial_expiration()` manually:
```python
from services import whop_service
await whop_service.handle_trial_expiration(user_id=1, db=db)
```

### Discount offer not showing after trial ends
**Solution:** Check:
- `trial_ends_at` is in past
- `subscription_status` is "expired"
- Less than 3 days since `trial_ends_at`

### Emails not sending
**Solution:** Set up background tasks:
- Check `/tasks.py` for `send_trial_reminders()` function
- Schedule it to run daily with APScheduler or Celery

---

## Key Decisions Made

1. **Trial Only Once** - User can only trial once per account
2. **Pro Plan Only** - Trial is for Pro ($29), not Agency ($99)
3. **14 Days** - Standard trial length
4. **10,000 Credits** - Unlimited effectively during trial
5. **30% Discount** - Applied after trial if user upgrades within 3 days
6. **Email Reminders** - 4 emails total: day 0, 3, 10, 13
7. **Trial-Only Credits** - Credits don't carry over (separate from paid plan)
8. **No Partial Days** - Days remaining shows full day count

---

## Files Modified

```
✅ db/models.py                          - Added 8 trial fields to User
✅ db/payment_schemas.py                 - Added 3 trial schemas
✅ services/whop_service.py              - Added 7 trial functions
✅ api.py                                - Added 3 trial endpoints
📄 docs/TRIAL_MANAGEMENT.md              - Full implementation guide (this file)
📄 TRIAL_MANAGEMENT_QUICK_REFERENCE.md   - This file
```

---

## Next Steps

1. **Backend Tasks** - Set up daily email reminder task
2. **Frontend Integration** - Update pricing page and billing settings
3. **Email Templates** - Create 4 trial-related email templates
4. **Testing** - Test all scenarios from checklist
5. **Deployment** - Deploy to production

---

**For detailed implementation:** See `docs/TRIAL_MANAGEMENT.md`
