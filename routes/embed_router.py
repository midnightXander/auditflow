"""
Embeddable Widget - Allow agencies to embed audit tool on their websites
"""
from datetime import timedelta, datetime
from fastapi import APIRouter,Body, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import uuid
from starlette.concurrency import run_in_threadpool

import os

from db.database import get_db
from db.models import User, Audit, EmbedLead
from db.auth import can_use_feature, get_current_user
from services.email_service import send_email
from auditor import WebsiteAuditor
from services.pdf_generator import PDFReportGenerator
from tasks import run_audit_task

from rq_app import queue
from rq import Retry

router = APIRouter(prefix="/api/embed", tags=["embed"])



# ──────────────────────────────────────────────────────────────────────────────
# Widget Configuration
# ──────────────────────────────────────────────────────────────────────────────

def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values back to hex color string."""
    return "#{:02x}{:02x}{:02x}".format(r, g, b)


def lighten_hex(hex_color: str, percent: float = 20) -> str:
    """Lighten a hex color by a given percentage (default 20%)."""
    r, g, b = hex_to_rgb(hex_color)
    factor = percent / 100
    new_r = min(255, round(r + (255 - r) * factor))
    new_g = min(255, round(g + (255 - g) * factor))
    new_b = min(255, round(b + (255 - b) * factor))
    return rgb_to_hex(new_r, new_g, new_b)


def darken_hex(hex_color: str, percent: float = 20) -> str:
    """Darken a hex color by a given percentage (default 20%)."""
    r, g, b = hex_to_rgb(hex_color)
    factor = 1 - percent / 100
    new_r = max(0, round(r * factor))
    new_g = max(0, round(g * factor))
    new_b = max(0, round(b * factor))
    return rgb_to_hex(new_r, new_g, new_b)







@router.get("/widget.js")
async def get_widget_script(
    api_key: str,
    db: Session = Depends(get_db)
):
    """
    Get embeddable widget JavaScript with modern UI
    
    Usage:
    <script src="https://api.auditflow.com/api/embed/widget.js?api_key=YOUR_KEY"></script>
    <div id="auditflow-widget"></div>
    """
    
    # Verify API key and get agency settings
    user = db.query(User).filter(User.embed_api_key == api_key).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Generate widget configuration
    print(user.embed_border_radius)
    API_BASE = os.getenv("BACKEND_URL","http://localhost:8000")
    config = {
        "apiKey": api_key,
        "agencyName": user.agency_name or "OutAudits",
        "accentColor": user.embed_primary_color or "#1F2937",
        "bgColor": user.embed_bg_color,
        "textColor": user.embed_text_color,
        "showPoweredBy" : 'true' if user.embed_show_poweredBy else '',
        "logo": user.agency_logo or "None",
        "inputBgColor": lighten_hex(user.embed_bg_color),
        "borderRadius": user.embed_border_radius,
        "leadCaptureEnabled": 'true' if user.embed_lead_capture else '',
        "requireEmail": 'true' if user.embed_require_email else "",
        "buttonText": user.embed_button_text or "Analyze Website",
        "headlineText": user.embed_headline or "Free Website SEO Audit",
        "descriptionText": user.embed_description or "Get a comprehensive SEO analysis in seconds",
    }
    
    
    # Widget JavaScript template with modern UI and in-widget results
    widget_js = f"""
(function() {{
  const CONFIG = {config};
  const API_BASE = '{API_BASE}';
  
  // Get origin for CORS
  const getApiBase = () => {{
    try {{
      return new URL(document.currentScript?.src || '').origin.replace('/api/embed/widget.js', '');
    }} catch (e) {{
      return API_BASE;
    }}
  }};
  console.log(getApiBase())
  
  // Create widget container
  const createWidget = () => {{
    const container = document.getElementById('auditflow-widget');
    if (!container) {{
      console.error('AuditFlow: Container #auditflow-widget not found');
      return;
    }}
    
    // Inject styles with modern minimalist design
    const style = document.createElement('style');
    style.textContent = `
      .af-widget {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        max-width: 700px;
        margin: 0 auto;
        padding: 32px 20px;
      }}
      .af-card {{
        background: ${{CONFIG.bgColor}};
        border-radius: ${{CONFIG.borderRadius}}px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 10px 40px rgba(0,0,0,0.08);
        padding: 48px 32px;
        text-align: center;
      }}
      .af-logo {{
        width: 100px;
        height: auto;
        margin: 0 auto;
        margin-bottom: 24px;
      }}
      .af-headline {{
        font-size: 28px;
        font-weight: 700;
        color: ${{CONFIG.textColor}};
        margin-bottom: 8px;
        letter-spacing: -0.5px;
      }}
      .af-description {{
        font-size: 15px;
        color: #6b7280;
        margin-bottom: 32px;
        line-height: 1.6;
      }}
      .af-poweredBy{{
        margin-top: 13px;
        color: #6b7280;
        font-size: 15px;
      }}
      .af-form {{
        display: flex;
        flex-direction: column;
        gap: 12px;
      }}
      .af-input {{
        padding: 12px 16px;
        border-radius: ${{CONFIG.borderRadius}}px;
        font-size: 15px;
        transition: all 0.2s;
        font-family: inherit;
        background: ${{CONFIG.inputBgColor}};;
      }}
      .af-input:focus {{
        outline: none;
        border-color: ${{CONFIG.accentColor}};
        background: white;
        box-shadow: 0 0 0 3px rgba(31, 41, 55, 0.1);
      }}
      .af-button {{
        padding: 12px 24px;
        background: ${{CONFIG.accentColor}};
        color: white;
        border: none;
        border-radius: ${{CONFIG.borderRadius}}px;;
        font-size: 15px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
        font-family: inherit;
      }}
      .af-button:hover {{
        opacity: 0.9;
        transform: translateY(-1px);
      }}
      .af-button:disabled {{
        opacity: 0.5;
        cursor: not-allowed;
        transform: none;
      }}
      .af-loading {{
        margin-top: 24px;
        text-align: center;
      }}
      .af-spinner {{
        border: 3px solid #e5e7eb;
        border-top: 3px solid ${{CONFIG.accentColor}};
        border-radius: 50%;
        width: 36px;
        height: 36px;
        animation: spin 1s linear infinite;
        margin: 0 auto;
      }}
      @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
      }}
      .af-progress {{
        margin-top: 12px;
        font-size: 14px;
        color: #6b7280;
      }}
      .af-error {{
        background: #fef2f2;
        color: #991b1b;
        padding: 12px 16px;
        border-radius: 8px;
        margin-top: 16px;
        border: 1px solid #fecaca;
        font-size: 14px;
      }}
      
      /* Results Styles */
      .af-results {{
        animation: slideUp 0.3s ease-out;
      }}
      @keyframes slideUp {{
        from {{ opacity: 0; transform: translateY(20px); }}
        to {{ opacity: 1; transform: translateY(0); }}
      }}
      .af-results-header {{
        text-align: center;
        margin-bottom: 32px;
      }}
      .af-results-url {{
        font-size: 14px;
        color: #6b7280;
        margin-top: 8px;
      }}
      .af-score-circle {{
        width: 140px;
        height: 140px;
        margin: 0 auto 24px;
        position: relative;
      }}
      .af-score-circle svg {{
        transform: rotate(-90deg);
      }}
      .af-score-number {{
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 48px;
        font-weight: 700;
        color: #1f2937;
      }}
      .af-score-label {{
        font-size: 13px;
        color: #6b7280;
        margin-top: 8px;
      }}
      .af-categories-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 12px;
        margin-bottom: 32px;
      }}
      .af-category-card {{
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        transition: all 0.2s;
      }}
      .af-category-card:hover {{
        border-color: ${{CONFIG.accentColor}};
        box-shadow: 0 4px 12px rgba(31, 41, 55, 0.1);
      }}
      .af-category-name {{
        font-size: 12px;
        color: #6b7280;
        margin-bottom: 8px;
        font-weight: 500;
      }}
      .af-category-score {{
        font-size: 24px;
        font-weight: 700;
        color: #1f2937;
      }}
      .af-category-score.good {{ color: #059669; }}
      .af-category-score.warning {{ color: #f59e0b; }}
      .af-category-score.poor {{ color: #dc2626; }}
      
      .af-checks-section {{
        text-align: left;
        margin-bottom: 32px;
      }}
      .af-checks-title {{
        font-size: 16px;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 16px;
      }}
      .af-checks-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
      }}
      .af-check {{
        padding: 12px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 8px;
      }}
      .af-check.pass {{
        background: #d1fae5;
        color: #065f46;
      }}
      .af-check.fail {{
        background: #fee2e2;
        color: #7f1d1d;
      }}
      .af-check-icon {{
        font-size: 16px;
      }}
      
      .af-cta-section {{
        border-top: 1px solid #e5e7eb;
        padding-top: 24px;
        margin-top: 32px;
      }}
      .af-cta-text {{
        font-size: 14px;
        color: #6b7280;
        margin-bottom: 16px;
      }}
      .af-button-group {{
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        justify-content: center;
      }}
      .af-button-secondary {{
        padding: 10px 20px;
        background: white;
        border: 1px solid #d1d5db;
        color: #374151;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
      }}
      .af-button-secondary:hover {{
        background: #f9fafb;
      }}
    `;
    document.head.appendChild(style);
    
    // Render widget HTML
    container.innerHTML = `
      <div class="af-widget">
        <div class="af-card">
          <div id="af-form-container">
            ${{CONFIG.logo ? `<img src="${{CONFIG.logo}}" alt="${{CONFIG.agencyName}}" class="af-logo">` : ''}}
            <h1 class="af-headline">${{CONFIG.headlineText}}</h1>
            <p class="af-description">${{CONFIG.descriptionText}}</p>
            
            <form id="af-form" class="af-form">
              ${{CONFIG.leadCaptureEnabled && CONFIG.requireEmail ? `
                <input 
                  type="email" 
                  id="af-email" 
                  class="af-input" 
                  placeholder="Your Email Address"
                  required
                />
              ` : ''}}
              <input 
                type="url" 
                id="af-url" 
                class="af-input" 
                placeholder="Enter Your Website URL"
                required
              />
              <button type="submit" class="af-button" id="af-submit">
                ${{CONFIG.buttonText}}
              </button>
              ${{CONFIG.showPoweredBy ? `<p class="af-poweredBy">
                              Powered by <a href="https://outaudits.com" target="_blank" rel="noopener noreferrer">OUTAUDITS</a>
                            </p>` : ''}}
            </form>
            
            <div id="af-loading" class="af-loading" style="display: none;">
              <div class="af-spinner"></div>
              <div class="af-progress" id="af-progress">Analyzing your website...</div>
            </div>
            
            <div id="af-error" class="af-error" style="display: none;"></div>
          </div>
          
          <div id="af-results-container" style="display: none;"></div>
        </div>
      </div>
    `;
    
    // Form submission handler
    const form = document.getElementById('af-form');
    const loading = document.getElementById('af-loading');
    const error = document.getElementById('af-error');
    const formContainer = document.getElementById('af-form-container');
    const resultsContainer = document.getElementById('af-results-container');
    
    form.addEventListener('submit', async (e) => {{
      e.preventDefault();
      
      const url = document.getElementById('af-url').value;
      const emailInput = document.getElementById('af-email');
      const email = emailInput ? emailInput.value : null;
      
      // Show loading
      form.style.display = 'none';
      loading.style.display = 'block';
      error.style.display = 'none';
      
      try {{
        // Start audit
        const response = await fetch(API_BASE + '/api/embed/audit', {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{
            api_key: CONFIG.apiKey,
            url: url,
            email: email
          }})
        }});
        
        const data = await response.json();
        
        if (!response.ok) {{
          throw new Error(data.detail || 'Audit failed');
        }}
        
        // Poll for results
        const jobId = data.job_id;
        pollResults(jobId);
        
      }} catch (err) {{
        error.textContent = err.message;
        error.style.display = 'block';
        form.style.display = 'flex';
        loading.style.display = 'none';
      }}
    }});
    
    // Poll for audit results
    const pollResults = async (jobId) => {{
      const progressEl = document.getElementById('af-progress');
      
      const poll = async () => {{
        try {{
          const response = await fetch(API_BASE + `/api/embed/status/${{jobId}}?api_key=${{CONFIG.apiKey}}`);
          const data = await response.json();
          
          if (data.status === 'completed') {{
            // Fetch and display results in-widget
            const resultsResponse = await fetch(API_BASE + `/api/embed/results-data/${{jobId}}?api_key=${{CONFIG.apiKey}}`);
            const resultsData = await resultsResponse.json();
            displayResults(resultsData, jobId);
          }} else if (data.status === 'failed') {{
            throw new Error('Audit failed. Please try again.');
          }} else {{
            progressEl.textContent = data.current_status || 'Analyzing your website...';
            setTimeout(poll, 2000);
          }}
        }} catch (err) {{
          error.textContent = err.message;
          error.style.display = 'block';
          form.style.display = 'flex';
          loading.style.display = 'none';
        }}
      }};
      
      poll();
    }};
    
    // Display results in-widget
    const displayResults = (resultsData, jobId) => {{
      loading.style.display = 'none';
      formContainer.style.display = 'none';
      resultsContainer.style.display = 'block';
      
      const results = resultsData.results;
      const score = results.overall_score || 0;
      
      // Color based on score
      const getScoreColor = (s) => s >= 80 ? 'good' : s >= 50 ? 'warning' : 'poor';
      const getScoreClass = (s) => s >= 80 ? '#059669' : s >= 50 ? '#f59e0b' : '#dc2626';
      
      // Build categories HTML
      let categoriesHtml = '';
      const categories = [
        {{ key: 'performance', title: 'Performance' }},
        {{ key: 'accessibility', title: 'Accessibility' }},
        {{ key: 'best_practices', title: 'Best Practices' }},
        {{ key: 'seo', title: 'SEO' }},
        {{ key: 'pwa', title: 'PWA' }}
      ];
      
      categories.forEach(cat => {{
        const score = results.lighthouse?.categories?.[cat.key]?.score || 0;
        const scoreClass = getScoreColor(score);
        categoriesHtml += `
          <div class="af-category-card">
            <div class="af-category-name">${{cat.title}}</div>
            <div class="af-category-score ${{scoreClass}}">${{Math.round(score)}}</div>
          </div>
        `;
      }});
      
      // Build checks grid
      let checksHtml = '';
      const checks = [
        {{ key: 'https', title: 'HTTPS' }},
        {{ key: 'title_tag', title: 'Title Tag' }},
        {{ key: 'meta_description', title: 'Meta Description' }},
        {{ key: 'robots_txt', title: 'Robots.txt' }},
        {{ key: 'sitemap_xml', title: 'Sitemap.xml' }},
        {{ key: 'canonical', title: 'Canonical Tag' }}
      ];
      
      checks.forEach(check => {{
        const passed = results.security?.https || results.technical_seo?.[check.key];
        const status = passed ? 'pass' : 'fail';
        const icon = passed ? '✓' : '✕';
        checksHtml += `
          <div class="af-check ${{status}}">
            <span class="af-check-icon">${{icon}}</span>
            <span>${{check.title}}</span>
          </div>
        `;
      }});
      
      resultsContainer.innerHTML = `
        <div class="af-results">
          <div class="af-results-header">
            <h2 class="af-headline">Your SEO Audit Results</h2>
            <p class="af-results-url">${{resultsData.url}}</p>
          </div>
          
          <div style="text-align: center; margin-bottom: 32px;">
            <div class="af-score-circle">
              <svg viewBox="0 0 200 200" width="140" height="140">
                <circle cx="100" cy="100" r="90" fill="none" stroke="#e5e7eb" stroke-width="8"/>
                <circle cx="100" cy="100" r="90" fill="none" stroke="${{getScoreClass(score)}}" stroke-width="8"
                  stroke-dasharray="${{565.48 * score / 100}} 565.48" stroke-linecap="round"/>
              </svg>
              <div class="af-score-number">${{Math.round(score)}}</div>
            </div>
            <p class="af-score-label">Overall SEO Score</p>
          </div>
          
          <div class="af-categories-grid">
            ${{categoriesHtml}}
          </div>
          
          <div class="af-checks-section">
            <h3 class="af-checks-title">All Checks at a Glance</h3>
            <div class="af-checks-grid">
              ${{checksHtml}}
            </div>
          </div>
          
          <div class="af-cta-section">
            <p class="af-cta-text">Ready to improve your SEO?</p>
            <div class="af-button-group">
              <button onclick="window.open('${{resultsData.agency_url || '#'}}', '_blank')" class="af-button">
                Get Started
              </button>
              <button onclick="fetch(API_BASE + '/api/embed/download/${{jobId}}?api_key=${{CONFIG.apiKey}}').then(r => r.blob()).then(b => {{ const url = window.URL.createObjectURL(b); const a = document.createElement('a'); a.href = url; a.download = 'audit-report.pdf'; a.click(); }});" class="af-button-secondary">
                Download PDF
              </button>
            </div>
          </div>
        </div>
      `;
    }};
  }};
  
  // Initialize widget when DOM is ready
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', createWidget);
  }} else {{
    createWidget();
  }}
}})();
"""
    
    return HTMLResponse(content=widget_js, media_type="application/javascript")


@router.post("/audit")
async def start_embedded_audit(
    request: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start audit from embedded widget"""
    
    api_key = request.get('api_key')
    url = request.get('url')
    email = request.get('email')
    
    # Verify API key
    user = db.query(User).filter(User.embed_api_key == api_key).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check plan/trial access
    if not can_use_feature(user):
      raise HTTPException(status_code=403, detail="Embed audits require Pro or Agency plan or an active trial")
    
    # Check if email required
    if user.embed_require_email and not email:
        raise HTTPException(status_code=400, detail="Email required")
    
    # Create audit job
    job_id = str(uuid.uuid4())
    
    audit = Audit(
        job_id=job_id,
        user_id=user.id,
        url=url,
        status="pending",
        progress=0,
        is_embedded=True,
        embed_email=email
    )
    
    db.add(audit)
    db.commit()

    # Create lead if email provided
    if email:
        lead = EmbedLead(
            user_id=user.id,
            email=email,
            website=url,
            audit_id=audit.id,
            source="embed_widget"
        )
        db.add(lead)
    
    db.commit()
    
    # Start audit in background (simplified - use background tasks in production)
    # background_tasks.add_task(run_audit_task, job_id, url, user.id, db)
    queue.enqueue(run_audit_task, job_id, url, user.id, retry=Retry(max=3, interval=60))
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Audit started"
    }


@router.get("/status/{job_id}")
async def get_embedded_audit_status(
    job_id: str,
    api_key: str,
    db: Session = Depends(get_db)
):
    """Get audit status for embedded widget"""
    
    # Verify API key
    user = db.query(User).filter(User.embed_api_key == api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Get audit
    audit = db.query(Audit).filter(
        Audit.job_id == job_id,
        Audit.user_id == user.id,
        Audit.is_embedded == True
    ).first()
    
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    
    return {
        "job_id": job_id,
        "status": audit.status,
        "progress": audit.progress,
        "current_status": "Analyzing..." if audit.status == "running" else audit.status
    }


@router.get("/results-data/{job_id}")
async def get_embedded_results_data(
    job_id: str,
    api_key: str,
    db: Session = Depends(get_db)
):
    """Get results data as JSON for embedded widget display"""
    
    # Verify API key and get agency settings
    user = db.query(User).filter(User.embed_api_key == api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Get audit
    audit = db.query(Audit).filter(
        Audit.job_id == job_id,
        Audit.user_id == user.id,
        Audit.is_embedded == True
    ).first()
    
    if not audit or not audit.results:
        raise HTTPException(status_code=404, detail="Results not found")
    
    return {
        "job_id": job_id,
        "url": audit.url,
        "client_name": audit.client_name or "Client",
        "agency_name": user.agency_name,
        "agency_url": user.agency_url,
        "results": audit.results
    }


@router.get("/results/{job_id}/{api_key}", response_class=HTMLResponse)
async def get_embedded_results(
    job_id: str,
    api_key: str,
    db: Session = Depends(get_db)
):
    """Show results page for embedded audit - kept for testing purposes"""
    
    # Verify API key and get agency settings
    user = db.query(User).filter(User.embed_api_key == api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Get audit
    audit = db.query(Audit).filter(
        Audit.job_id == job_id,
        Audit.user_id == user.id,
        Audit.is_embedded == True
    ).first()
    
    if not audit or not audit.results:
        raise HTTPException(status_code=404, detail="Results not found")
    
    results = audit.results
    print(results.get('lighthouse').get('categories'))
    score = results.get('overall_score', 0)
    
    # Generate HTML results page with modern design
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SEO Audit Results - {user.agency_name}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            html, body {{ height: 100%; }}
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f9fafb;
                padding: 32px 20px;
            }}
            .container {{
                max-width: 900px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 10px 40px rgba(0,0,0,0.08);
                padding: 48px 40px;
            }}
            .header {{
                text-align: center;
                margin-bottom: 48px;
            }}
            .logo {{
                width: 80px;
                height: auto;
                margin-bottom: 24px;
            }}
            .header h1 {{
                font-size: 32px;
                font-weight: 700;
                color: #1f2937;
                margin-bottom: 8px;
            }}
            .header p {{
                font-size: 15px;
                color: #6b7280;
            }}
            .score-section {{
                text-align: center;
                margin-bottom: 48px;
            }}
            .score-circle {{
                width: 160px;
                height: 160px;
                margin: 0 auto 24px;
                position: relative;
            }}
            .score-circle svg {{
                transform: rotate(-90deg);
            }}
            .score-number {{
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 56px;
                font-weight: 700;
                color: #1f2937;
            }}
            .score-label {{
                font-size: 14px;
                color: #6b7280;
            }}
            .categories-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                gap: 16px;
                margin-bottom: 48px;
            }}
            .category-card {{
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                transition: all 0.2s;
            }}
            .category-card:hover {{
                border-color: {user.accent_color};
                box-shadow: 0 4px 12px rgba(31, 41, 55, 0.1);
            }}
            .category-name {{
                font-size: 13px;
                color: #6b7280;
                margin-bottom: 12px;
                font-weight: 500;
            }}
            .category-score {{
                font-size: 28px;
                font-weight: 700;
                color: #1f2937;
            }}
            .category-score.good {{ color: #059669; }}
            .category-score.warning {{ color: #f59e0b; }}
            .category-score.poor {{ color: #dc2626; }}
            .checks-section {{
                margin-bottom: 48px;
            }}
            .section-title {{
                font-size: 18px;
                font-weight: 700;
                color: #1f2937;
                margin-bottom: 20px;
            }}
            .checks-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                gap: 12px;
            }}
            .check {{
                padding: 14px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .check.pass {{
                background: #d1fae5;
                color: #065f46;
                border: 1px solid #a7f3d0;
            }}
            .check.fail {{
                background: #fee2e2;
                color: #7f1d1d;
                border: 1px solid #fecaca;
            }}
            .check-icon {{
                font-size: 18px;
                font-weight: 700;
            }}
            .details-section {{
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                padding: 24px;
                margin-bottom: 48px;
            }}
            .detail-item {{
                display: flex;
                justify-content: space-between;
                padding: 12px 0;
                border-bottom: 1px solid #e5e7eb;
            }}
            .detail-item:last-child {{
                border-bottom: none;
            }}
            .detail-label {{
                color: #6b7280;
                font-weight: 500;
            }}
            .detail-value {{
                color: #1f2937;
                font-weight: 600;
            }}
            .cta-section {{
                border-top: 1px solid #e5e7eb;
                padding-top: 32px;
                text-align: center;
            }}
            .cta-title {{
                font-size: 20px;
                font-weight: 700;
                color: #1f2937;
                margin-bottom: 12px;
            }}
            .cta-text {{
                font-size: 15px;
                color: #6b7280;
                margin-bottom: 24px;
            }}
            .button-group {{
                display: flex;
                gap: 12px;
                justify-content: center;
                flex-wrap: wrap;
            }}
            .button {{
                padding: 12px 32px;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 600;
                text-decoration: none;
                border: none;
                cursor: pointer;
                transition: all 0.2s;
            }}
            .button-primary {{
                background: {user.accent_color};
                color: white;
            }}
            .button-primary:hover {{
                opacity: 0.9;
            }}
            .button-secondary {{
                background: white;
                border: 1px solid #d1d5db;
                color: #374151;
            }}
            .button-secondary:hover {{
                background: #f9fafb;
            }}
            .insights-section {{
                margin-bottom: 48px;
            }}
            .insight {{
                background: #fef3c7;
                border: 1px solid #fde68a;
                border-left: 4px solid #f59e0b;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 12px;
            }}
            .insight.error {{
                background: #fee2e2;
                border-color: #fecaca;
                border-left-color: #dc2626;
            }}
            .insight.success {{
                background: #d1fae5;
                border-color: #a7f3d0;
                border-left-color: #059669;
            }}
            .insight-title {{
                font-weight: 600;
                margin-bottom: 4px;
            }}
            .insight-text {{
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                {f'<img src="{user.agency_logo}" class="logo" alt="{user.agency_name}">' if user.agency_logo else ''}
                <h1>Your SEO Audit Results</h1>
                <p>{audit.url}</p>
            </div>
            
            <div class="score-section">
                <div class="score-circle">
                    <svg viewBox="0 0 200 200" width="160" height="160">
                        <circle cx="100" cy="100" r="90" fill="none" stroke="#e5e7eb" stroke-width="8"/>
                        <circle cx="100" cy="100" r="90" fill="none" stroke="{get_score_color_hex(score, user.accent_color)}" stroke-width="8"
                            stroke-dasharray="{565.48 * score / 100} 565.48" stroke-linecap="round"/>
                    </svg>
                    <div class="score-number">{score}</div>
                </div>
                <p class="score-label">Overall SEO Score</p>
            </div>
            
            <div class="categories-grid">
                {generate_categories_html(results, user.accent_color)}
            </div>
            
            {generate_checks_html(results)}
            
            {generate_insights_html(results)}
            
            
            
            <div class="cta-section">
                <h2 class="cta-title">Ready to Improve Your Score?</h2>
                <p class="cta-text">Our experts can help you optimize your website for better performance and rankings.</p>
                <div class="button-group">
                    <a href="{user.agency_url or '#'}" class="button button-primary">Get Started</a>
                    <a href="/api/embed/download/{job_id}?api_key={api_key}" class="button button-secondary">Download PDF</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    # {generate_details_html(results)}
    
    return HTMLResponse(content=html)


def get_score_color_hex(score: int, accent_color: str) -> str:
    """Get color based on score"""
    if score >= 80:
        return '#059669'  # Green
    elif score >= 50:
        return '#f59e0b'  # Amber
    else:
        return '#dc2626'  # Red


def get_score_class(score: int) -> str:
    """Get CSS class based on score"""
    if score >= 80:
        return 'good'
    elif score >= 50:
        return 'warning'
    else:
        return 'poor'


def generate_categories_html(results: dict, accent_color: str) -> str:
    """Generate HTML for category cards"""
    html = ""
    
    categories = [
        {'key': 'performance', 'title': 'Performance'},
        {'key': 'accessibility', 'title': 'Accessibility'},
        {'key': 'best-practices', 'title': 'Best Practices'},
        {'key': 'seo', 'title': 'SEO'},
        {'key': 'pwa', 'title': 'PWA'}
    ]
    
    for cat in categories:
        # Try to get score from lighthouse categories
        score = 0
        if 'lighthouse' in results and 'categories' in results.get('lighthouse', {}):
            score = results['lighthouse']['categories'].get(cat['key'], {}).get('score', 0)
        
        score = int(score)
        score_class = get_score_class(score)
        
        html += f"""
        <div class="category-card">
            <div class="category-name">{cat['title']}</div>
            <div class="category-score {score_class}">{score}</div>
        </div>
        """
    
    return html


def generate_checks_html(results: dict) -> str:
    """Generate HTML for checks at a glance"""
    checks = [
        {'key': 'https', 'title': 'HTTPS', 'section': 'security'},
        {'key': 'title', 'title': 'Title Tag', 'section': 'technical_seo'},
        {'key': 'meta_description', 'title': 'Meta Description', 'section': 'technical_seo'},
        {'key': 'robots_txt', 'title': 'Robots.txt', 'section': 'technical_seo'},
        {'key': 'sitemap_xml', 'title': 'Sitemap.xml', 'section': 'technical_seo'},
        {'key': 'canonical', 'title': 'Canonical Tag', 'section': 'technical_seo'}
    ]
    
    checks_html = ""
    for check in checks:
        # Determine if check passed
        passed = False
        if check['section'] == 'security':
            passed = results.get('security', {}).get('https', False)
        else:
            tech_seo = results.get('technical_seo', {})
            if check['key'] == 'title':
                passed = bool(tech_seo.get('title'))
            elif check['key'] == 'meta_description':
                passed = bool(tech_seo.get('meta_description'))
            else:
                passed = tech_seo.get(check['key'], False)
        
        status = 'pass' if passed else 'fail'
        icon = '✓' if passed else '✕'
        
        checks_html += f"""
        <div class="check {status}">
            <span class="check-icon">{icon}</span>
            <span>{check['title']}</span>
        </div>
        """
    
    return f"""
    <div class="checks-section">
        <h3 class="section-title">All Checks at a Glance</h3>
        <div class="checks-grid">
            {checks_html}
        </div>
    </div>
    """


def generate_insights_html(results: dict) -> str:
    """Generate HTML for key insights"""
    insights_html = ""
    
    # Broken links insight
    broken_links = results.get('broken_links', {})
    if broken_links.get('broken_count', 0) > 0:
        insights_html += f"""
        <div class="insight error">
            <div class="insight-title">⚠️ Broken Links Found</div>
            <div class="insight-text">{broken_links.get('broken_count', 0)} broken links detected. These can hurt your SEO and user experience.</div>
        </div>
        """
    
    # Image optimization insight
    image_opt = results.get('image_optimization', {})
    if image_opt.get('score', 100) < 80:
        insights_html += f"""
        <div class="insight">
            <div class="insight-title">🖼️ Image Optimization</div>
            <div class="insight-text">Optimize {image_opt.get('total_images', 0)} images on your site to improve performance.</div>
        </div>
        """
    
    # Structured data insight
    struct_data = results.get('structured_data', {})
    if not struct_data.get('has_json_ld'):
        insights_html += f"""
        <div class="insight">
            <div class="insight-title">📊 No Structured Data</div>
            <div class="insight-text">Add JSON-LD schema markup to help search engines understand your content better.</div>
        </div>
        """
    else:
        insights_html += f"""
        <div class="insight success">
            <div class="insight-title">✓ Structured Data Present</div>
            <div class="insight-text">Great! Your site has {', '.join(struct_data.get('json_ld_types', []))} schema markup.</div>
        </div>
        """
    
    if not insights_html:
        insights_html = '<div class="insight success"><div class="insight-title">✓ Great Job!</div><div class="insight-text">Your website is well-optimized. Keep up the good work!</div></div>'
    
    return f"""
    <div class="insights-section">
        {insights_html}
    </div>
    """


def generate_details_html(results: dict) -> str:
    """Generate HTML for technical details"""
    content = results.get('content_quality', {})
    
    return f"""
    <div class="details-section">
        <h3 class="section-title">Content Quality Details</h3>
        <div class="detail-item">
            <span class="detail-label">Word Count</span>
            <span class="detail-value">{content.get('word_count', 'N/A'):,}</span>
        </div>
        <div class="detail-item">
            <span class="detail-label">Paragraphs</span>
            <span class="detail-value">{content.get('paragraph_count', 'N/A')}</span>
        </div>
        <div class="detail-item">
            <span class="detail-label">Avg Sentence Length</span>
            <span class="detail-value">{content.get('avg_sentence_length', 'N/A')}</span>
        </div>
        <div class="detail-item">
            <span class="detail-label">Reading Level</span>
            <span class="detail-value">{content.get('reading_level', 'N/A')}</span>
        </div>
        <div class="detail-item">
            <span class="detail-label">Content to Code Ratio</span>
            <span class="detail-value">{content.get('content_to_code_ratio', 'N/A')}</span>
        </div>
    </div>
    """


@router.get("/download/{job_id}/{api_key}")
async def download_pdf_report(
    job_id: str,
    api_key: str,
    db: Session = Depends(get_db)
):
    """Download PDF report from embedded widget"""
    
    # Verify API key
    user = db.query(User).filter(User.embed_api_key == api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Get audit
    audit = db.query(Audit).filter(
        Audit.job_id == job_id,
        Audit.user_id == user.id
    ).first()
    
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    
    lead = db.query(EmbedLead).filter(EmbedLead.audit_id == audit.id).first()
    lead_info = {
            "first_name": "John",  # Placeholder - you would capture this from the lead form
            "last_name": "Doe",     # Placeholder - you would capture this from the lead form
            "email": "email@example.com",  # Placeholder - you would capture this from the lead form
            "company": "Example Inc."  # Placeholder - you would capture this from the lead form
        }
    if lead:
        lead_info['email'] = lead.email

    # Generate PDF (simplified - use proper PDF generation in production)
    # Return PDF file
    # This would integrate with your existing PDF generation
    branding = {
      "agency_name" : user.agency_name,
      "logo_url": user.agency_logo,
      "accent_color": user.accent_color,
      "agency_url" : user.agency_url,

    }
    generator = PDFReportGenerator()
    audit_url = str(audit.url).replace('https://', '').replace('http://', '').rstrip('/')
    safe_filename = f"SEO_Audit_Report_{audit_url.replace('.', '_').replace('/', '_')}.pdf"
    #report_path = generator.generate_audit_report(job_id, audit.results, lead_info, branding, safe_filename)
    
    # report_path = await run_in_threadpool(
    #     generator.generate_audit_report,
    #     job_id,
    #     audit.results,
    #     lead_info,
    #     branding,
    #     safe_filename
    # )

    # report_path = await generator.generate_audit_report(
    #     job_id,
    #     audit.results,
    #     lead_info,
    #     branding,
    #     safe_filename
    # )

    #use queue instead
    report_path = await queue.enqueue_call(
        func=generator.generate_audit_report,
        args=(job_id, audit.results, lead_info, branding, safe_filename),
        timeout=300  # Set a timeout for the job
    )
    

    return FileResponse(
        path=report_path,
        filename=safe_filename,
        media_type="application/pdf"
    )


# ──────────────────────────────────────────────────────────────────────────────
# API Key Management
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/generate-key")
async def generate_embed_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate new embed API key for agency"""
    
    # if can_use_feature(current_user) is False:
    #     raise HTTPException(status_code=403, detail="Feature not available for your plan")

    # Generate unique API key
    api_key = f"af_embed_{uuid.uuid4().hex}"
    
    current_user.embed_api_key = api_key
    current_user.embed_enabled = True
    db.commit()
    
    return {
        "api_key": api_key,
        "message": "API key generated successfully"
    }


@router.get("/settings")
async def get_embed_settings(
    current_user: User = Depends(get_current_user)
):
    """Get current embed settings"""
    print("getting settings")
    
    return {
        "api_key": current_user.embed_api_key,
        "enabled": current_user.embed_enabled,
        "lead_capture": current_user.embed_lead_capture,
        "require_email": current_user.embed_require_email,
        "button_text": current_user.embed_button_text,
        "headline": current_user.embed_headline,
        "description": current_user.embed_description,
        "primary_color" : current_user.embed_primary_color,
        "bg_color" : current_user.embed_bg_color,
        "text_color" : current_user.embed_text_color,
        "border_radius" : current_user.embed_border_radius,
        "show_logo" : current_user.embed_show_logo,
        "show_poweredBy" : current_user.embed_show_poweredBy,
        "email_placeholder" : current_user.embed_email_placeholder,
        "width" : current_user.embed_width,
        "shadow" : current_user.embed_shadow,
    }


@router.patch("/settings")
async def update_embed_settings(
    settings: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update embed widget settings"""
    # {
    #   title: 'Free SEO Audit',
    #   subtitle: 'Enter your website URL for an instant analysis',
    #   buttonText: 'Analyze',
    #   primaryColor: '#00a4c6',
    #   bgColor: '#ffffff',
    #   textColor: '#141e27',
    #   borderRadius: 8,
    #   showLogo: true,
    #   showPoweredBy: false,
    #   requireEmail: true,
    #   emailPlaceholder: 'Enter your email',
    #   width: '100%',
    #   shadow: true,
    # }

    
    
    if 'lead_capture' in settings:
        current_user.embed_lead_capture = settings['lead_capture']
    if 'require_email' in settings:
        current_user.embed_require_email = settings['require_email']
    if 'button_text' in settings:
        current_user.embed_button_text = settings['button_text']
    if 'headline' in settings:
        current_user.embed_headline = settings['headline']
    if 'description' in settings:
        current_user.embed_description = settings['description']
    if 'primary_color' in settings:
        current_user.embed_primary_color = settings['primary_color']
    if 'bg_color' in settings:
        current_user.embed_bg_color = settings['bg_color'] 
    if 'text_color' in settings:
        current_user.embed_text_color = settings['text_color'] 
    if 'border_radius' in settings:
        current_user.embed_border_radius = settings['border_radius']   
    if 'show_logo' in settings:
        current_user.embed_show_logo = settings['show_logo']   
    if 'show_powered_by' in settings:
        current_user.embed_show_poweredBy = settings['show_powered_by'] 
    if 'email_placeholder' in settings:
        current_user.embed_email_placeholder = settings['email_placeholder']     
    if 'width' in settings:
        current_user.embed_width = settings['width'] 
    if 'shadow' in settings:
        current_user.embed_shadow = settings['shadow']                             
    
    db.commit()
    
    
    return {"message": "Settings updated successfully"}


@router.get("/leads")
async def get_embed_leads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get leads captured from embedded widget"""
    
    leads = db.query(EmbedLead).filter(EmbedLead.user_id == current_user.id).all()

    def get_audit_id_and_score(audit_id):
        audit = db.query(Audit).filter(Audit.id == audit_id).first()
        
        data = {
            "job_id" : None,
            "score" : 0
        }
        if audit:
            data['job_id'] = audit.job_id
            data['score'] = audit.overall_score
        return data

    # Calculate previous calendar month range (start of previous month -> start of current month)
    start_current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day_prev_month = start_current_month - timedelta(days=1)
    start_prev_month = last_day_prev_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    current_month_leads = db.query(EmbedLead).filter(
        EmbedLead.user_id == current_user.id,
        EmbedLead.created_at >= start_current_month
    ).all()
    #get the percentage increase/decrease compared to the previous month

    previous_leads = db.query(EmbedLead).filter(
        EmbedLead.user_id == current_user.id,
        EmbedLead.created_at >= start_prev_month,
        EmbedLead.created_at < start_current_month
    ).all()

    current_total = len(current_month_leads)
    previous_total = len(previous_leads)
    print(current_total, previous_total)
    diff = current_total - previous_total

    # Percent change relative to previous period; avoid division by zero
    if previous_total == 0:
        if current_total == 0:
            diff_percent = 0.0
        else:
            # If there were 0 in previous period and >0 now, treat as 100% increase
            diff_percent = 100.0
    else:
        diff_percent = (diff / previous_total) * 100.0

    diff_percent = round(diff_percent, 1)

    print(diff_percent)
    
    
    return {
        "change": diff_percent,
        "leads": [
            {
                "id" : lead.id,
                "email": lead.email,
                "website": lead.website,
                "status": lead.status,
                "notes" : lead.notes,
                "source": lead.source,
                "audit_id" : lead.audit_id,
                "job_id" : get_audit_id_and_score(lead.audit_id)['job_id'],
                "score" : get_audit_id_and_score(lead.audit_id)['score'],
                "created_at": lead.created_at.isoformat(),

            }
            for lead in leads
        ],


    }



#update lead 
@router.patch("/leads/{lead_id}")
async def update_lead(
    lead_id: int,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    current_user : User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
      """Update lead note, status, etc."""
      print(lead_id)
      
      lead = db.query(EmbedLead).filter(
          EmbedLead.id == lead_id,
          EmbedLead.user_id == current_user.id
      ).first()

      if not lead:
          raise HTTPException(status_code=404, detail="Lead not found")

      if status:
          lead.status = status
      if notes:
          lead.notes = notes

      print(notes, status)    

      db.commit()

      return {"message": "Lead updated successfully"}

#delete lead
@router.delete("/leads/{lead_id}")
async def delete_lead(
    lead_id: int,
    current_user : User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a lead"""
    lead = db.query(EmbedLead).filter(
          EmbedLead.id == lead_id,
          EmbedLead.user_id == current_user.id
      ).first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    db.delete(lead)
    db.commit()

    return {"message": "Lead deleted successfully"}

    