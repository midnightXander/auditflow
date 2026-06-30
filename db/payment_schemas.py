"""
Payment-related Pydantic schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class CheckoutLinkRequest(BaseModel):
    """Request to create checkout link"""
    plan_tier: str = Field(..., description="Plan tier: 'pro' or 'agency'")
    
    class Config:
        json_schema_extra = {
            "example": {
                "plan_tier": "pro"
            }
        }


class CheckoutLinkResponse(BaseModel):
    """Response with checkout link"""
    checkout_url: str
    plan_tier: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "checkout_url": "https://whop.com/checkout/...",
                "plan_tier": "pro"
            }
        }


class SubscriptionStatus(BaseModel):
    """User subscription status"""
    plan: str
    subscription_status: str
    subscription_started_at: Optional[datetime]
    subscription_renews_at: Optional[datetime]
    credits_remaining: int
    whop_subscription_id: Optional[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "plan": "pro",
                "subscription_status": "active",
                "subscription_started_at": "2024-04-28T10:00:00",
                "subscription_renews_at": "2024-05-28T10:00:00",
                "credits_remaining": 10000,
                "whop_subscription_id": "sub_123456"
            }
        }


class CancelSubscriptionResponse(BaseModel):
    """Response for subscription cancellation"""
    success: bool
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Subscription cancelled successfully"
            }
        }


class PlanInfo(BaseModel):
    """Plan tier information"""
    name: str
    price: int
    credits: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Pro Plan",
                "price": 29,
                "credits": 10000
            }
        }


class PlansResponse(BaseModel):
    """All available plans"""
    plans: Dict[str, PlanInfo]
    
    class Config:
        json_schema_extra = {
            "example": {
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
        }


class TrialStatus(BaseModel):
    """User trial status"""
    trial_active: bool
    trial_started_at: Optional[datetime]
    trial_ends_at: Optional[datetime]
    trial_used: bool
    days_remaining: Optional[int]
    plan: str
    credits_remaining: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "trial_active": True,
                "trial_started_at": "2024-05-01T10:00:00",
                "trial_ends_at": "2024-05-15T10:00:00",
                "trial_used": False,
                "days_remaining": 10,
                "plan": "pro",
                "credits_remaining": 10000
            }
        }


class StartTrialResponse(BaseModel):
    """Response when starting trial"""
    success: bool
    message: str
    trial_ends_at: datetime
    credits_granted: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "14-day Pro trial started! You now have 10,000 credits.",
                "trial_ends_at": "2024-05-15T10:00:00",
                "credits_granted": 10000
            }
        }


class TrialUpgradeOffer(BaseModel):
    """Upgrade offer after trial expires"""
    trial_expired: bool
    offer_active: bool
    discount_percent: int
    offer_expires_at: datetime
    plan_tier: str
    discounted_price: int
    original_price: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "trial_expired": True,
                "offer_active": True,
                "discount_percent": 30,
                "offer_expires_at": "2024-05-20T10:00:00",
                "plan_tier": "pro",
                "discounted_price": 20,
                "original_price": 29
            }
        }


class WhopWebhookPayload(BaseModel):
    """Whop webhook payload structure"""
    event: str
    data: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "event": "order.completed",
                "data": {
                    "order_id": "order_123",
                    "subscription_id": "sub_123",
                    "product_id": "prod_123",
                    "customer_email": "user@example.com",
                    "metadata": {
                        "user_id": "1",
                        "plan_tier": "pro"
                    }
                }
            }
        }
