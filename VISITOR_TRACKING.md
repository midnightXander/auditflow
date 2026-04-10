# Visitor Tracking & Conversion Analytics

Track landing page visitors, their geographic location, referrer source, and conversion metrics for data-driven growth decisions.

## Features

✅ **Automatic IP Capture** — Extract visitor IP from requests (handles proxies/load balancers)  
✅ **GeoIP Geolocation** — Auto-detect country, city, latitude, longitude  
✅ **Referrer Tracking** — Know where traffic comes from  
✅ **Conversion Tracking** — Mark visitors who sign up as customers  
✅ **UTM Parameters** — Track marketing campaigns (utm_source, utm_medium, utm_campaign)  
✅ **Analytics Dashboard** — View conversion rate, top countries, top referrers  
✅ **No Auth Required** — Landing page can track anonymously  

## Quick Start

### 1. Track a visitor (from landing page)

**JavaScript (Frontend)**
```javascript
// Call when page loads or on specific events
fetch('/api/track/visitor', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    page_url: window.location.href,
    utm_source: new URLSearchParams(window.location.search).get('utm_source'),
    utm_medium: new URLSearchParams(window.location.search).get('utm_medium'),
    utm_campaign: new URLSearchParams(window.location.search).get('utm_campaign')
  })
});
```

**Or with query parameters:**
```
POST /api/track/visitor?page_url=https://mysite.com/pricing&utm_source=google&utm_medium=cpc&utm_campaign=spring-2024
```

**Response:**
```json
{
  "status": "tracked",
  "visitor_id": 123,
  "ip": "203.0.113.45",
  "country": "United States",
  "timestamp": "2026-04-10T15:30:00",
  "utm": {
    "source": "google",
    "medium": "cpc",
    "campaign": "spring-2024"
  }
}
```

### 2. Mark conversion when user signs up

When a user registers, their visitor record is **automatically** marked as converted (matched by IP).

Or manually mark:
```bash
POST /api/visitors/123/mark-converted
Authorization: Bearer YOUR_TOKEN
```

### 3. View analytics (Admin only)

```bash
GET /api/visitors/analytics?days=30
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "analytics": {
    "period_days": 30,
    "total_visits": 1250,
    "unique_visitors": 987,
    "conversions": 45,
    "conversion_rate": 3.6,
    "top_countries": [
      {
        "country": "United States",
        "code": "US",
        "count": 650
      },
      {
        "country": "United Kingdom",
        "code": "GB",
        "count": 180
      }
    ],
    "top_referrers": [
      {
        "referrer": "https://www.google.com",
        "count": 420
      },
      {
        "referrer": "https://www.producthunt.com",
        "count": 85
      }
    ]
  },
  "period": "Last 30 days",
  "generated_at": "2026-04-10T15:30:00"
}
```

## API Reference

### Tracking Endpoints

#### `POST /api/track/visitor`
Track a landing page visitor (no auth required)

**Query Parameters:**
- `page_url` (string, optional) — URL being visited
- `utm_source` (string, optional) — Traffic source (google, facebook, newsletter, etc)
- `utm_medium` (string, optional) — Traffic medium (cpc, organic, email, social, etc)
- `utm_campaign` (string, optional) — Campaign name

**Response:**
```json
{
  "status": "tracked|error",
  "visitor_id": 123,
  "ip": "203.0.113.45",
  "country": "United States",
  "timestamp": "2026-04-10T15:30:00",
  "utm": { "source": "google", "medium": "cpc", "campaign": "spring-2024" }
}
```

---

#### `GET /api/visitors/analytics`
Get visitor analytics for conversion analysis (admin only)

**Query Parameters:**
- `days` (int, default: 30) — Analytics period

**Response:**
```json
{
  "analytics": {
    "total_visits": 1250,
    "unique_visitors": 987,
    "conversions": 45,
    "conversion_rate": 3.6,
    "top_countries": [...],
    "top_referrers": [...]
  },
  "period": "Last 30 days",
  "generated_at": "2026-04-10T15:30:00"
}
```

---

#### `GET /api/visitors/list`
List all tracked visitors with filtering (admin only)

**Query Parameters:**
- `page` (int, default: 1) — Page number
- `page_size` (int, default: 50) — Items per page
- `country` (string, optional) — Filter by country code (e.g., "US")
- `converted_only` (bool, default: false) — Show only converted visitors

**Response:**
```json
{
  "items": [
    {
      "id": 123,
      "ip": "203.0.113.45",
      "country": "United States",
      "country_code": "US",
      "city": "San Francisco",
      "referer": "https://www.google.com",
      "visited_at": "2026-04-10T15:30:00",
      "converted": true,
      "converted_user_id": 42
    }
  ],
  "total": 987,
  "page": 1,
  "page_size": 50,
  "total_pages": 20
}
```

---

#### `POST /api/visitors/{visitor_id}/mark-converted`
Manually mark a visitor as converted (auth required)

**Response:**
```json
{
  "status": "success",
  "visitor_id": 123,
  "converted": true,
  "user_id": 42
}
```

## Geolocation

Uses free GeoIP services with fallbacks:

1. **ipapi.co** (30,000 requests/month free)
2. **ip-api.com** (45 requests/minute free)
3. **geoip.rs** (unlimited free, slower)

**Captured Data:**
- IP Address
- Country & Country Code (ISO 3166-1 alpha-2)
- City
- Latitude & Longitude

**Private IPs** (localhost, 192.168.x.x, etc.) are marked as "Local Network" and don't consume API quota.

## Frontend Implementation

### React Example

```jsx
import { useEffect } from 'react';

export default function LandingPage() {
  useEffect(() => {
    // Track visitor on page load
    const trackVisitor = async () => {
      const params = new URLSearchParams(window.location.search);
      
      try {
        const response = await fetch('/api/track/visitor', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            page_url: window.location.href,
            utm_source: params.get('utm_source'),
            utm_medium: params.get('utm_medium'),
            utm_campaign: params.get('utm_campaign')
          })
        });
        
        const data = await response.json();
        console.log('Visitor tracked:', data.visitor_id);
        
        // Store visitor_id in session for conversion tracking
        sessionStorage.setItem('visitor_id', data.visitor_id);
      } catch (error) {
        console.error('Failed to track visitor:', error);
      }
    };
    
    trackVisitor();
  }, []);
  
  return <h1>Welcome to AuditFlow</h1>;
}
```

### Register with Conversion Tracking

```jsx
async function handleRegister(email, password) {
  const response = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: name })
  });
  
  if (response.ok) {
    const data = await response.json();
    // User is automatically marked as converted by IP
    console.log('Registration successful, conversion tracked');
    localStorage.setItem('access_token', data.access_token);
  }
}
```

## UTM Campaign Tracking

Use standard UTM parameters to track marketing campaigns:

```
https://yoursite.com/?utm_source=google&utm_medium=cpc&utm_campaign=spring-sale

https://yoursite.com/?utm_source=twitter&utm_medium=social&utm_campaign=product-launch

https://yoursite.com/?utm_source=newsletter&utm_medium=email&utm_campaign=weekly-digest
```

These are captured in the analytics and help you understand which campaigns drive conversions.

## Analytics Use Cases

### 🎯 Monitor Conversion Funnel
```
Total Visits: 1000
Conversions: 50
Conversion Rate: 5%
```

### 🌍 Identify High-Value Markets
```
Top Countries by Conversion:
1. US: 35 conversions (best performer)
2. UK: 8 conversions
3. CA: 5 conversions
```

### 📊 Evaluate Marketing Channels
```
Top Referrers:
- Google Search: 420 visits → 25 conversions (5.95%)
- ProductHunt: 85 visits → 12 conversions (14.1%)
- Newsletter: 120 visits → 8 conversions (6.67%)
```

### 🎥 Campaign Performance
```
utm_campaign=spring-sale: 250 visits → 18 conversions (7.2%)
utm_campaign=product-launch: 180 visits → 9 conversions (5%)
utm_campaign=weekly-digest: 120 visits → 8 conversions (6.67%)
```

## Privacy Considerations

✅ **Privacy-Friendly:**
- No cookies used
- Only captures IP, country, referrer (standard HTTP headers)
- No personal data collected without consent
- Private IPs (localhost, VPN, corporate) handled safely

⚠️ **Compliance:**
- Add tracking disclosure in Privacy Policy
- Comply with GDPR, CCPA as needed
- Consider IP anonymization for EU visitors

## Troubleshooting

**Visitors not being tracked?**
- Check CORS settings allow `/api/track/visitor` from your domain
- Verify `page_url` parameter is correct
- Check browser console for network errors

**GeoIP lookups failing?**
- Free APIs have rate limits (30-45 requests/minute)
- Check server logs for GeoIP service errors
- Visitor still tracked even if geolocation fails

**Conversion not matching?**
- Conversion matched by IP address
- If visitor uses VPN/proxy, IP may change before signup
- Use `visitor_id` from tracking response for manual matching

## Database Migrations

Create the `visitors` table:

```bash
cd backend
alembic revision --autogenerate -m "add visitor tracking"
alembic upgrade head
```

## Example: Full Workflow

1. **User visits landing page**
   ```
   GET / (page loads)
   POST /api/track/visitor
   → Visitor ID 123 created, IP 203.0.113.45, Country: US
   ```

2. **User clicks signup button**
   ```
   GET /signup
   ```

3. **User fills form and registers**
   ```
   POST /api/auth/register (email, password)
   → User 42 created
   → Visitor 123 marked as converted, linked to User 42
   ```

4. **Admin checks analytics**
   ```
   GET /api/visitors/analytics?days=7
   → Conversion rate: 5.2%
   → Top referrer: google.com
   → Top country: US (45 conversions)
   ```

That's it! You now have actionable conversion insights. 🚀
