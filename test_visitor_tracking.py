"""
Test Visitor Tracking Endpoints
Run with: pytest test_visitor_tracking.py
"""

import pytest
import httpx
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import Visitor, User
from services.visitor_tracking import (
    GeoIPService, extract_ip_from_request, track_visitor, 
    get_visitor_analytics, mark_visitor_converted
)


# ──────────────────────────────────────────────────────────────────────────────
# Test GeoIP Service
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_geoip_public_ip():
    """Test geolocation of public IP"""
    geo = await GeoIPService.get_geolocation("8.8.8.8")  # Google DNS
    
    assert geo is not None
    assert geo['country'] is not None
    assert geo['country_code'] is not None
    assert len(geo['country_code']) == 2
    print(f"✓ Geolocation test: {geo['country']} ({geo['country_code']})")


@pytest.mark.asyncio
async def test_geoip_private_ip():
    """Test that private IPs are handled"""
    geo = await GeoIPService.get_geolocation("192.168.1.1")
    
    assert geo is not None
    assert geo['country'] == "Local"
    print("✓ Private IP handled correctly")


def test_private_ip_detection():
    """Test private IP detection"""
    assert GeoIPService._is_private_ip("127.0.0.1") is True
    assert GeoIPService._is_private_ip("192.168.1.1") is True
    assert GeoIPService._is_private_ip("10.0.0.1") is True
    assert GeoIPService._is_private_ip("172.16.0.1") is True
    assert GeoIPService._is_private_ip("::1") is True
    
    assert GeoIPService._is_private_ip("8.8.8.8") is False
    assert GeoIPService._is_private_ip("203.0.113.45") is False
    
    print("✓ Private IP detection working")


# ──────────────────────────────────────────────────────────────────────────────
# Test Database Operations
# ──────────────────────────────────────────────────────────────────────────────

def test_create_visitor():
    """Test creating a visitor record"""
    db = SessionLocal()
    
    try:
        visitor = Visitor(
            ip_address="203.0.113.45",
            country="United States",
            country_code="US",
            city="San Francisco",
            latitude=37.7749,
            longitude=-122.4194,
            user_agent="Mozilla/5.0",
            referer="https://google.com",
            page_url="https://auditflow.com/pricing",
            visited_at=datetime.utcnow()
        )
        
        db.add(visitor)
        db.commit()
        db.refresh(visitor)
        
        assert visitor.id is not None
        assert visitor.ip_address == "203.0.113.45"
        assert visitor.country == "United States"
        
        # Cleanup
        db.delete(visitor)
        db.commit()
        
        print(f"✓ Visitor record created and deleted: {visitor.id}")
    
    finally:
        db.close()


def test_visitor_analytics():
    """Test analytics calculations"""
    db = SessionLocal()
    
    try:
        # Create test visitors
        for i in range(5):
            visitor = Visitor(
                ip_address=f"203.0.113.{i}",
                country="United States" if i < 3 else "United Kingdom",
                country_code="US" if i < 3 else "GB",
                visited_at=datetime.utcnow()
            )
            if i < 2:
                visitor.converted = True
                visitor.converted_user_id = 1
            
            db.add(visitor)
        
        db.commit()
        
        # Get analytics
        analytics = get_visitor_analytics(db, days=1)
        
        assert analytics['total_visits'] >= 5
        assert analytics['conversions'] >= 2
        assert analytics['conversion_rate'] >= 0
        assert len(analytics['top_countries']) > 0
        
        # Cleanup
        for visitor in db.query(Visitor).filter(Visitor.ip_address.like("203.0.113.%")).all():
            db.delete(visitor)
        db.commit()
        
        print(f"✓ Analytics test passed")
        print(f"  Total: {analytics['total_visits']}, Conversions: {analytics['conversions']}")
    
    finally:
        db.close()


def test_mark_visitor_converted():
    """Test marking visitor as converted"""
    db = SessionLocal()
    
    try:
        # Create visitor
        visitor = Visitor(
            ip_address="203.0.113.99",
            country="Canada",
            country_code="CA",
            visited_at=datetime.utcnow(),
            converted=False
        )
        db.add(visitor)
        db.commit()
        db.refresh(visitor)
        
        assert visitor.converted is False
        
        # Mark as converted
        mark_visitor_converted(db, "203.0.113.99", user_id=42)
        
        # Verify
        updated_visitor = db.query(Visitor).filter(Visitor.ip_address == "203.0.113.99").first()
        assert updated_visitor.converted is True
        assert updated_visitor.converted_user_id == 42
        
        # Cleanup
        db.delete(updated_visitor)
        db.commit()
        
        print("✓ Visitor conversion marking works")
    
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────────────────────
# Integration Tests (requires running API)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_track_visitor_endpoint():
    """Test the track visitor endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/track/visitor",
            params={
                "page_url": "https://auditflow.com",
                "utm_source": "google",
                "utm_medium": "cpc",
                "utm_campaign": "test"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'tracked'
        assert data['visitor_id'] is not None
        assert data['country'] is not None
        
        print(f"✓ Track visitor endpoint working: {data['visitor_id']}")


@pytest.mark.asyncio
async def test_analytics_endpoint(auth_token: str):
    """Test the analytics endpoint (requires auth)"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await client.get(
            "http://localhost:8000/api/visitors/analytics?days=7",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'analytics' in data
        assert 'total_visits' in data['analytics']
        assert 'conversion_rate' in data['analytics']
        
        print(f"✓ Analytics endpoint working")
        print(f"  Total visits: {data['analytics']['total_visits']}")
        print(f"  Conversion rate: {data['analytics']['conversion_rate']}%")


@pytest.mark.asyncio
async def test_list_visitors_endpoint(auth_token: str):
    """Test the list visitors endpoint"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await client.get(
            "http://localhost:8000/api/visitors/list?page=1&page_size=10",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'items' in data
        assert 'total' in data
        
        print(f"✓ List visitors endpoint working")
        print(f"  Total visitors: {data['total']}")


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def auth_token():
    """Get authentication token for tests"""
    # Create test user and return token
    # This depends on your auth setup
    return "test-token-here"


# ──────────────────────────────────────────────────────────────────────────────
# Run Tests
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🧪 Running Visitor Tracking Tests\n")
    
    # Run unit tests
    print("📋 Unit Tests:")
    test_private_ip_detection()
    test_create_visitor()
    test_visitor_analytics()
    test_mark_visitor_converted()
    
    # Run async tests
    print("\n⚡ Async Tests:")
    asyncio.run(test_geoip_public_ip())
    asyncio.run(test_geoip_private_ip())
    
    # Integration tests (uncomment if API is running)
    # print("\n🌐 Integration Tests (requires API running):")
    # asyncio.run(test_track_visitor_endpoint())
    
    print("\n✅ All tests passed!")
