// Frontend Integration Examples - React/TypeScript

// ──────────────────────────────────────────────────────────────────────────────
// 1. Pricing Page Component
// ──────────────────────────────────────────────────────────────────────────────

import React, { useEffect, useState } from 'react';
import { useAuth } from './context/AuthContext';

interface Plan {
  name: string;
  price: number;
  credits: number;
}

export const PricingPage = () => {
  const { authToken } = useAuth();
  const [plans, setPlans] = useState<Record<string, Plan>>({});
  const [loading, setLoading] = useState(false);
  const [currentPlan, setCurrentPlan] = useState<string>('free');

  useEffect(() => {
    fetchPlans();
    fetchCurrentPlan();
  }, []);

  const fetchPlans = async () => {
    try {
      const response = await fetch('/api/billing/plans');
      const data = await response.json();
      setPlans(data.plans);
    } catch (error) {
      console.error('Error fetching plans:', error);
    }
  };

  const fetchCurrentPlan = async () => {
    if (!authToken) return;
    try {
      const response = await fetch('/api/billing/subscription', {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      const data = await response.json();
      setCurrentPlan(data.plan);
    } catch (error) {
      console.error('Error fetching subscription:', error);
    }
  };

  const handleUpgrade = async (planTier: string) => {
    if (!authToken) {
      // Redirect to login
      window.location.href = '/login';
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/billing/checkout-link', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ plan_tier: planTier })
      });

      if (!response.ok) {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
        return;
      }

      const data = await response.json();
      // Redirect to Whop checkout
      window.location.href = data.checkout_url;
    } catch (error) {
      console.error('Error creating checkout:', error);
      alert('Failed to create checkout. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pricing-container">
      <h1>Choose Your Plan</h1>
      
      <div className="pricing-grid">
        {/* Free Plan */}
        <div className="plan-card">
          <h2>Free</h2>
          <p className="price">$0<span>/month</span></p>
          <p className="credits">20 credits/month</p>
          <button 
            disabled={currentPlan === 'free'}
            className="btn-secondary"
          >
            {currentPlan === 'free' ? 'Current Plan' : 'Continue as Free'}
          </button>
        </div>

        {/* Pro Plan */}
        {plans.pro && (
          <div className="plan-card highlighted">
            <h2>{plans.pro.name}</h2>
            <p className="price">${plans.pro.price}<span>/month</span></p>
            <p className="credits">{plans.pro.credits.toLocaleString()} credits/month</p>
            <button 
              onClick={() => handleUpgrade('pro')}
              disabled={loading || currentPlan === 'pro'}
              className="btn-primary"
            >
              {loading ? 'Processing...' : currentPlan === 'pro' ? 'Current Plan' : 'Upgrade to Pro'}
            </button>
          </div>
        )}

        {/* Agency Plan */}
        {plans.agency && (
          <div className="plan-card">
            <h2>{plans.agency.name}</h2>
            <p className="price">${plans.agency.price}<span>/month</span></p>
            <p className="credits">{plans.agency.credits.toLocaleString()} credits/month</p>
            <button 
              onClick={() => handleUpgrade('agency')}
              disabled={loading || currentPlan === 'agency'}
              className="btn-primary"
            >
              {loading ? 'Processing...' : currentPlan === 'agency' ? 'Current Plan' : 'Upgrade to Agency'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

// ──────────────────────────────────────────────────────────────────────────────
// 2. Billing Settings Component
// ──────────────────────────────────────────────────────────────────────────────

export const BillingSettings = () => {
  const { authToken } = useAuth();
  const [subscription, setSubscription] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchSubscription();
  }, []);

  const fetchSubscription = async () => {
    if (!authToken) return;
    try {
      const response = await fetch('/api/billing/subscription', {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      const data = await response.json();
      setSubscription(data);
    } catch (error) {
      console.error('Error fetching subscription:', error);
    }
  };

  const handleCancelSubscription = async () => {
    if (!window.confirm('Are you sure you want to cancel your subscription?')) {
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/billing/cancel-subscription', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${authToken}` }
      });

      if (!response.ok) {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
        return;
      }

      alert('Subscription cancelled successfully');
      fetchSubscription();
    } catch (error) {
      console.error('Error cancelling subscription:', error);
      alert('Failed to cancel subscription. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!subscription) {
    return <div>Loading...</div>;
  }

  return (
    <div className="billing-settings">
      <h2>Billing & Subscription</h2>
      
      <div className="subscription-info">
        <div className="info-row">
          <span className="label">Plan:</span>
          <span className="value">{subscription.plan.toUpperCase()}</span>
        </div>

        <div className="info-row">
          <span className="label">Status:</span>
          <span className={`status ${subscription.subscription_status}`}>
            {subscription.subscription_status.toUpperCase()}
          </span>
        </div>

        <div className="info-row">
          <span className="label">Credits Remaining:</span>
          <span className="value">{subscription.credits_remaining.toLocaleString()}</span>
        </div>

        {subscription.subscription_started_at && (
          <div className="info-row">
            <span className="label">Started:</span>
            <span className="value">
              {new Date(subscription.subscription_started_at).toLocaleDateString()}
            </span>
          </div>
        )}

        {subscription.subscription_renews_at && (
          <div className="info-row">
            <span className="label">Renews:</span>
            <span className="value">
              {new Date(subscription.subscription_renews_at).toLocaleDateString()}
            </span>
          </div>
        )}
      </div>

      {subscription.subscription_status === 'active' && (
        <button 
          onClick={handleCancelSubscription}
          disabled={loading}
          className="btn-danger"
        >
          {loading ? 'Cancelling...' : 'Cancel Subscription'}
        </button>
      )}
    </div>
  );
};

// ──────────────────────────────────────────────────────────────────────────────
// 3. Success Page After Payment
// ──────────────────────────────────────────────────────────────────────────────

export const SuccessPage = () => {
  const { authToken } = useAuth();
  const [subscription, setSubscription] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Small delay to ensure webhook has been processed
    const timer = setTimeout(() => {
      fetchSubscription();
    }, 2000);

    return () => clearTimeout(timer);
  }, []);

  const fetchSubscription = async () => {
    if (!authToken) return;
    try {
      const response = await fetch('/api/billing/subscription', {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      const data = await response.json();
      setSubscription(data);
    } catch (error) {
      console.error('Error fetching subscription:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="success-page loading">Loading subscription details...</div>;
  }

  return (
    <div className="success-page">
      <div className="success-card">
        <h1>🎉 Payment Successful!</h1>
        
        <p className="subtitle">Your subscription has been activated</p>

        <div className="plan-details">
          <h2>{subscription?.plan.toUpperCase()} Plan</h2>
          <p className="credits">
            {subscription?.credits_remaining.toLocaleString()} Credits
          </p>
          <p className="renewal">
            Next renewal: {new Date(subscription?.subscription_renews_at).toLocaleDateString()}
          </p>
        </div>

        <div className="actions">
          <button className="btn-primary" onClick={() => window.location.href = '/dashboard'}>
            Go to Dashboard
          </button>
          <button className="btn-secondary" onClick={() => window.location.href = '/billing'}>
            View Billing
          </button>
        </div>
      </div>
    </div>
  );
};

// ──────────────────────────────────────────────────────────────────────────────
// 4. API Service (TypeScript)
// ──────────────────────────────────────────────────────────────────────────────

class BillingService {
  private baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  async getPlans() {
    const response = await fetch(`${this.baseURL}/api/billing/plans`);
    return response.json();
  }

  async createCheckoutLink(planTier: string, authToken: string) {
    const response = await fetch(`${this.baseURL}/api/billing/checkout-link`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ plan_tier: planTier })
    });
    return response.json();
  }

  async getSubscription(authToken: string) {
    const response = await fetch(`${this.baseURL}/api/billing/subscription`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    return response.json();
  }

  async cancelSubscription(authToken: string) {
    const response = await fetch(`${this.baseURL}/api/billing/cancel-subscription`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    return response.json();
  }
}

export const billingService = new BillingService();

// ──────────────────────────────────────────────────────────────────────────────
// 5. CSS Styles (Example)
// ──────────────────────────────────────────────────────────────────────────────

/*
.pricing-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin: 2rem 0;
}

.plan-card {
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  padding: 2rem;
  text-align: center;
  transition: all 0.3s;
}

.plan-card.highlighted {
  border-color: #0075FF;
  box-shadow: 0 10px 40px rgba(0, 117, 255, 0.1);
}

.plan-card h2 {
  margin: 0 0 1rem;
  font-size: 1.5rem;
  color: #1f2937;
}

.price {
  font-size: 2.5rem;
  font-weight: 700;
  color: #0075FF;
  margin: 1rem 0;
}

.price span {
  font-size: 0.8rem;
  color: #666;
  margin-left: 0.5rem;
}

.credits {
  color: #666;
  margin: 1rem 0;
}

.btn-primary,
.btn-secondary {
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  border: none;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 1rem;
}

.btn-primary {
  background: #0075FF;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #0056cc;
}

.btn-secondary {
  background: #f0f0f0;
  color: #1f2937;
}

.btn-secondary:hover:not(:disabled) {
  background: #e0e0e0;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
*/
