"""
Embeddable Widget - Allow agencies to embed audit tool on their websites
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import uuid

from db.database import get_db
from db.models import User, Audit, EmbedLead
from db.auth import get_current_user
from services.email_service import send_email
from auditor import WebsiteAuditor

router = APIRouter(prefix="/api/embed", tags=["embed"])


# ──────────────────────────────────────────────────────────────────────────────
# Widget Configuration
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/widget.js")
async def get_widget_script(
    api_key: str,
    db: Session = Depends(get_db)
):
    """
    Get embeddable widget JavaScript
    
    Usage:
    <script src="https://api.auditflow.com/api/embed/widget.js?api_key=YOUR_KEY"></script>
    <div id="auditflow-widget"></div>
    """
    
    # Verify API key and get agency settings
    user = db.query(User).filter(User.embed_api_key == api_key).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Generate widget configuration
    config = {
        "apiKey": api_key,
        "agencyName": user.agency_name or "AuditFlow",
        "accentColor": user.accent_color or "#0075FF",
        "logo": user.agency_logo or None,
        "leadCaptureEnabled": user.embed_lead_capture,
        "requireEmail": user.embed_require_email,
        "buttonText": user.embed_button_text or "Analyze Website",
        "headlineText": user.embed_headline or "Free Website SEO Audit",
        "descriptionText": user.embed_description or "Get a comprehensive SEO analysis in seconds",
    }
    
    # Widget JavaScript template
    widget_js = f"""
(function() {{
  const CONFIG = {config};
  
  // Create widget container
  const createWidget = () => {{
    const container = document.getElementById('auditflow-widget');
    if (!container) {{
      console.error('AuditFlow: Container #auditflow-widget not found');
      return;
    }}
    
    // Inject styles
    const style = document.createElement('style');
    style.textContent = `
      .af-widget {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        max-width: 600px;
        margin: 0 auto;
        padding: 40px 20px;
      }}
      .af-card {{
        background: white;
        border-radius: 16px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        padding: 40px;
        text-align: center;
      }}
      .af-logo {{
        width: 120px;
        height: auto;
        margin-bottom: 20px;
      }}
      .af-headline {{
        font-size: 32px;
        font-weight: 800;
        color: #1a1a1a;
        margin-bottom: 12px;
      }}
      .af-description {{
        font-size: 16px;
        color: #666;
        margin-bottom: 30px;
      }}
      .af-form {{
        display: flex;
        flex-direction: column;
        gap: 16px;
      }}
      .af-input {{
        padding: 16px;
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        font-size: 16px;
        transition: border-color 0.2s;
      }}
      .af-input:focus {{
        outline: none;
        border-color: ${{CONFIG.accentColor}};
      }}
      .af-button {{
        padding: 16px 32px;
        background: linear-gradient(135deg, ${{CONFIG.accentColor}} 0%, #8766FF 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 18px;
        font-weight: 700;
        cursor: pointer;
        transition: transform 0.2s;
      }}
      .af-button:hover {{
        transform: translateY(-2px);
      }}
      .af-button:disabled {{
        opacity: 0.6;
        cursor: not-allowed;
      }}
      .af-loading {{
        margin-top: 20px;
        text-align: center;
      }}
      .af-spinner {{
        border: 4px solid #f3f3f3;
        border-top: 4px solid ${{CONFIG.accentColor}};
        border-radius: 50%;
        width: 40px;
        height: 40px;
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
        color: #666;
      }}
      .af-error {{
        background: #fee;
        color: #c33;
        padding: 12px;
        border-radius: 8px;
        margin-top: 16px;
      }}
    `;
    document.head.appendChild(style);
    
    // Render widget HTML
    container.innerHTML = `
      <div class="af-widget">
        <div class="af-card">
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
          </form>
          
          <div id="af-loading" class="af-loading" style="display: none;">
            <div class="af-spinner"></div>
            <div class="af-progress" id="af-progress">Analyzing your website...</div>
          </div>
          
          <div id="af-error" class="af-error" style="display: none;"></div>
        </div>
      </div>
    `;
    
    // Form submission handler
    const form = document.getElementById('af-form');
    const loading = document.getElementById('af-loading');
    const error = document.getElementById('af-error');
    const submitBtn = document.getElementById('af-submit');
    
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
        const response = await fetch('https://api.auditflow.com/api/embed/audit', {{
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
          const response = await fetch(`https://api.auditflow.com/api/embed/status/${{jobId}}?api_key=${{CONFIG.apiKey}}`);
          const data = await response.json();
          
          if (data.status === 'completed') {{
            // Redirect to results page
            window.location.href = `https://api.auditflow.com/api/embed/results/${{jobId}}?api_key=${{CONFIG.apiKey}}`;
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
    # background_tasks.add_task(run_audit_task, job_id, user.id, db)
    
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


@router.get("/results/{job_id}", response_class=HTMLResponse)
async def get_embedded_results(
    job_id: str,
    api_key: str,
    db: Session = Depends(get_db)
):
    """Show results page for embedded audit"""
    
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
    score = results.get('overall_score', 0)
    
    # Generate HTML results page
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SEO Audit Results - {user.agency_name}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 40px 20px;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                padding: 40px;
            }}
            .header {{
                text-align: center;
                margin-bottom: 40px;
            }}
            .logo {{
                width: 150px;
                height: auto;
                margin-bottom: 20px;
            }}
            .score-circle {{
                width: 200px;
                height: 200px;
                margin: 0 auto 20px;
                position: relative;
            }}
            .score-number {{
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 64px;
                font-weight: 900;
                color: {user.accent_color};
            }}
            .score-label {{
                font-size: 14px;
                color: #666;
                margin-top: -10px;
            }}
            .categories {{
                margin-top: 40px;
            }}
            .category {{
                padding: 20px;
                background: #f8f9fa;
                border-radius: 12px;
                margin-bottom: 16px;
            }}
            .category-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
            }}
            .category-name {{
                font-size: 18px;
                font-weight: 700;
                color: #1a1a1a;
            }}
            .category-score {{
                font-size: 24px;
                font-weight: 900;
            }}
            .issues {{
                margin-top: 12px;
            }}
            .issue {{
                padding: 12px;
                background: white;
                border-radius: 8px;
                margin-bottom: 8px;
                border-left: 4px solid #ffc107;
            }}
            .cta {{
                text-align: center;
                margin-top: 40px;
                padding-top: 40px;
                border-top: 2px solid #e0e0e0;
            }}
            .cta-button {{
                display: inline-block;
                padding: 16px 48px;
                background: linear-gradient(135deg, {user.accent_color} 0%, #8766FF 100%);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-size: 18px;
                font-weight: 700;
                margin-bottom: 20px;
            }}
            .download-button {{
                display: inline-block;
                padding: 12px 32px;
                background: white;
                border: 2px solid {user.accent_color};
                color: {user.accent_color};
                text-decoration: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                margin-left: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                {f'<img src="{user.agency_logo}" class="logo" alt="{user.agency_name}">' if user.agency_logo else ''}
                <h1>Your SEO Audit Results</h1>
                <p style="color: #666; margin-top: 12px;">{audit.url}</p>
            </div>
            
            <div style="text-align: center;">
                <div class="score-circle">
                    <svg viewBox="0 0 200 200">
                        <circle cx="100" cy="100" r="90" fill="none" stroke="#e0e0e0" stroke-width="12"/>
                        <circle cx="100" cy="100" r="90" fill="none" stroke="{user.accent_color}" stroke-width="12"
                            stroke-dasharray="{565.48 * score / 100} 565.48" stroke-linecap="round"
                            transform="rotate(-90 100 100)"/>
                    </svg>
                    <div class="score-number">{score}</div>
                </div>
                <p class="score-label">Overall SEO Score</p>
            </div>
            
            <div class="categories">
                {generate_category_html(results)}
            </div>
            
            <div class="cta">
                <h2>Want to Fix These Issues?</h2>
                <p style="color: #666; margin: 16px 0 24px;">Let our experts help you improve your SEO score.</p>
                <a href="{user.agency_url or '#'}" class="cta-button">Get Started</a>
                <a href="/api/embed/download/{job_id}?api_key={api_key}" class="download-button">Download PDF Report</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html)


def generate_category_html(results: dict) -> str:
    """Generate HTML for category results"""
    html = ""
    
    for category, data in results.items():
        if category == 'overall_score' or not isinstance(data, dict):
            continue
        
        score = data.get('score', 0)
        issues = data.get('issues', [])
        
        color = '#4caf50' if score >= 80 else '#ffc107' if score >= 50 else '#f44336'
        
        html += f"""
        <div class="category">
            <div class="category-header">
                <span class="category-name">{category.replace('_', ' ').title()}</span>
                <span class="category-score" style="color: {color};">{score}</span>
            </div>
            <div class="issues">
        """
        
        for issue in issues[:3]:  # Show top 3 issues
            html += f"""
            <div class="issue">
                <strong>{issue.get('severity', 'warning').upper()}:</strong> {issue.get('message', '')}
            </div>
            """
        
        html += "</div></div>"
    
    return html


@router.get("/download/{job_id}")
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
    
    # Generate PDF (simplified - use proper PDF generation in production)
    # Return PDF file
    # This would integrate with your existing PDF generation
    
    return {"message": "PDF download would happen here"}


# ──────────────────────────────────────────────────────────────────────────────
# API Key Management
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/generate-key")
async def generate_embed_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate new embed API key for agency"""
    
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
    
    return {
        "api_key": current_user.embed_api_key,
        "enabled": current_user.embed_enabled,
        "lead_capture": current_user.embed_lead_capture,
        "require_email": current_user.embed_require_email,
        "button_text": current_user.embed_button_text,
        "headline": current_user.embed_headline,
        "description": current_user.embed_description
    }


@router.patch("/settings")
async def update_embed_settings(
    settings: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update embed widget settings"""
    
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
    
    db.commit()
    
    return {"message": "Settings updated successfully"}