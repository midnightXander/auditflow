// Trial Management - React Frontend Integration Example
// Place these components in your frontend (Next.js/React app)

import { useState, useEffect } from 'react';

// ============================================================================
// 1. TRIAL STATUS BADGE - Show in header/navbar
// ============================================================================

export function TrialBadge() {
  const [trial, setTrial] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkTrialStatus = async () => {
      try {
        const response = await fetch(`${process.env.REACT_APP_API_URL}/api/billing/trial-status`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          setTrial(data);
        }
      } catch (error) {
        console.error('Failed to check trial status:', error);
      } finally {
        setLoading(false);
      }
    };

    checkTrialStatus();
  }, []);

  if (loading || !trial) return null;

  if (trial.trial_active) {
    const daysLeft = trial.days_remaining;
    const urgency = daysLeft <= 3 ? 'urgent' : daysLeft <= 7 ? 'warning' : 'info';
    
    return (
      <div className={`trial-badge ${urgency}`}>
        🎉 Trial: {daysLeft} day{daysLeft !== 1 ? 's' : ''} left
      </div>
    );
  }

  if (!trial.trial_used) {
    return (
      <div className="trial-badge available">
        💰 Free trial available
      </div>
    );
  }

  return null;
}

// Styles for TrialBadge
const trialBadgeStyles = `
  .trial-badge {
    padding: 0.5rem 1rem;
    border-radius: 0.5rem;
    font-size: 0.875rem;
    font-weight: 600;
    display: inline-block;
  }

  .trial-badge.info {
    background-color: #e0e7ff;
    color: #3730a3;
  }

  .trial-badge.warning {
    background-color: #fef3c7;
    color: #92400e;
  }

  .trial-badge.urgent {
    background-color: #fee2e2;
    color: #7f1d1d;
  }

  .trial-badge.available {
    background-color: #d1fae5;
    color: #065f46;
  }
`;

// ============================================================================
// 2. PRICING PAGE WITH TRIAL BUTTON
// ============================================================================

export function PricingPage() {
  const [plans, setPlans] = useState(null);
  const [trial, setTrial] = useState(null);
  const [offer, setOffer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const token = localStorage.getItem('accessToken');

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch plans
        const plansRes = await fetch(`${process.env.REACT_APP_API_URL}/api/billing/plans`);
        const plansData = await plansRes.json();
        setPlans(plansData.plans);

        // Fetch trial status
        const trialRes = await fetch(`${process.env.REACT_APP_API_URL}/api/billing/trial-status`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const trialData = await trialRes.json();
        setTrial(trialData);

        // Fetch upgrade offer
        const offerRes = await fetch(`${process.env.REACT_APP_API_URL}/api/billing/trial-upgrade-offer`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const offerData = await offerRes.json();
        setOffer(offerData);
      } catch (err) {
        setError('Failed to load pricing information');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [token]);

  async function handleStartTrial() {
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/api/billing/start-trial`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        alert(`🎉 Trial started! Expires ${new Date(data.trial_ends_at).toLocaleDateString()}`);
        window.location.reload();
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (err) {
      alert('Failed to start trial');
      console.error(err);
    }
  }

  async function handleCheckout(planTier) {
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/api/billing/checkout-link`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ plan_tier: planTier })
      });

      if (response.ok) {
        const data = await response.json();
        window.location.href = data.checkout_url;
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (err) {
      alert('Failed to create checkout link');
      console.error(err);
    }
  }

  if (loading) {
    return <div className="pricing-container"><p>Loading pricing...</p></div>;
  }

  if (error) {
    return <div className="pricing-container"><p className="error">{error}</p></div>;
  }

  return (
    <div className="pricing-container">
      <h1>Simple, Transparent Pricing</h1>
      <p className="subtitle">Choose the plan that works for you</p>

      <div className="pricing-grid">
        {/* FREE PLAN */}
        <div className="pricing-card">
          <h3>Free</h3>
          <div className="price">$0<span>/mo</span></div>
          <p className="description">Perfect for getting started</p>
          
          <div className="features">
            <div className="feature">✓ 20 credits/month</div>
            <div className="feature">✓ 1 audit per day</div>
            <div className="feature">✓ Basic reports</div>
          </div>

          <button disabled className="btn btn-secondary">
            Current Plan
          </button>
        </div>

        {/* PRO PLAN */}
        <div className={`pricing-card ${trial?.plan === 'pro' && trial?.trial_active ? 'highlight' : offer?.offer_active ? 'special' : ''}`}>
          {offer?.offer_active && (
            <div className="badge-discount">
              🎉 {offer.discount_percent}% OFF
            </div>
          )}
          
          <h3>Pro</h3>
          <div className="price">
            {offer?.offer_active ? (
              <>
                <span className="original">${offer.original_price}</span>
                <span className="discounted">${offer.discounted_price}</span>
                <span>/mo</span>
              </>
            ) : (
              <>
                ${plans?.pro?.price}
                <span>/mo</span>
              </>
            )}
          </div>
          <p className="description">Most popular for agencies</p>

          <div className="features">
            <div className="feature">✓ {plans?.pro?.credits?.toLocaleString()} credits</div>
            <div className="feature">✓ Unlimited audits</div>
            <div className="feature">✓ Advanced reports</div>
            <div className="feature">✓ API access</div>
          </div>

          {/* Show appropriate button based on trial status */}
          {!trial?.trial_used && !trial?.trial_active ? (
            <button onClick={handleStartTrial} className="btn btn-primary">
              Start 14-Day Free Trial
            </button>
          ) : trial?.trial_active ? (
            <button disabled className="btn btn-success">
              ✓ Trial Active ({trial.days_remaining} days)
            </button>
          ) : offer?.offer_active ? (
            <>
              <button onClick={() => handleCheckout('pro')} className="btn btn-primary">
                Get {offer.discount_percent}% OFF - ${offer.discounted_price}/mo
              </button>
              <p className="offer-expiry">
                Offer expires {new Date(offer.offer_expires_at).toLocaleDateString()}
              </p>
            </>
          ) : trial?.plan === 'pro' ? (
            <button disabled className="btn btn-secondary">
              ✓ Active Subscription
            </button>
          ) : (
            <button onClick={() => handleCheckout('pro')} className="btn btn-primary">
              Upgrade Now - ${plans?.pro?.price}/mo
            </button>
          )}
        </div>

        {/* AGENCY PLAN */}
        <div className="pricing-card">
          <h3>Agency</h3>
          <div className="price">${plans?.agency?.price}<span>/mo</span></div>
          <p className="description">For larger teams</p>

          <div className="features">
            <div className="feature">✓ {plans?.agency?.credits?.toLocaleString()} credits</div>
            <div className="feature">✓ Unlimited everything</div>
            <div className="feature">✓ Premium support</div>
            <div className="feature">✓ Custom integrations</div>
          </div>

          {trial?.plan === 'agency' ? (
            <button disabled className="btn btn-secondary">
              ✓ Active Subscription
            </button>
          ) : (
            <button onClick={() => handleCheckout('agency')} className="btn btn-primary">
              Upgrade Now - ${plans?.agency?.price}/mo
            </button>
          )}
        </div>
      </div>

      <p className="info-text">
        💡 All plans include 14-day money-back guarantee
      </p>
    </div>
  );
}

// Styles for PricingPage
const pricingPageStyles = `
  .pricing-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 3rem 2rem;
    text-align: center;
  }

  .pricing-container h1 {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
  }

  .pricing-container .subtitle {
    font-size: 1.125rem;
    color: #6b7280;
    margin-bottom: 3rem;
  }

  .pricing-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
    margin: 3rem 0;
  }

  .pricing-card {
    border: 2px solid #e5e7eb;
    border-radius: 0.75rem;
    padding: 2rem;
    background: white;
    position: relative;
    transition: all 0.3s ease;
  }

  .pricing-card:hover {
    border-color: #0075ff;
    box-shadow: 0 10px 30px rgba(0, 117, 255, 0.1);
    transform: translateY(-5px);
  }

  .pricing-card.highlight {
    border-color: #0075ff;
    box-shadow: 0 0 0 3px rgba(0, 117, 255, 0.1);
  }

  .pricing-card.special {
    border-color: #f59e0b;
    background: #fffbf0;
  }

  .pricing-card .badge-discount {
    position: absolute;
    top: -15px;
    right: 20px;
    background: #f59e0b;
    color: white;
    padding: 0.5rem 1rem;
    border-radius: 999px;
    font-size: 0.875rem;
    font-weight: 600;
  }

  .pricing-card h3 {
    font-size: 1.5rem;
    font-weight: 600;
    margin-top: 0.5rem;
  }

  .pricing-card .price {
    font-size: 3rem;
    font-weight: 700;
    margin: 1rem 0;
    color: #0075ff;
  }

  .pricing-card .price .original {
    text-decoration: line-through;
    color: #9ca3af;
    font-size: 1.875rem;
    margin-right: 0.5rem;
  }

  .pricing-card .price .discounted {
    color: #dc2626;
  }

  .pricing-card .price span {
    font-size: 1rem;
    color: #6b7280;
  }

  .pricing-card .description {
    color: #6b7280;
    margin-bottom: 2rem;
  }

  .features {
    text-align: left;
    margin: 2rem 0;
  }

  .feature {
    padding: 0.75rem 0;
    color: #374151;
    border-bottom: 1px solid #f3f4f6;
  }

  .feature:last-child {
    border-bottom: none;
  }

  .btn {
    width: 100%;
    padding: 0.75rem 1.5rem;
    border-radius: 0.5rem;
    font-size: 1rem;
    font-weight: 600;
    border: none;
    cursor: pointer;
    transition: all 0.3s ease;
    margin-top: 1rem;
  }

  .btn-primary {
    background: linear-gradient(135deg, #0075ff, #005acc);
    color: white;
  }

  .btn-primary:hover {
    transform: scale(1.02);
    box-shadow: 0 5px 15px rgba(0, 117, 255, 0.3);
  }

  .btn-secondary {
    background: #e5e7eb;
    color: #374151;
  }

  .btn-secondary:hover {
    background: #d1d5db;
  }

  .btn-success {
    background: #10b981;
    color: white;
  }

  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .offer-expiry {
    font-size: 0.875rem;
    color: #f59e0b;
    margin-top: 0.5rem;
    font-weight: 600;
  }

  .info-text {
    color: #6b7280;
    margin-top: 2rem;
    font-size: 0.875rem;
  }
`;

// ============================================================================
// 3. BILLING SETTINGS PAGE
// ============================================================================

export function BillingSettings() {
  const [trial, setTrial] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [offer, setOffer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const token = localStorage.getItem('accessToken');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [trialRes, subRes, offerRes] = await Promise.all([
          fetch(`${process.env.REACT_APP_API_URL}/api/billing/trial-status`, {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch(`${process.env.REACT_APP_API_URL}/api/billing/subscription`, {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch(`${process.env.REACT_APP_API_URL}/api/billing/trial-upgrade-offer`, {
            headers: { 'Authorization': `Bearer ${token}` }
          })
        ]);

        if (trialRes.ok) setTrial(await trialRes.json());
        if (subRes.ok) setSubscription(await subRes.json());
        if (offerRes.ok) setOffer(await offerRes.json());
      } catch (err) {
        setError('Failed to load billing information');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [token]);

  async function handleCancelSubscription() {
    if (!window.confirm('Are you sure you want to cancel your subscription?')) {
      return;
    }

    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/api/billing/cancel-subscription`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        alert('Subscription cancelled');
        window.location.reload();
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (err) {
      alert('Failed to cancel subscription');
      console.error(err);
    }
  }

  async function handleUpgrade(plan) {
    window.location.href = `/pricing?upgrade=${plan}`;
  }

  if (loading) return <div>Loading...</div>;

  return (
    <div className="billing-settings">
      <h2>Billing & Subscription</h2>

      {/* TRIAL SECTION */}
      {trial?.trial_active && (
        <div className="card trial-card">
          <div className="card-header">
            <h3>🎉 Free Trial Active</h3>
            <span className="badge-active">Active</span>
          </div>

          <div className="card-body">
            <div className="info-row">
              <span className="label">Plan:</span>
              <span className="value">{trial.plan} Trial</span>
            </div>

            <div className="info-row">
              <span className="label">Credits:</span>
              <span className="value">{trial.credits_remaining.toLocaleString()}</span>
            </div>

            <div className="info-row">
              <span className="label">Started:</span>
              <span className="value">{new Date(trial.trial_started_at).toLocaleDateString()}</span>
            </div>

            <div className="info-row">
              <span className="label">Expires:</span>
              <span className="value">{new Date(trial.trial_ends_at).toLocaleDateString()}</span>
            </div>

            <div className="progress-bar">
              <div 
                className="progress-fill"
                style={{ width: `${(14 - trial.days_remaining) / 14 * 100}%` }}
              />
            </div>

            <p className="countdown">
              <strong>{trial.days_remaining}</strong> day{trial.days_remaining !== 1 ? 's' : ''} remaining
            </p>

            {trial.days_remaining <= 3 && (
              <div className="alert alert-warning">
                ⚠️ Your trial is expiring soon! Upgrade now to get 30% off.
              </div>
            )}

            <button 
              onClick={() => handleUpgrade('pro')} 
              className="btn btn-primary"
            >
              Upgrade Now
            </button>
          </div>
        </div>
      )}

      {/* SUBSCRIPTION SECTION */}
      {subscription?.subscription_status === 'active' && (
        <div className="card subscription-card">
          <div className="card-header">
            <h3>Active Subscription</h3>
            <span className="badge-active">Active</span>
          </div>

          <div className="card-body">
            <div className="info-row">
              <span className="label">Plan:</span>
              <span className="value capitalize">{subscription.plan} Plan</span>
            </div>

            <div className="info-row">
              <span className="label">Credits:</span>
              <span className="value">{subscription.credits_remaining.toLocaleString()}</span>
            </div>

            <div className="info-row">
              <span className="label">Renews:</span>
              <span className="value">{new Date(subscription.subscription_renews_at).toLocaleDateString()}</span>
            </div>

            <div className="info-row">
              <span className="label">Subscription ID:</span>
              <span className="value mono">{subscription.whop_subscription_id}</span>
            </div>

            <button 
              onClick={handleCancelSubscription}
              className="btn btn-danger"
            >
              Cancel Subscription
            </button>
          </div>
        </div>
      )}

      {/* POST-TRIAL DISCOUNT OFFER */}
      {offer?.offer_active && (
        <div className="card offer-card">
          <div className="card-header">
            <h3>🎁 Limited Time Offer</h3>
            <span className="badge-discount">{offer.discount_percent}% OFF</span>
          </div>

          <div className="card-body">
            <p className="offer-text">
              Upgrade to Pro and save <strong>{offer.discount_percent}%</strong>!
            </p>

            <div className="price-comparison">
              <div className="price-item">
                <span className="label">Original Price:</span>
                <span className="price original">${offer.original_price}</span>
              </div>

              <div className="price-item">
                <span className="label">Your Price:</span>
                <span className="price discounted">${offer.discounted_price}</span>
              </div>

              <div className="price-item">
                <span className="label">You Save:</span>
                <span className="price savings">${offer.original_price - offer.discounted_price}</span>
              </div>
            </div>

            <p className="offer-expiry">
              ⏰ Offer expires {new Date(offer.offer_expires_at).toLocaleDateString()}
            </p>

            <button 
              onClick={() => handleUpgrade('pro')}
              className="btn btn-primary"
            >
              Claim {offer.discount_percent}% Discount - ${offer.discounted_price}/mo
            </button>
          </div>
        </div>
      )}

      {/* NO TRIAL/SUBSCRIPTION */}
      {!trial?.trial_active && subscription?.subscription_status !== 'active' && !offer?.offer_active && (
        <div className="card empty-card">
          <p>No active subscription or trial</p>
          <button 
            onClick={() => window.location.href = '/pricing'}
            className="btn btn-primary"
          >
            View Plans
          </button>
        </div>
      )}

      {error && <div className="alert alert-error">{error}</div>}
    </div>
  );
}

// Styles for BillingSettings
const billingSettingsStyles = `
  .billing-settings {
    max-width: 600px;
    margin: 0 auto;
    padding: 2rem;
  }

  .billing-settings h2 {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 2rem;
  }

  .card {
    border: 2px solid #e5e7eb;
    border-radius: 0.75rem;
    padding: 1.5rem;
    background: white;
    margin-bottom: 2rem;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #f3f4f6;
  }

  .card-header h3 {
    font-size: 1.25rem;
    font-weight: 600;
    margin: 0;
  }

  .badge-active {
    background: #d1fae5;
    color: #065f46;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.875rem;
    font-weight: 600;
  }

  .badge-discount {
    background: #f59e0b;
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.875rem;
    font-weight: 600;
  }

  .card-body {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .info-row {
    display: flex;
    justify-content: space-between;
    padding: 0.75rem 0;
  }

  .info-row .label {
    color: #6b7280;
    font-weight: 500;
  }

  .info-row .value {
    font-weight: 600;
    color: #1f2937;
  }

  .info-row .mono {
    font-family: monospace;
    font-size: 0.875rem;
  }

  .progress-bar {
    height: 8px;
    background: #e5e7eb;
    border-radius: 999px;
    overflow: hidden;
    margin: 1rem 0;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #0075ff, #0066dd);
    transition: width 0.3s ease;
  }

  .countdown {
    text-align: center;
    color: #0075ff;
    font-weight: 600;
    font-size: 1.125rem;
  }

  .alert {
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
    font-size: 0.875rem;
  }

  .alert-warning {
    background: #fef3c7;
    color: #92400e;
    border: 1px solid #fcd34d;
  }

  .alert-error {
    background: #fee2e2;
    color: #7f1d1d;
    border: 1px solid #fca5a5;
  }

  .price-comparison {
    background: #f9fafb;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
  }

  .price-item {
    display: flex;
    justify-content: space-between;
    padding: 0.5rem 0;
  }

  .price {
    font-weight: 700;
  }

  .price.original {
    text-decoration: line-through;
    color: #9ca3af;
  }

  .price.discounted {
    color: #dc2626;
    font-size: 1.25rem;
  }

  .price.savings {
    color: #10b981;
  }

  .offer-expiry {
    text-align: center;
    color: #f59e0b;
    font-weight: 600;
    font-size: 0.875rem;
  }

  .btn {
    width: 100%;
    padding: 0.75rem 1.5rem;
    border-radius: 0.5rem;
    font-size: 1rem;
    font-weight: 600;
    border: none;
    cursor: pointer;
    transition: all 0.3s ease;
  }

  .btn-primary {
    background: linear-gradient(135deg, #0075ff, #005acc);
    color: white;
  }

  .btn-primary:hover {
    transform: scale(1.02);
    box-shadow: 0 5px 15px rgba(0, 117, 255, 0.3);
  }

  .btn-danger {
    background: #ef4444;
    color: white;
  }

  .btn-danger:hover {
    background: #dc2626;
  }

  .trial-card {
    border-color: #0075ff;
    background: #f0f9ff;
  }

  .subscription-card {
    border-color: #10b981;
    background: #f0fdf4;
  }

  .offer-card {
    border: 2px solid #f59e0b;
    background: #fffbf0;
  }

  .empty-card {
    text-align: center;
    padding: 3rem 2rem;
  }

  .capitalize {
    text-transform: capitalize;
  }
`;

export default {
  TrialBadge,
  PricingPage,
  BillingSettings,
};
