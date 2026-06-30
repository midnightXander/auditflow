# """
# PDF Generation Service - Create professional audit reports
# Supports HTML to PDF conversion with custom branding
# """

# from weasyprint import HTML, CSS
# from io import BytesIO
# from datetime import datetime
# from typing import Dict, Optional, Any
# import logging
# import os
# from pathlib import Path
# from reportlab 
# logger = logging.getLogger(__name__)


# class PDFReportGenerator:
#     """Generate professional PDF reports from audit results"""
    
#     def __init__(self, base_url: str = "http://localhost:8000"):
#         self.base_url = base_url
#         self.output_dir = Path("uploads/pdfs")
#         self.output_dir.mkdir(parents=True, exist_ok=True)
    
#     def generate_audit_report(
#         self,
#         job_id: str,
#         audit_results: Dict[str, Any],
#         lead_info: Dict[str, str],
#         embed_token_data: Dict[str, str],
#         filename: Optional[str] = None
#     ) -> str:
#         """
#         Generate PDF audit report
        
#         Args:
#             job_id: Audit job ID
#             audit_results: Audit results dict with score, issues, etc
#             lead_info: {"first_name", "last_name", "email", "company"}
#             embed_token_data: {"agency_name", "primary_color", "logo_url"}
#             filename: Custom filename (auto-generated if not provided)
        
#         Returns:
#             Path to generated PDF
#         """
        
#         try:
#             filename = filename or f"audit_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
#             filepath = self.output_dir / filename
            
#             # Generate HTML
#             html_content = self._generate_html(
#                 audit_results,
#                 lead_info,
#                 embed_token_data,
#                 job_id
#             )
            
#             # Convert to PDF
#             HTML(string=html_content).write_pdf(str(filepath))
            
#             logger.info(f"[PDF] Generated report: {filepath}")
#             return str(filepath)
        
#         except Exception as e:
#             logger.error(f"[PDF] Error generating report: {e}")
#             raise
    
#     def _generate_html(
#         self,
#         results: Dict[str, Any],
#         lead_info: Dict[str, str],
#         branding: Dict[str, str],
#         job_id: str
#     ) -> str:
#         """Generate HTML report with custom branding"""
        
#         score = results.get("score", 0)
#         issues = results.get("issues", {})
#         timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
#         # Color based on score
#         if score >= 90:
#             score_color = "#10b981"  # Green
#             rating = "Excellent"
#         elif score >= 70:
#             score_color = "#f59e0b"  # Amber
#             rating = "Good"
#         elif score >= 50:
#             score_color = "#f97316"  # Orange
#             rating = "Fair"
#         else:
#             score_color = "#ef4444"  # Red
#             rating = "Needs Work"
        
#         html = f"""
#         <!DOCTYPE html>
#         <html>
#         <head>
#             <meta charset="UTF-8">
#             <style>
#                 * {{
#                     margin: 0;
#                     padding: 0;
#                     box-sizing: border-box;
#                 }}
                
#                 body {{
#                     font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
#                     line-height: 1.6;
#                     color: #333;
#                     background: white;
#                 }}
                
#                 .header {{
#                     background: linear-gradient(135deg, {branding.get('primary_color', '#0075FF')} 0%, {branding.get('accent_color', '#8766FF')} 100%);
#                     color: white;
#                     padding: 40px;
#                     text-align: center;
#                     margin-bottom: 40px;
#                     border-radius: 10px;
#                 }}
                
#                 .logo {{
#                     max-width: 150px;
#                     margin-bottom: 20px;
#                 }}
                
#                 .header h1 {{
#                     font-size: 32px;
#                     margin-bottom: 10px;
#                 }}
                
#                 .header p {{
#                     font-size: 14px;
#                     opacity: 0.9;
#                 }}
                
#                 .lead-info {{
#                     background: #f9fafb;
#                     padding: 20px;
#                     border-radius: 8px;
#                     margin-bottom: 30px;
#                     border-left: 4px solid {branding.get('primary_color', '#0075FF')};
#                 }}
                
#                 .lead-info h3 {{
#                     color: {branding.get('primary_color', '#0075FF')};
#                     margin-bottom: 10px;
#                     font-size: 14px;
#                     text-transform: uppercase;
#                     letter-spacing: 0.5px;
#                 }}
                
#                 .info-grid {{
#                     display: grid;
#                     grid-template-columns: 1fr 1fr;
#                     gap: 20px;
#                     font-size: 13px;
#                 }}
                
#                 .info-item label {{
#                     font-weight: 600;
#                     color: #666;
#                     display: block;
#                     margin-bottom: 4px;
#                 }}
                
#                 .info-item value {{
#                     color: #333;
#                     display: block;
#                 }}
                
#                 .score-section {{
#                     text-align: center;
#                     margin: 40px 0;
#                     padding: 40px;
#                     background: linear-gradient(135deg, rgba({self._hex_to_rgb(score_color)}, 0.1) 0%, rgba({self._hex_to_rgb(score_color)}, 0.05) 100%);
#                     border-radius: 12px;
#                 }}
                
#                 .score-circle {{
#                     display: inline-block;
#                     width: 150px;
#                     height: 150px;
#                     border-radius: 50%;
#                     background: {score_color};
#                     color: white;
#                     display: flex;
#                     align-items: center;
#                     justify-content: center;
#                     margin-bottom: 20px;
#                     flex-direction: column;
#                     box-shadow: 0 10px 30px rgba({self._hex_to_rgb(score_color)}, 0.3);
#                 }}
                
#                 .score-number {{
#                     font-size: 48px;
#                     font-weight: bold;
#                 }}
                
#                 .score-label {{
#                     font-size: 12px;
#                     opacity: 0.9;
#                 }}
                
#                 .score-text {{
#                     font-size: 24px;
#                     font-weight: 600;
#                     color: {score_color};
#                     margin-top: 20px;
#                 }}
                
#                 .issues-section {{
#                     margin: 40px 0;
#                 }}
                
#                 .issues-section h2 {{
#                     font-size: 20px;
#                     margin-bottom: 20px;
#                     color: #333;
#                     border-bottom: 2px solid {branding.get('primary_color', '#0075FF')};
#                     padding-bottom: 10px;
#                 }}
                
#                 .issue-category {{
#                     margin-bottom: 30px;
#                 }}
                
#                 .issue-category h3 {{
#                     font-size: 16px;
#                     color: {branding.get('primary_color', '#0075FF')};
#                     margin-bottom: 15px;
#                     font-weight: 600;
#                 }}
                
#                 .issue-list {{
#                     background: #f9fafb;
#                     border-radius: 8px;
#                     padding: 20px;
#                 }}
                
#                 .issue-item {{
#                     display: flex;
#                     margin-bottom: 12px;
#                     padding-bottom: 12px;
#                     border-bottom: 1px solid #e5e7eb;
#                     font-size: 13px;
#                 }}
                
#                 .issue-item:last-child {{
#                     border-bottom: none;
#                     margin-bottom: 0;
#                     padding-bottom: 0;
#                 }}
                
#                 .issue-icon {{
#                     color: #ef4444;
#                     font-weight: bold;
#                     margin-right: 12px;
#                     min-width: 20px;
#                 }}
                
#                 .recommendations {{
#                     background: #f0fdf4;
#                     border-left: 4px solid #10b981;
#                     padding: 20px;
#                     border-radius: 8px;
#                     margin: 30px 0;
#                     font-size: 13px;
#                 }}
                
#                 .recommendations h3 {{
#                     color: #10b981;
#                     margin-bottom: 10px;
#                     font-size: 14px;
#                 }}
                
#                 .recommendations ul {{
#                     margin-left: 20px;
#                 }}
                
#                 .recommendations li {{
#                     margin-bottom: 8px;
#                 }}
                
#                 .footer {{
#                     margin-top: 50px;
#                     padding-top: 30px;
#                     border-top: 2px solid #e5e7eb;
#                     text-align: center;
#                     font-size: 11px;
#                     color: #666;
#                 }}
                
#                 .cta-button {{
#                     display: inline-block;
#                     background: linear-gradient(135deg, {branding.get('primary_color', '#0075FF')} 0%, {branding.get('accent_color', '#8766FF')} 100%);
#                     color: white;
#                     padding: 15px 30px;
#                     border-radius: 6px;
#                     text-decoration: none;
#                     font-weight: 600;
#                     margin-top: 20px;
#                     font-size: 14px;
#                 }}
                
#                 .page-break {{
#                     page-break-after: always;
#                 }}
                
#                 @media print {{
#                     body {{
#                         margin: 0;
#                         padding: 0;
#                     }}
#                 }}
#             </style>
#         </head>
#         <body>
#             <div class="header">
#                 {f'<img src="{branding.get("logo_url")}" alt="Logo" class="logo">' if branding.get("logo_url") else ''}
#                 <h1>{branding.get("agency_name", "AuditFlow")}</h1>
#                 <p>Website SEO Audit Report</p>
#             </div>
            
#             <div class="lead-info">
#                 <h3>Audit Details</h3>
#                 <div class="info-grid">
#                     <div class="info-item">
#                         <label>Name</label>
#                         <value>{lead_info.get("first_name", "")} {lead_info.get("last_name", "")}</value>
#                     </div>
#                     <div class="info-item">
#                         <label>Email</label>
#                         <value>{lead_info.get("email", "")}</value>
#                     </div>
#                     <div class="info-item">
#                         <label>Company</label>
#                         <value>{lead_info.get("company", "N/A")}</value>
#                     </div>
#                     <div class="info-item">
#                         <label>Website</label>
#                         <value>{lead_info.get("website_url", "")}</value>
#                     </div>
#                     <div class="info-item">
#                         <label>Audit Date</label>
#                         <value>{timestamp}</value>
#                     </div>
#                     <div class="info-item">
#                         <label>Report ID</label>
#                         <value>{job_id[:8].upper()}</value>
#                     </div>
#                 </div>
#             </div>
            
#             <div class="score-section">
#                 <div class="score-circle">
#                     <div class="score-number">{score}</div>
#                     <div class="score-label">/ 100</div>
#                 </div>
#                 <div class="score-text">{rating}</div>
#             </div>
            
#             <div class="issues-section">
#                 <h2>Audit Findings</h2>
                
#                 {self._render_issues(issues, branding)}
#             </div>
            
#             <div class="recommendations">
#                 <h3>✓ Recommended Next Steps</h3>
#                 <ul>
#                     <li>Review critical issues identified above</li>
#                     <li>Prioritize high-impact fixes first</li>
#                     <li>Test changes with another audit scan</li>
#                     <li>Monitor rankings and traffic improvements</li>
#                 </ul>
#             </div>
            
#             <div class="footer">
#                 <p>This report was generated by {branding.get("agency_name", "AuditFlow")} on {timestamp}</p>
#                 <p>For more information, visit {branding.get("agency_url", "https://example.com")}</p>
#             </div>
#         </body>
#         </html>
#         """
        
#         return html
    
#     def _render_issues(self, issues: Dict[str, Any], branding: Dict[str, str]) -> str:
#         """Render issues section with categories"""
        
#         html = ""
        
#         categories = {
#             "critical": ("Critical Issues", "#ef4444"),
#             "warnings": ("Warnings", "#f59e0b"),
#             "suggestions": ("Suggestions", "#3b82f6"),
#         }
        
#         for key, (title, color) in categories.items():
#             if key in issues and issues[key]:
#                 html += f"""
#                 <div class="issue-category">
#                     <h3>{title}</h3>
#                     <div class="issue-list">
#                 """
                
#                 for issue in issues[key][:10]:  # Limit to 10 per category
#                     html += f"""
#                     <div class="issue-item">
#                         <span class="issue-icon">•</span>
#                         <span>{issue}</span>
#                     </div>
#                     """
                
#                 html += """
#                     </div>
#                 </div>
#                 """
        
#         return html
    
#     @staticmethod
#     def _hex_to_rgb(hex_color: str) -> str:
#         """Convert hex color to RGB values (for CSS rgba)"""
#         hex_color = hex_color.lstrip('#')
#         r = int(hex_color[0:2], 16)
#         g = int(hex_color[2:4], 16)
#         b = int(hex_color[4:6], 16)
#         return f"{r}, {g}, {b}"