# Whop Integration - Quick Reference

## What Was Implemented

✅ **Database Schema** - Added Whop subscription fields to User model
✅ **Whop Service** - API integration for checkout, webhooks, and subscription management  
✅ **Payment Schemas** - Pydantic models for all payment-related endpoints
✅ **API Endpoints** - Complete billing endpoints for checkout and subscription management
✅ **Webhook Handler** - Secure webhook processing with signature verification
✅ **Documentation** - Comprehensive setup and integration guide

## Quick Start

### 1. Set Environment Variables
```bash
WHOP_API_KEY=sk_prod_xxxxx
WHOP_PRO_PRODUCT_ID=prod_xxxxx
WHOP_AGENCY_PRODUCT_ID=prod_xxxxx
WHOP_WEBHOOK_SECRET=whsec_xxxxx
WHOP_SUCCESS_URL=https://yourdomain.com/billing/success
WHOP_CANCEL_URL=https://yourdomain.com/billing/cancelled
```

### 2. Test Endpoints

**Get pricing info:**
```bash
curl http://localhost:8000/api/billing/plans
```

**Create checkout (with auth token):**
```bash
curl -X POST http://localhost:8000/api/billing/checkout-link \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_tier": "pro"}'
```

**Check subscription status:**
```bash
curl http://localhost:8000/api/billing/subscription \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/billing/plans` | GET | No | Get all available plans |
| `/api/billing/checkout-link` | POST | Yes | Create Whop checkout link |
| `/api/billing/subscription` | GET | Yes | Get user's subscription status |
| `/api/billing/cancel-subscription` | POST | Yes | Cancel active subscription |
| `/api/billing/webhook` | POST | No* | Receive Whop webhook events |

*Webhook requires valid signature in headers

## Payment Flow

1. **User initiates upgrade** → Clicks "Upgrade to Pro/Agency"
2. **Get checkout link** → POST `/api/billing/checkout-link`
3. **Redirect to Whop** → Opens Whop checkout URL
4. **User pays** → Enters payment details on Whop
5. **Whop confirms payment** → Sends webhook event
6. **Update user** → Backend updates plan, credits, subscription info
7. **User redirected** → Back to SUCCESS_URL with updated plan

## Database Updates

When payment succeeds:
- `plan` = "pro" or "agency"
- `credits_remaining` = 10000 or 50000
- `subscription_status` = "active"
- `subscription_started_at` = Now
- `subscription_renews_at` = Now + 30 days
- `whop_subscription_id` = Subscription ID from Whop
- `whop_product_id` = Product ID from Whop

## Key Files

| File | Purpose |
|------|---------|
| `services/whop_service.py` | Whop API integration |
| `db/payment_schemas.py` | Pydantic models |
| `api.py` | Billing endpoints |
| `db/models.py` | User model with Whop fields |
| `.env.example` | Configuration template |
| `docs/WHOP_INTEGRATION.md` | Full documentation |

## Testing Webhook Locally

Use ngrok to expose local endpoint:
```bash
ngrok http 8000
```

Then set webhook URL in Whop to: `https://your-ngrok-url.ngrok.io/api/billing/webhook`

Use Whop's webhook tester to send test events.

## Security Features

✅ Webhook signature verification (HMAC-SHA256)
✅ User ownership validation
✅ API key in environment variables
✅ Subscription status tracking
✅ Activity logging

## Troubleshooting

**Webhook not working?**
- Check webhook secret matches
- Ensure endpoint is publicly accessible
- Verify webhook subscription in Whop dashboard

**Checkout link fails?**
- Verify WHOP_API_KEY is correct
- Check product IDs exist
- Review logs in `whop_service.py`

**Credits not updating?**
- Check webhook is received (check logs)
- Verify database fields updated
- Check subscription_id is stored

## Next Steps

1. ✅ Environment setup (copy `.env.example` → `.env`)
2. ✅ Test endpoints locally
3. ✅ Deploy webhook endpoint publicly
4. ✅ Configure Whop webhooks
5. ✅ Update frontend pricing page
6. ✅ Test full payment flow in production

## References

- [Whop Documentation](https://docs.whop.com)
- [WHOP_INTEGRATION.md](./docs/WHOP_INTEGRATION.md) - Full guide
- `services/whop_service.py` - Code comments
