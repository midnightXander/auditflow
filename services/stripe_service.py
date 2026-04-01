"""
Stripe Integration - Handle subscriptions and payments
"""

import stripe
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any
from datetime import datetime
from ..db.models import User
load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Price IDs (create these in Stripe Dashboard)
PRICE_PRO_MONTHLY = os.getenv("STRIPE_PRICE_PRO_MONTHLY", "price_pro_monthly")
PRICE_AGENCY_MONTHLY = os.getenv("STRIPE_PRICE_AGENCY_MONTHLY", "price_agency_monthly")


def create_checkout_session(
    user_id: int,
    user_email: str,
    price_id: str,
    success_url: str,
    cancel_url: str
) -> Optional[str]:
    """
    Create Stripe Checkout session for subscription
    
    Returns:
        Checkout session URL or None if error
    """
    try:
        session = stripe.checkout.Session.create(
            customer_email=user_email,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'user_id': str(user_id),
            },
            allow_promotion_codes=True,
        )
        
        return session.url
    except Exception as e:
        print(f"Error creating checkout session: {e}")
        return None


def create_customer_portal_session(
    customer_id: str,
    return_url: str
) -> Optional[str]:
    """
    Create Stripe Customer Portal session for managing subscription
    
    Returns:
        Portal session URL or None if error
    """
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        
        return session.url
    except Exception as e:
        print(f"Error creating portal session: {e}")
        return None


def verify_webhook_signature(payload: bytes, sig_header: str) -> Optional[Dict[str, Any]]:
    """
    Verify Stripe webhook signature
    
    Returns:
        Event dict or None if invalid
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        return event
    except ValueError:
        # Invalid payload
        return None
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return None


def handle_checkout_completed(session: Dict[str, Any], db):
    """
    Handle successful checkout - upgrade user plan
    
    Args:
        session: Stripe checkout session
        db: Database session
    """
   
    
    user_id = int(session['metadata']['user_id'])
    customer_id = session['customer']
    subscription_id = session['subscription']
    
    # Get subscription to determine plan
    subscription = stripe.Subscription.retrieve(subscription_id)
    price_id = subscription['items']['data'][0]['price']['id']
    
    # Determine plan
    if price_id == PRICE_PRO_MONTHLY:
        plan = 'pro'
        credits = 100
    elif price_id == PRICE_AGENCY_MONTHLY:
        plan = 'agency'
        credits = 1000
    else:
        plan = 'free'
        credits = 10
    
    # Update user
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.plan = plan
        user.credits_remaining = credits
        user.stripe_customer_id = customer_id
        user.stripe_subscription_id = subscription_id
        db.commit()
        
        print(f"✅ User {user_id} upgraded to {plan}")


def handle_subscription_updated(subscription: Dict[str, Any], db):
    """Handle subscription updated (plan change, renewal, etc.)"""
    
    
    subscription_id = subscription['id']
    
    user = db.query(User).filter(
        User.stripe_subscription_id == subscription_id
    ).first()
    
    if user:
        # Reset credits on renewal
        price_id = subscription['items']['data'][0]['price']['id']
        
        if price_id == PRICE_PRO_MONTHLY:
            user.credits_remaining = 100
        elif price_id == PRICE_AGENCY_MONTHLY:
            user.credits_remaining = 1000
        
        db.commit()
        print(f"✅ Subscription renewed for user {user.id}")


def handle_subscription_deleted(subscription: Dict[str, Any], db):
    """Handle subscription cancellation"""
    
    
    subscription_id = subscription['id']
    
    user = db.query(User).filter(
        User.stripe_subscription_id == subscription_id
    ).first()
    
    if user:
        user.plan = 'free'
        user.credits_remaining = 10
        user.stripe_subscription_id = None
        db.commit()
        
        print(f"⚠️  User {user.id} downgraded to free (subscription cancelled)")


def cancel_subscription(subscription_id: str) -> bool:
    """Cancel a subscription immediately"""
    try:
        stripe.Subscription.delete(subscription_id)
        return True
    except Exception as e:
        print(f"Error cancelling subscription: {e}")
        return False


def get_subscription_details(subscription_id: str) -> Optional[Dict[str, Any]]:
    """Get subscription details"""
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        return {
            'status': subscription['status'],
            'current_period_end': datetime.fromtimestamp(subscription['current_period_end']),
            'cancel_at_period_end': subscription['cancel_at_period_end'],
            'price_id': subscription['items']['data'][0]['price']['id'],
        }
    except Exception as e:
        print(f"Error retrieving subscription: {e}")
        return None