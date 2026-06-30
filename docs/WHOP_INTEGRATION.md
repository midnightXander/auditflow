# Whop Payment Integration Guide

Complete integration of Whop checkout for plan upgrades in AuditFlow.

## Overview

This integration enables users to upgrade from the Free plan to Pro ($29/month) or Agency ($99/month) plans using Whop's payment processing.

### Plan Details
- **Free**: $0/month, 20 credits/month
- **Pro**: $29/month, 10,000 credits/month
- **Agency**: $99/month, 50,000 credits/month

## Setup Instructions

### 1. Create Whop Account & Products

1. Sign up at [whop.com](https://whop.com)
2. Go to **Dashboard > Products**
3. Create two products:
   - **Pro Plan**: Price $29/month, name "Pro Plan"
   - **Agency Plan**: Price $99/month, name "Agency Plan"
4. Copy the product IDs

### 2. Configure API Keys

1. Go to **Dashboard > Settings > API**
2. Generate an API key
3. Go to **Dashboard > Settings > Webhooks**
4. Generate a webhook secret

### 3. Environment Variables

Add the following to your `.env` file:

```bash
WHOP_API_KEY=your_whop_api_key_here
WHOP_PRO_PRODUCT_ID=your_pro_product_id_here
WHOP_AGENCY_PRODUCT_ID=your_agency_product_id_here
WHOP_WEBHOOK_SECRET=your_webhook_secret_here
WHOP_SUCCESS_URL=https://yourdomain.com/billing/success
WHOP_CANCEL_URL=https://yourdomain.com/billing/cancelled
```

### 4. Configure Webhooks

1. Go to **Dashboard > Settings > Webhooks**
2. Add webhook endpoint: `https://yourdomain.com/api/billing/webhook`
3. Subscribe to events:
   - `order.completed`
   - `order.failed`
   - `subscription.cancelled`

## API Endpoints

### Get All Plans
```
GET /api/billing/plans
```

**Response:**
```json
{
  "plans": {
    "pro": {
      "name": "Pro Plan",
      "price": 29,
      "credits": 10000
    },
    "agency": {
      "name": "Agency Plan",
      "price": 99,
      "credits": 50000
    }
  }
}
```

### Create Checkout Link
```
POST /api/billing/checkout-link
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "plan_tier": "pro"
}
```

**Response:**
```json
{
  "checkout_url": "https://whop.com/checkout/...",
  "plan_tier": "pro"
}
```

### Get Subscription Status
```
GET /api/billing/subscription
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "plan": "pro",
  "subscription_status": "active",
  "subscription_started_at": "2024-04-28T10:00:00",
  "subscription_renews_at": "2024-05-28T10:00:00",
  "credits_remaining": 10000,
  "whop_subscription_id": "sub_123456"
}
```

### Cancel Subscription
```
POST /api/billing/cancel-subscription
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "message": "Subscription cancelled successfully"
}
```

### Webhook Endpoint
```
POST /api/billing/webhook
X-Whop-Signature: <signature>
```

This endpoint receives payment events from Whop and updates user records.

## Frontend Integration

### Show Pricing Page
```javascript
// Fetch available plans
const response = await fetch('/api/billing/plans');
const { plans } = await response.json();

// Display plans with upgrade buttons
```

### Initiate Checkout
```javascript
// When user clicks "Upgrade to Pro"
const response = await fetch('/api/billing/checkout-link', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ plan_tier: 'pro' })
});

const { checkout_url } = await response.json();
window.location.href = checkout_url;
```

### After Payment
1. User completes payment on Whop
2. Redirected to `WHOP_SUCCESS_URL`
3. Whop sends webhook to `/api/billing/webhook`
4. Backend updates user:
   - `plan` = "pro" or "agency"
   - `credits_remaining` = 10000 or 50000
   - `subscription_status` = "active"
   - Stores subscription ID and renewal date
5. User can check subscription status via `/api/billing/subscription`

## Payment Flow

```
User clicks "Upgrade"
    ↓
Frontend calls POST /api/billing/checkout-link
    ↓
Backend creates Whop checkout link
    ↓
Frontend redirects to Whop checkout URL
    ↓
User enters payment info on Whop
    ↓
Payment processed
    ↓
Whop sends webhook to /api/billing/webhook
    ↓
Backend updates user plan & credits
    ↓
User redirected to SUCCESS_URL
    ↓
Dashboard shows new plan & credits
```

## Database Changes

New fields added to `User` model:
- `whop_subscription_id` - Whop subscription ID
- `whop_product_id` - Product ID (pro/agency)
- `subscription_status` - Status (active/cancelled/expired)
- `subscription_started_at` - When subscription started
- `subscription_renews_at` - Next renewal date
- `whop_metadata` - Additional Whop data

## Error Handling

### Invalid Plan Tier
```json
{
  "detail": "Invalid plan tier: invalid_tier"
}
```

### Already Subscribed
```json
{
  "detail": "You already have an active pro subscription"
}
```

### Checkout Link Creation Failed
```json
{
  "detail": "Failed to create checkout link. Please try again."
}
```

### Invalid Webhook Signature
The webhook will reject requests with invalid signatures for security.

## Testing

### Local Testing
1. Set `WHOP_API_KEY` and product IDs in `.env`
2. Use Whop's test mode for sandbox payments
3. Test webhook delivery using Whop's webhook tester

### Test Endpoints
```bash
# Get plans
curl http://localhost:8000/api/billing/plans

# Create checkout link (requires auth)
curl -X POST http://localhost:8000/api/billing/checkout-link \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"plan_tier": "pro"}'

# Get subscription status
curl http://localhost:8000/api/billing/subscription \
  -H "Authorization: Bearer <token>"
```

## Security Considerations

1. **Webhook Verification**: All webhooks are verified using HMAC-SHA256
2. **API Key Storage**: Never commit API keys to version control
3. **Sensitive Data**: Subscription details are only returned to authenticated users
4. **Rate Limiting**: Consider adding rate limiting to checkout endpoint
5. **User Validation**: All operations validate user ownership

## Troubleshooting

### Webhook Not Received
1. Check webhook endpoint is publicly accessible
2. Verify webhook secret in `.env`
3. Check Whop dashboard webhook logs
4. Ensure firewall allows Whop IPs

### Checkout Link Not Working
1. Verify WHOP_API_KEY is correct
2. Verify product IDs exist in Whop account
3. Check Whop API rate limits
4. Review application logs for errors

### Credits Not Updated
1. Check webhook is being received
2. Verify subscription_id is stored
3. Check database logs
4. Ensure webhook secret matches

## Support

For Whop API documentation: https://docs.whop.com
For issues: Check logs in `backend/services/whop_service.py`

## Files Modified/Created

- `db/models.py` - Added Whop fields to User model
- `services/whop_service.py` - Whop API integration service
- `db/payment_schemas.py` - Pydantic schemas for payment endpoints
- `backend/api.py` - Added billing endpoints and webhook handler
- `.env.example` - Configuration template

## Next Steps

1. Configure Whop account with API keys
2. Update `.env` with Whop credentials
3. Deploy webhook endpoint publicly
4. Test checkout flow
5. Update pricing page frontend to call checkout endpoint
6. Monitor webhook logs
