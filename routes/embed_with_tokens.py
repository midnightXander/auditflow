# # Add these endpoints before the health check

# import secrets
# import secrets
# from fastapi.responses import HTMLResponse, JSONResponse

# # ──────────────────────────────────────────────────────────────────────────────
# # EMBED ENDPOINTS - White-label audit tool for agencies
# # ──────────────────────────────────────────────────────────────────────────────

# @app.post("/api/embed/tokens", response_model=EmbedTokenResponse)
# async def create_embed_token(
#     token_data: EmbedTokenCreate,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Create white-label embed token for agency
#     Pro/Agency plan only
#     """
    
#     # Check plan
#     if current_user.plan not in ["pro", "agency"]:
#         raise HTTPException(
#             status_code=403,
#             detail="Embed feature requires Pro or Agency plan"
#         )
    
#     # Generate unique token
#     embed_token = secrets.token_urlsafe(32)
    
#     # Validate custom domain (if provided)
#     if token_data.custom_domain:
#         existing = db.query(EmbedToken).filter(
#             EmbedToken.custom_domain == token_data.custom_domain
#         ).first()
#         if existing:
#             raise HTTPException(
#                 status_code=400,
#                 detail="Custom domain already claimed"
#             )
    
#     # Create token
#     db_token = EmbedToken(
#         user_id=current_user.id,
#         token=embed_token,
#         agency_name=token_data.agency_name,
#         agency_logo_url=token_data.agency_logo_url,
#         primary_color=token_data.primary_color,
#         accent_color=token_data.accent_color,
#         show_branding=token_data.show_branding,
#         custom_domain=token_data.custom_domain,
#         callback_url=token_data.callback_url,
#         allowed_domains=token_data.allowed_domains,
#         monthly_audits_limit=token_data.monthly_audits_limit
#     )
    
#     db.add(db_token)
#     db.commit()
#     db.refresh(db_token)
    
#     logger.info(f"[EMBED] Created token for user {current_user.id}: {token_data.agency_name}")
    
#     return EmbedTokenResponse.model_validate(db_token)


# @app.get("/api/embed/tokens")
# async def list_embed_tokens(
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """List user's embed tokens"""
    
#     tokens = db.query(EmbedToken).filter(EmbedToken.user_id == current_user.id).all()
    
#     return {
#         "total": len(tokens),
#         "tokens": [EmbedTokenResponse.model_validate(t) for t in tokens]
#     }


# @app.get("/api/embed/tokens/{token_id}", response_model=EmbedTokenResponse)
# async def get_embed_token(
#     token_id: int,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Get embed token details"""
    
#     token = db.query(EmbedToken).filter(
#         EmbedToken.id == token_id,
#         EmbedToken.user_id == current_user.id
#     ).first()
    
#     if not token:
#         raise HTTPException(status_code=404, detail="Token not found")
    
#     return EmbedTokenResponse.model_validate(token)


# @app.patch("/api/embed/tokens/{token_id}", response_model=EmbedTokenResponse)
# async def update_embed_token(
#     token_id: int,
#     update_data: EmbedTokenUpdate,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Update embed token customization"""
    
#     token = db.query(EmbedToken).filter(
#         EmbedToken.id == token_id,
#         EmbedToken.user_id == current_user.id
#     ).first()
    
#     if not token:
#         raise HTTPException(status_code=404, detail="Token not found")
    
#     # Update fields
#     update_dict = update_data.model_dump(exclude_unset=True)
#     for field, value in update_dict.items():
#         setattr(token, field, value)
    
#     token.updated_at = datetime.utcnow()
#     db.commit()
#     db.refresh(token)
    
#     return EmbedTokenResponse.model_validate(token)


# @app.delete("/api/embed/tokens/{token_id}")
# async def delete_embed_token(
#     token_id: int,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Delete embed token"""
    
#     token = db.query(EmbedToken).filter(
#         EmbedToken.id == token_id,
#         EmbedToken.user_id == current_user.id
#     ).first()
    
#     if not token:
#         raise HTTPException(status_code=404, detail="Token not found")
    
#     db.delete(token)
#     db.commit()
    
#     return {"status": "deleted"}


# @app.get("/embed/{embed_token}", response_class=HTMLResponse)
# async def embed_audit_page(
#     embed_token: str,
#     db: Session = Depends(get_db)
# ):
#     """
#     Embedded audit tool page
#     Loads the interactive audit form with agency branding
#     """
    
#     # Get token and validate
#     token = db.query(EmbedToken).filter(EmbedToken.token == embed_token).first()
    
#     if not token or not token.is_active:
#         return HTMLResponse(
#             content="<h1>Embed token not found or inactive</h1>",
#             status_code=404
#         )
    
#     # Generate HTML with custom styling
#     html = f"""
#     <!DOCTYPE html>
#     <html lang="en">
#     <head>
#         <meta charset="UTF-8">
#         <meta name="viewport" content="width=device-width, initial-scale=1.0">
#         <title>{token.agency_name} - Website Audit</title>
#         <style>
#             * {{
#                 margin: 0;
#                 padding: 0;
#                 box-sizing: border-box;
#             }}
            
#             body {{
#                 font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
#                 background: linear-gradient(135deg, {token.primary_color} 0%, {token.accent_color} 100%);
#                 min-height: 100vh;
#                 display: flex;
#                 align-items: center;
#                 justify-content: center;
#                 padding: 20px;
#             }}
            
#             .container {{
#                 background: white;
#                 border-radius: 12px;
#                 box-shadow: 0 20px 60px rgba(0,0,0,0.15);
#                 max-width: 500px;
#                 width: 100%;
#                 padding: 40px;
#             }}
            
#             .header {{
#                 text-align: center;
#                 margin-bottom: 30px;
#             }}
            
#             .logo {{
#                 max-width: 200px;
#                 margin: 0 auto 20px;
#                 display: block;
#             }}
            
#             .header h1 {{
#                 font-size: 28px;
#                 color: #222;
#                 margin-bottom: 10px;
#             }}
            
#             .header p {{
#                 color: #666;
#                 font-size: 14px;
#             }}
            
#             .form-group {{
#                 margin-bottom: 20px;
#             }}
            
#             label {{
#                 display: block;
#                 font-weight: 600;
#                 margin-bottom: 8px;
#                 color: #333;
#                 font-size: 14px;
#             }}
            
#             input {{
#                 width: 100%;
#                 padding: 12px;
#                 border: 2px solid #e0e0e0;
#                 border-radius: 6px;
#                 font-size: 14px;
#                 transition: border-color 0.3s;
#             }}
            
#             input:focus {{
#                 outline: none;
#                 border-color: {token.primary_color};
#             }}
            
#             input::placeholder {{
#                 color: #999;
#             }}
            
#             .submit-btn {{
#                 width: 100%;
#                 padding: 12px;
#                 background: linear-gradient(135deg, {token.primary_color} 0%, {token.accent_color} 100%);
#                 color: white;
#                 border: none;
#                 border-radius: 6px;
#                 font-weight: 600;
#                 cursor: pointer;
#                 font-size: 16px;
#                 transition: transform 0.2s, box-shadow 0.2s;
#             }}
            
#             .submit-btn:hover {{
#                 transform: translateY(-2px);
#                 box-shadow: 0 10px 20px rgba(0,0,0,0.15);
#             }}
            
#             .submit-btn:active {{
#                 transform: translateY(0);
#             }}
            
#             .loading {{
#                 display: none;
#                 text-align: center;
#                 margin: 20px 0;
#             }}
            
#             .spinner {{
#                 width: 40px;
#                 height: 40px;
#                 border: 4px solid #f3f3f3;
#                 border-top: 4px solid {token.primary_color};
#                 border-radius: 50%;
#                 animation: spin 1s linear infinite;
#                 margin: 0 auto;
#             }}
            
#             @keyframes spin {{
#                 0% {{ transform: rotate(0deg); }}
#                 100% {{ transform: rotate(360deg); }}
#             }}
            
#             .results {{
#                 display: none;
#                 margin-top: 20px;
#             }}
            
#             .score {{
#                 font-size: 48px;
#                 font-weight: bold;
#                 text-align: center;
#                 color: {token.primary_color};
#                 margin: 20px 0;
#             }}
            
#             .branding {{
#                 text-align: center;
#                 margin-top: 30px;
#                 padding-top: 20px;
#                 border-top: 1px solid #eee;
#                 font-size: 12px;
#                 color: #999;
#             }}
#         </style>
#     </head>
#     <body>
#         <div class="container">
#             <div class="header">
#                 {f'<img src="{token.agency_logo_url}" alt="{token.agency_name}" class="logo">' if token.agency_logo_url else ''}
#                 <h1>{token.agency_name}</h1>
#                 <p>Get a comprehensive SEO audit in seconds</p>
#             </div>
            
#             <form id="auditForm">
#                 <div class="form-group">
#                     <label for="url">Website URL *</label>
#                     <input 
#                         type="url" 
#                         id="url" 
#                         name="url" 
#                         placeholder="https://example.com" 
#                         required
#                     >
#                 </div>
                
#                 <div class="form-group">
#                     <label for="email">Email (Optional)</label>
#                     <input 
#                         type="email" 
#                         id="email" 
#                         name="email" 
#                         placeholder="your@email.com"
#                     >
#                 </div>
                
#                 <button type="submit" class="submit-btn">Start Audit</button>
#             </form>
            
#             <div class="loading" id="loading">
#                 <div class="spinner"></div>
#                 <p style="margin-top: 10px; color: #666;">Analyzing website...</p>
#             </div>
            
#             <div class="results" id="results">
#                 <h2 style="text-align: center; margin-bottom: 20px;">Audit Results</h2>
#                 <div class="score" id="scoreDisplay"></div>
#                 <div id="resultsSummary"></div>
#                 <button 
#                     onclick="window.location.reload()" 
#                     class="submit-btn" 
#                     style="margin-top: 20px;"
#                 >
#                     Audit Another Site
#                 </button>
#             </div>
            
#             {f'<div class="branding">Powered by AuditFlow</div>' if token.show_branding else ''}
#         </div>
        
#         <script>
#             const EMBED_TOKEN = "{embed_token}";
#             const API_URL = "{FRONTEND_URL or 'https://api.yourdomain.com'}";
            
#             document.getElementById('auditForm').addEventListener('submit', async (e) => {{
#                 e.preventDefault();
                
#                 const url = document.getElementById('url').value;
#                 const email = document.getElementById('email').value;
                
#                 document.getElementById('auditForm').style.display = 'none';
#                 document.getElementById('loading').style.display = 'block';
                
#                 try {{
#                     // Create audit via embed token (no auth needed)
#                     const response = await fetch(`${{API_URL}}/api/embed/audit`, {{
#                         method: 'POST',
#                         headers: {{
#                             'Content-Type': 'application/json',
#                         }},
#                         body: JSON.stringify({{
#                             url: url,
#                             email: email,
#                             embed_token: EMBED_TOKEN
#                         }})
#                     }});
                    
#                     const data = await response.json();
                    
#                     if (!response.ok) {{
#                         throw new Error(data.detail || 'Audit failed');
#                     }}
                    
#                     // Poll for results
#                     const jobId = data.job_id;
#                     pollResults(jobId);
                    
#                 }} catch (error) {{
#                     document.getElementById('loading').style.display = 'none';
#                     document.getElementById('auditForm').style.display = 'block';
#                     alert('Error: ' + error.message);
#                 }}
#             }});
            
#             async function pollResults(jobId) {{
#                 for (let i = 0; i < 120; i++) {{ // Poll for max 2 minutes
#                     try {{
#                         const response = await fetch(`${{API_URL}}/api/embed/audit/${{jobId}}`);
#                         const data = await response.json();
                        
#                         if (data.status === 'completed') {{
#                             showResults(data);
#                             return;
#                         }}
                        
#                         if (data.status === 'failed') {{
#                             throw new Error(data.error || 'Audit failed');
#                         }}
                        
#                         // Wait before polling again
#                         await new Promise(r => setTimeout(r, 1000));
#                     }} catch (error) {{
#                         console.error('Poll error:', error);
#                     }}
#                 }}
                
#                 throw new Error('Audit timeout');
#             }}
            
#             function showResults(data) {{
#                 document.getElementById('loading').style.display = 'none';
#                 document.getElementById('results').style.display = 'block';
                
#                 const score = data.results?.score || 0;
#                 document.getElementById('scoreDisplay').textContent = score + '/100';
                
#                 const summary = data.results?.summary || 'Audit complete';
#                 document.getElementById('resultsSummary').innerHTML = `
#                     <p style="text-align: center; color: #666;">${{summary}}</p>
#                 `;
#             }}
#         </script>
#     </body>
#     </html>
#     """
    
#     return HTMLResponse(content=html)


# @app.post("/api/embed/audit", response_model=AuditResponse)
# async def create_embed_audit(
#     url: str,
#     email: Optional[str] = None,
#     embed_token: str = None,
#     db: Session = Depends(get_db)
# ):
#     """
#     Create audit from embedded form (no auth required)
#     Validates embed token and enforces rate limits
#     """
    
#     # Validate token
#     token = db.query(EmbedToken).filter(EmbedToken.token == embed_token).first()
    
#     if not token or not token.is_active:
#         raise HTTPException(status_code=401, detail="Invalid embed token")
    
#     # Check monthly limit
#     if token.current_month_audits >= token.monthly_audits_limit:
#         raise HTTPException(
#             status_code=429,
#             detail=f"Monthly audit limit ({token.monthly_audits_limit}) reached"
#         )
    
#     # Create audit
#     job_id = str(uuid.uuid4())
#     audit = Audit(
#         job_id=job_id,
#         user_id=token.user_id,
#         embed_token_id=token.id,
#         url=url,
#         status="pending",
#         progress=0,
#         client_name=email or "Embedded Audit"
#     )
    
#     db.add(audit)
    
#     # Increment usage
#     token.current_month_audits += 1
#     db.commit()
    
#     # Run audit
#     run_audit_task.delay(job_id, url, token.user_id)
    
#     logger.info(f"[EMBED] Audit created via token {embed_token}: {url}")
    
#     return AuditResponse(job_id=job_id, status="pending")


# @app.get("/api/embed/audit/{job_id}", response_model=AuditStatus)
# async def get_embed_audit(job_id: str, db: Session = Depends(get_db)):
#     """Get embed audit status (no auth, uses embed_token for access)"""
    
#     audit = db.query(Audit).filter(Audit.job_id == job_id).first()
    
#     if not audit:
#         raise HTTPException(status_code=404, detail="Audit not found")
    
#     # Note: In production, verify the requester has access via token
    
#     return AuditStatus(
#         job_id=audit.job_id,
#         status=audit.status,
#         progress=audit.progress,
#         results=audit.results,
#         error=audit.error
#     )