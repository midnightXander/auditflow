"""
Whop Payment Integration Service
Handles checkout link creation, webhook verification, and subscription management
"""

import os
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import httpx
from sqlalchemy.orm import Session
from db.models import User
import logging
from whop_sdk import Whop
import base64




logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

WHOP_API_KEY = os.getenv("WHOP_API_KEY", "")
WHOP_API_BASE = "https://api.whop.com/api/v1"

# webhook_key must be base64-encoded — the SDK passes it
# straight to the Standard Webhooks verifier, which expects b64.
whopsdk = Whop(
    api_key=WHOP_API_KEY,
    webhook_key=base64.b64encode(os.environ["WHOP_WEBHOOK_SECRET"].encode()).decode(),
)

client = Whop(
    api_key=WHOP_API_KEY,
)
company_id = os.getenv("WHOP_COMPANY_ID", "")

# Plan Configuration
PLAN_CONFIG = {
    "pro": {
        "product_id": os.getenv("WHOP_PRO_PRODUCT_ID", ""),
        "price": 29,
        "credits": 10000,
        "name": "Pro Plan"
    },
    "agency": {
        "product_id": os.getenv("WHOP_AGENCY_PRODUCT_ID", ""),
        "price": 99,
        "credits": 50000,
        "name": "Agency Plan"
    }
}

SUCCESS_URL = os.getenv("WHOP_SUCCESS_URL", "http://localhost:3000/billing/success")
CANCEL_URL = os.getenv("WHOP_CANCEL_URL", "http://localhost:3000/billing/cancelled")
WEBHOOK_SECRET = os.getenv("WHOP_WEBHOOK_SECRET", "")


# ──────────────────────────────────────────────────────────────────────────────
# Whop API Calls
# ──────────────────────────────────────────────────────────────────────────────

async def create_checkout_config(plan_tier: str) -> Optional[Dict[str, Any]]:
    """
    Get checkout configuration for a given plan tier
    
    Args:
        plan_tier: "pro" or "agency"
    
    Returns:
        Dictionary with product_id, price, credits, and name or None if invalid tier
    """
    
    if plan_tier not in PLAN_CONFIG:
        logger.error(f"Invalid plan tier: {plan_tier}")
        return None
    
    return PLAN_CONFIG[plan_tier]

async def create_checkout_link(
    user_id: int,
    plan_tier: str,
    db: Session
) -> Optional[str]:
    """
    Create a Whop checkout link for the specified plan
    
    Args:
        user_id: User ID for metadata
        plan_tier: "pro" or "agency"
        db: Database session
    
    Returns:
        Checkout URL or None if failed
    """

    # return "https://whop.com/checkout/plan_9pqLGZBOb5G6j"
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.error(f"User {user_id} not found")
        return None
    
    if plan_tier not in PLAN_CONFIG:
        logger.error(f"Invalid plan tier: {plan_tier}")
        return None
    
    plan = PLAN_CONFIG[plan_tier]
    product_id = plan["product_id"]
    
    if not product_id or not WHOP_API_KEY:
        logger.error("Whop configuration missing (product_id or API key)")
        return None
    
    try:
        
        checkout = client.checkout_configurations.create(
            plan={
                # "initial_price": plan["price"],
                "plan_type": "renewal",
                "renewal_price" : plan["price"],
                "company_id": company_id,
                "product_id": product_id,
                "currency": "usd",
                # "trial_period_days": 14,
                "billing_period": 30,
                "payment_method_configuration": {
                    "enabled": [
                        "crypto", # low fees
                        "us_bank_transfer", # very low fees
                        "apple_pay", # standard cc rates
                    ],
                    "disabled": [
                        "acss_debit",
                    ],
                },
            },
            metadata = {
                    "user_id": str(user_id),
                    "user_email": user.email,
                    "plan_tier": plan_tier
                },
            redirect_url= SUCCESS_URL
        )

        
        checkout_link = f"https://whop.com/checkout/{checkout.id}/?email={user.email}"
        #encode url to ensure email is passed correctly
        # checkout_link = 
        print("checkout id: ", checkout.id)
        
        return checkout_link

    except Exception as e:
        logger.error(f"Error creating Whop checkout link: {str(e)}")
        return None


async def handle_payment_success(
    subscription_id: str,
    product_id: str,
    customer_email: str,
    metadata: Dict[str, Any],
    trial: Optional[int],
    db: Session
) -> bool:
    """
    Handle successful payment from Whop webhook
    
    Updates user plan, credits, and subscription info
    
    Args:
        subscription_id: Whop subscription ID
        product_id: Whop product ID
        customer_email: Customer email
        metadata: Metadata from webhook (should contain user_id)
        db: Database session
    
    Returns:
        True if successful, False otherwise
    """
    
    # checkout_config = client.checkout_configurations.retrieve("ch_LWf3OIdrIMw2pZM")
    # print(checkout_config)
    
    
    try:
        # Get user ID from metadata
        user_id = metadata.get("user_id")
        if not user_id:
            # Fallback to email lookup
            user = db.query(User).filter(User.email == customer_email).first()
            if not user:
                logger.error(f"Could not find user with email {customer_email}")
                return False
            user_id = user.id
        else:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if not user:
                logger.error(f"User {user_id} not found")
                return False
        
        # Determine plan tier from product_id
        plan_tier = None
        for tier, config in PLAN_CONFIG.items():
            if config["product_id"] == product_id:
                plan_tier = tier
                break
        
        if not plan_tier:
            logger.error(f"Unknown product_id: {product_id}")
            return False
        
        plan = PLAN_CONFIG[plan_tier]
        # plan = "pro"
        
        # Update user subscription
        user.plan = plan_tier
        user.credits_remaining = plan["credits"]
        user.whop_subscription_id = subscription_id
        user.whop_product_id = product_id
        user.subscription_status = "active"
        user.subscription_started_at = datetime.utcnow()
        user.subscription_renews_at = datetime.utcnow() + timedelta(days=30)
        user.whop_metadata = metadata
        user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"✓ Payment success: User {user_id} upgraded to {plan_tier}, subscription {subscription_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error handling payment success: {str(e)}")
        db.rollback()
        return False


async def handle_payment_failed(
    customer_email: str,
    reason: str,
    db: Session
) -> None:
    """
    Handle failed payment from Whop webhook
    
    Args:
        customer_email: Customer email
        reason: Failure reason
        db: Database session
    """
    
    try:
        user = db.query(User).filter(User.email == customer_email).first()
        if user:
            logger.warning(f"Payment failed for user {user.id}: {reason}")
            # Could notify user or take other actions here
    except Exception as e:
        logger.error(f"Error handling payment failure: {str(e)}")


async def cancel_subscription(user_id: int, db: Session) -> bool:
    """
    Cancel user's Whop subscription
    
    Args:
        user_id: User ID
        db: Database session
    
    Returns:
        True if successful, False otherwise
    """
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.whop_subscription_id:
            logger.error(f"User {user_id} not found or no subscription")
            return False
        
        subscription_id = user.whop_subscription_id
        
        # Call Whop API to cancel subscription
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {WHOP_API_KEY}",
                "Content-Type": "application/json"
            }
            
            response = await client.post(
                f"{WHOP_API_BASE}/subscription/{subscription_id}/cancel",
                headers=headers,
                timeout=10.0
            )
            
            response.raise_for_status()
        
        # Update user record
        user.subscription_status = "cancelled"
        user.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"✓ Cancelled subscription for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error cancelling subscription: {str(e)}")
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Webhook Verification
# ──────────────────────────────────────────────────────────────────────────────

def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """
    Verify Whop webhook signature
    
    Args:
        body: Raw request body
        signature: X-Whop-Signature header value
    
    Returns:
        True if signature is valid, False otherwise
    """
    
    if not WEBHOOK_SECRET:
        logger.warning("WHOP_WEBHOOK_SECRET not set - skipping signature verification")
        return True  # For development
    
    try:
        # Whop uses HMAC-SHA256
        computed_signature = hmac.new(
            WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(computed_signature, signature)
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {str(e)}")
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Trial Management
# ──────────────────────────────────────────────────────────────────────────────

async def start_free_trial(user_id: int, db: Session) -> tuple[bool, str, Optional[datetime]]:
    """
    Start 14-day free trial for Pro plan
    Returns: (success, message, trial_ends_at)
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return False, "User not found", None
    
    # Check if user already used trial
    if user.trial_used:
        return False, "You have already used your free trial", None
    
    # Check if user is already in trial
    if user.trial_started_at and user.trial_ends_at and datetime.utcnow() < user.trial_ends_at:
        days_left = (user.trial_ends_at - datetime.utcnow()).days
        return False, f"You are already in a trial with {days_left} days remaining", None
    
    # Start trial
    trial_start = datetime.utcnow()
    trial_end = trial_start + timedelta(days=14)
    
    user.trial_started_at = trial_start
    user.trial_ends_at = trial_end
    user.trial_used = True
    user.trial_plan = "pro"
    user.plan = "pro"
    user.credits_remaining = 10000  # Unlimited for Pro, but set high number
    user.subscription_status = "trial"
    user.trial_email_sent_start = False
    user.trial_email_sent_day3 = False
    user.trial_email_sent_day10 = False
    user.trial_email_sent_expiring_soon = False
    user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"Started 14-day trial for user {user_id}, expires {trial_end}")
    
    return True, "14-day Pro trial started! You now have 10,000 credits.", trial_end


def get_trial_status(user: User) -> Dict[str, Any]:
    """Get user's trial status"""
    now = datetime.utcnow()
    trial_active = False
    days_remaining = None
    
    if user.trial_started_at and user.trial_ends_at:
        if now < user.trial_ends_at:
            trial_active = True
            days_remaining = (user.trial_ends_at - now).days + 1
        else:
            # Trial has expired but not converted yet
            trial_active = False
    
    return {
        "trial_active": trial_active,
        "trial_started_at": user.trial_started_at,
        "trial_ends_at": user.trial_ends_at,
        "trial_used": user.trial_used,
        "days_remaining": days_remaining,
        "plan": user.plan,
        "credits_remaining": user.credits_remaining
    }


async def handle_trial_expiration(user_id: int, db: Session) -> bool:
    """
    Handle trial expiration - revert to free plan
    Called via scheduled task or webhook
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return False
    
    # Check if trial has expired
    if user.subscription_status != "trial" or not user.trial_ends_at:
        return False
    
    if datetime.utcnow() < user.trial_ends_at:
        return False  # Trial not expired yet
    
    # Revert to free plan
    user.plan = "free"
    user.subscription_status = "expired"
    user.credits_remaining = 20  # Free plan credits
    user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"Trial expired for user {user_id}, reverted to free plan")
    return True


def get_trial_email_reminders(user: User) -> Dict[str, bool]:
    """Get which trial reminder emails have been sent"""
    now = datetime.utcnow()
    days_since_start = None
    
    if user.trial_started_at:
        days_since_start = (now - user.trial_started_at).days
    
    return {
        "should_send_start": (
            user.trial_started_at and 
            days_since_start == 0 and 
            not user.trial_email_sent_start
        ),
        "should_send_day3": (
            user.trial_started_at and 
            days_since_start >= 3 and 
            not user.trial_email_sent_day3
        ),
        "should_send_day10": (
            user.trial_started_at and 
            days_since_start >= 10 and 
            not user.trial_email_sent_day10
        ),
        "should_send_expiring_soon": (
            user.trial_started_at and 
            user.trial_ends_at and
            (user.trial_ends_at - now).days <= 1 and
            not user.trial_email_sent_expiring_soon
        ),
    }


def mark_trial_email_sent(user_id: int, email_type: str, db: Session) -> bool:
    """Mark a trial email as sent to prevent duplicates"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return False
    
    if email_type == "start":
        user.trial_email_sent_start = True
    elif email_type == "day3":
        user.trial_email_sent_day3 = True
    elif email_type == "day10":
        user.trial_email_sent_day10 = True
    elif email_type == "expiring_soon":
        user.trial_email_sent_expiring_soon = True
    
    db.commit()
    return True


def get_trial_upgrade_offer(user: User) -> Dict[str, Any]:
    """
    Get upgrade offer after trial expires
    30% discount for first month if upgrading within 3 days of trial end
    """
    now = datetime.utcnow()
    offer_active = False
    discount_percent = 30
    
    if user.subscription_status == "expired" and user.trial_ends_at:
        days_since_expiration = (now - user.trial_ends_at).days
        if 0 <= days_since_expiration <= 3:
            offer_active = True
    
    if offer_active:
        pro_original_price = PLAN_CONFIG["pro"]["price"]
        pro_discounted_price = int(pro_original_price * (1 - discount_percent / 100))
        
        return {
            "trial_expired": True,
            "offer_active": True,
            "discount_percent": discount_percent,
            "offer_expires_at": user.trial_ends_at + timedelta(days=3),
            "plan_tier": "pro",
            "discounted_price": pro_discounted_price,
            "original_price": pro_original_price
        }
    
    return {
        "trial_expired": user.subscription_status == "expired",
        "offer_active": False,
        "discount_percent": 0,
        "offer_expires_at": None,
        "plan_tier": "pro",
        "discounted_price": PLAN_CONFIG["pro"]["price"],
        "original_price": PLAN_CONFIG["pro"]["price"]
    }


async def upgrade_from_trial(user_id: int, plan_tier: str, db: Session) -> bool:
    """Upgrade user from trial to paid plan"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return False
    
    # Check if user is on trial
    if user.subscription_status != "trial" and user.subscription_status != "expired":
        return False
    
    plan_info = get_plan_info(plan_tier)
    if not plan_info:
        return False
    
    # Update user
    user.plan = plan_tier
    user.subscription_status = "active"
    user.subscription_started_at = datetime.utcnow()
    user.subscription_renews_at = datetime.utcnow() + timedelta(days=30)
    user.credits_remaining = plan_info["credits"]
    user.trial_started_at = None
    user.trial_ends_at = None
    user.trial_plan = None
    user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"User {user_id} upgraded from trial to {plan_tier} plan")
    return True


# ──────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────────────────────────────────────

def get_plan_info(plan_tier: str) -> Optional[Dict[str, Any]]:
    """Get plan configuration"""
    return PLAN_CONFIG.get(plan_tier)


def get_all_plans() -> Dict[str, Dict[str, Any]]:
    """Get all plan configurations"""
    return PLAN_CONFIG
