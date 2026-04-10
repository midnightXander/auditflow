"""
Visitor Tracking Service
Track landing page visitors for conversion analysis
Uses GeoIP for location detection
"""

import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from db.models import Visitor


logger = logging.getLogger(__name__)


class GeoIPService:
    """Get geolocation from IP address using free APIs"""
    
    # Multiple free GeoIP services for fallback
    SERVICES = [
        "https://ipapi.co/{ip}/json/",  # Free tier: 30k/month
        "https://ip-api.com/json/{ip}",  # Free tier: 45 req/min
        "https://api.geoip.rs/?ip={ip}",  # Free tier: no limit (slow)
    ]
    
    @staticmethod
    async def get_geolocation(ip_address: str, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        Get geolocation data from IP address
        
        Args:
            ip_address: IP address to geolocate
            timeout: Request timeout in seconds
        
        Returns:
            Dict with country, city, lat, lon or None if failed
        """
        
        # Skip private/local IPs
        if GeoIPService._is_private_ip(ip_address):
            return {
                "ip": ip_address,
                "country": "Local",
                "country_code": "XX",
                "city": "Local Network",
                "latitude": None,
                "longitude": None
            }
        
        # Try each service until one succeeds
        for service_url in GeoIPService.SERVICES:
            try:
                url = service_url.format(ip=ip_address)
                
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(url)
                    
                    if response.status_code != 200:
                        continue
                    
                    data = response.json()
                    
                    # Parse response based on service
                    if "ip-api" in service_url:
                        if data.get('status') == 'success':
                            return {
                                "ip": ip_address,
                                "country": data.get('country', 'Unknown'),
                                "country_code": data.get('countryCode', 'XX'),
                                "city": data.get('city', 'Unknown'),
                                "latitude": data.get('lat'),
                                "longitude": data.get('lon')
                            }
                    
                    elif "ipapi.co" in service_url:
                        return {
                            "ip": ip_address,
                            "country": data.get('country_name', 'Unknown'),
                            "country_code": data.get('country_code', 'XX'),
                            "city": data.get('city', 'Unknown'),
                            "latitude": float(data.get('latitude')) if data.get('latitude') else None,
                            "longitude": float(data.get('longitude')) if data.get('longitude') else None
                        }
                    
                    elif "geoip.rs" in service_url:
                        return {
                            "ip": ip_address,
                            "country": data.get('country_name', 'Unknown'),
                            "country_code": data.get('country_code', 'XX'),
                            "city": data.get('city', 'Unknown'),
                            "latitude": data.get('latitude'),
                            "longitude": data.get('longitude')
                        }
            
            except (httpx.TimeoutException, httpx.RequestError) as e:
                logger.warning(f"GeoIP service {service_url} failed: {e}")
                continue
            except Exception as e:
                logger.error(f"Error parsing GeoIP response: {e}")
                continue
        
        # If all services fail, return None
        logger.warning(f"All GeoIP services failed for IP {ip_address}")
        return None
    
    @staticmethod
    def _is_private_ip(ip_address: str) -> bool:
        """Check if IP is private/local"""
        private_ranges = [
            "127.",  # Loopback
            "192.168.",  # Private
            "10.",  # Private
            "172.16.", "172.17.", "172.18.", "172.19.",
            "172.20.", "172.21.", "172.22.", "172.23.",
            "172.24.", "172.25.", "172.26.", "172.27.",
            "172.28.", "172.29.", "172.30.", "172.31.",  # Private
            "::1",  # IPv6 loopback
            "fc00:", "fd00:",  # IPv6 private
            "169.254.",  # Link-local
        ]
        
        return any(ip_address.startswith(r) for r in private_ranges)


def extract_ip_from_request(request) -> str:
    """
    Extract IP address from FastAPI request
    Handles X-Forwarded-For header (for proxies/load balancers)
    """
    
    # Check X-Forwarded-For header first (for proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get first IP in chain
        return forwarded_for.split(",")[0].strip()
    
    # Check other proxy headers
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection IP
    return request.client.host


async def track_visitor(
    db: Session,
    request,
    page_url: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[Visitor]:
    """
    Track a visitor to the landing page
    
    Args:
        db: Database session
        request: FastAPI request object
        page_url: Optional URL being visited
        user_agent: Optional user agent string
    
    Returns:
        Visitor record or None if tracking failed
    """
    
    try:
        # Extract IP address
        ip_address = extract_ip_from_request(request)
        
        # Get user agent
        if not user_agent:
            user_agent = request.headers.get("User-Agent", "Unknown")
        
        # Get referer
        referer = request.headers.get("Referer")
        
        # Get page URL
        if not page_url:
            page_url = str(request.url)
        
        logger.info(f"[VISITOR] Tracking IP {ip_address} from {page_url}")
        
        # Get geolocation
        geo_data = await GeoIPService.get_geolocation(ip_address)
        
        # Create visitor record
        visitor = Visitor(
            ip_address=ip_address,
            country=geo_data.get('country') if geo_data else 'Unknown',
            country_code=geo_data.get('country_code') if geo_data else 'XX',
            city=geo_data.get('city') if geo_data else None,
            latitude=geo_data.get('latitude') if geo_data else None,
            longitude=geo_data.get('longitude') if geo_data else None,
            user_agent=user_agent,
            referer=referer,
            page_url=page_url,
            visited_at=datetime.utcnow()
        )
        
        db.add(visitor)
        db.commit()
        db.refresh(visitor)
        
        logger.info(f"[VISITOR] Tracked: {visitor.country} ({visitor.ip_address})")
        
        return visitor
    
    except Exception as e:
        logger.error(f"[VISITOR] Error tracking visitor: {e}")
        return None


def get_visitor_analytics(db: Session, days: int = 30) -> Dict[str, Any]:
    """Get visitor analytics for the past N days"""
    
    from datetime import timedelta
    from sqlalchemy import func
    
    since = datetime.utcnow() - timedelta(days=days)
    
    # Total visitors
    total = db.query(Visitor).filter(Visitor.visited_at >= since).count()
    
    # Unique IPs
    unique_ips = db.query(func.count(func.distinct(Visitor.ip_address)))\
        .filter(Visitor.visited_at >= since).scalar()
    
    # Conversions
    conversions = db.query(Visitor).filter(
        Visitor.visited_at >= since,
        Visitor.converted == True
    ).count()
    
    # By country
    by_country = db.query(
        Visitor.country,
        Visitor.country_code,
        func.count(Visitor.id).label('count')
    ).filter(Visitor.visited_at >= since)\
        .group_by(Visitor.country, Visitor.country_code)\
        .order_by(func.count(Visitor.id).desc())\
        .limit(10)\
        .all()
    
    # By referrer
    by_referrer = db.query(
        Visitor.referer,
        func.count(Visitor.id).label('count')
    ).filter(
        Visitor.visited_at >= since,
        Visitor.referer != None
    ).group_by(Visitor.referer)\
        .order_by(func.count(Visitor.id).desc())\
        .limit(10)\
        .all()
    
    # Conversion rate
    conversion_rate = (conversions / total * 100) if total > 0 else 0
    
    return {
        "period_days": days,
        "total_visits": total,
        "unique_visitors": unique_ips,
        "conversions": conversions,
        "conversion_rate": round(conversion_rate, 2),
        "top_countries": [
            {"country": c[0], "code": c[1], "count": c[2]} for c in by_country
        ],
        "top_referrers": [
            {"referrer": r[0], "count": r[1]} for r in by_referrer if r[0]
        ]
    }


def mark_visitor_converted(db: Session, ip_address: str, user_id: int):
    """Mark a visitor as converted when they sign up/become a customer"""
    
    visitor = db.query(Visitor).filter(Visitor.ip_address == ip_address).first()
    if visitor:
        visitor.converted = True
        visitor.converted_user_id = user_id
        db.commit()
        logger.info(f"[VISITOR] Marked {ip_address} as converted (user {user_id})")
        return visitor
    
    return None
