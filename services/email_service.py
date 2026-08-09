"""
Email Service - Send verification, password reset, and notification emails
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional
import os
from dotenv import load_dotenv
from datetime import datetime

from rq_app import queue
from rq import Retry

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "info@outaudits.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


# from rq_app import queue
# from rq import Retry


def send_email(to_email: str, subject: str, html_content: str, text_content: Optional[str] = None):
    """
    Send email via SMTP
    
    Args:
        to_email: Recipient email
        subject: Email subject
        html_content: HTML email body
        text_content: Plain text fallback (optional)
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"⚠️  Email not configured. Would send to {to_email}: {subject}")
        return
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = FROM_EMAIL
    # msg['From'] = formataddr(("OutAudits Team", FROM_EMAIL))
    # msg['Sender'] = 'OutAudits'
    msg['To'] = to_email
    
    # Add text and HTML parts
    if text_content:
        part1 = MIMEText(text_content, 'plain')
        msg.attach(part1)
    
    part2 = MIMEText(html_content, 'html')
    msg.attach(part2)
    
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"✅ Email sent to {to_email}: {subject}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
    



def send_verification_email(email: str, token: str, user_name: Optional[str] = None):
    
    


    """Send email verification link"""
    
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"
    
    name = user_name or "there"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0075FF 0%, #8766FF 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #0075FF 0%, #8766FF 100%); color: white; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to OutAudits!</h1>
            </div>
            <div class="content">
                <p>Hi {name},</p>
                <p>Thanks for signing up! Please verify your email address to get started.</p>
                <p style="text-align: center;">
                    <a href="{verify_url}" class="button">Verify Email Address</a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="background: white; padding: 15px; border-radius: 5px; word-break: break-all; font-family: monospace; font-size: 12px;">
                    {verify_url}
                </p>
                <p style="margin-top: 30px; color: #666; font-size: 14px;">
                    This link will expire in 24 hours.
                </p>
            </div>
            <div class="footer">
                <p>If you didn't create an account, you can safely ignore this email.</p>
                <p>&copy; {datetime.now().year} OutAudits. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text = f"""
    Welcome to OutAudits!
    
    Hi {name},
    
    Thanks for signing up! Please verify your email address by clicking the link below:
    
    {verify_url}
    
    This link will expire in 24 hours.
    
    If you didn't create an account, you can safely ignore this email.
    """
    
    queue.enqueue(send_email, email, "Verify your OutAudits account", html, text, retry = Retry(max=3, interval=[10, 30, 60]) )


def send_password_reset_email(email: str, token: str, user_name: Optional[str] = None):
    
    """Send password reset link"""
    
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
    
    name = user_name or "there"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0075FF 0%, #8766FF 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #0075FF 0%, #8766FF 100%); color: white; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Reset Your Password</h1>
            </div>
            <div class="content">
                <p>Hi {name},</p>
                <p>We received a request to reset your password. Click the button below to create a new password:</p>
                <p style="text-align: center;">
                    <a href="{reset_url}" class="button">Reset Password</a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="background: white; padding: 15px; border-radius: 5px; word-break: break-all; font-family: monospace; font-size: 12px;">
                    {reset_url}
                </p>
                <div class="warning">
                    <strong>⚠️ Security Notice:</strong> This link will expire in 1 hour. For your security, never share this link with anyone.
                </div>
            </div>
            <div class="footer">
                <p>If you didn't request a password reset, you can safely ignore this email. Your password won't change.</p>
                <p>&copy; {datetime.now().year} OutAudits. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text = f"""
    Reset Your Password
    
    Hi {name},
    
    We received a request to reset your password. Click the link below to create a new password:
    
    {reset_url}
    
    This link will expire in 1 hour.
    
    If you didn't request a password reset, you can safely ignore this email.
    """
    
    queue.enqueue(send_email, email, "Reset your OutAudits password", html, text, retry = Retry(max=3, interval=[10, 30, 60]) )


def send_audit_complete_email(email: str, audit_url: str, score: int, user_name: Optional[str] = None):
    
    """Send notification when audit is complete"""
    
    name = user_name or "there"
    
    # Score-based emoji
    emoji = "🎉" if score >= 90 else "✅" if score >= 70 else "⚠️"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0075FF 0%, #8766FF 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .score {{ font-size: 48px; font-weight: bold; color: #0075FF; text-align: center; margin: 20px 0; }}
            .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #0075FF 0%, #8766FF 100%); color: white; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{emoji} Your Audit is Complete!</h1>
            </div>
            <div class="content">
                <p>Hi {name},</p>
                <p>Great news! Your website audit has finished processing.</p>
                <div class="score">{score}/100</div>
                <p style="text-align: center;">
                    <a href="{audit_url}" class="button">View Full Report</a>
                </p>
            </div>
            <div class="footer">
                <p>&copy; {datetime.now().year} OutAudits. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text = f"""
    {emoji} Your Audit is Complete!
    
    Hi {name},
    
    Your website audit has finished processing.
    
    Score: {score}/100
    
    View your full report: {audit_url}
    """
    
    queue.enqueue(send_email, email, f"Your audit is ready! Score: {score}/100", html, text, retry = Retry(max=3, interval=[10, 30, 60]) )


def send_credits_low_email(email: str, credits_remaining: int, user_name: Optional[str] = None):
    
    """Send notification when credits are running low"""
    
    name = user_name or "there"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #ffc107; color: #333; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .credits {{ font-size: 36px; font-weight: bold; color: #ff5722; text-align: center; margin: 20px 0; }}
            .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #0075FF 0%, #8766FF 100%); color: white; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⚠️ Credits Running Low</h1>
            </div>
            <div class="content">
                <p>Hi {name},</p>
                <p>You're running low on audit credits this month.</p>
                <div class="credits">{credits_remaining} credits remaining</div>
                <p>Upgrade your plan to get more credits and unlock premium features:</p>
                <p style="text-align: center;">
                    <a href="{FRONTEND_URL}/pricing" class="button">View Plans</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    queue.enqueue(send_email, email, f"⚠️ Only {credits_remaining} credits remaining", html, retry = Retry(max=3, interval=[10, 30, 60]) )


def send_trial_start_email(user):
    
    """Send email confirming start of 14-day Pro trial"""
    name = user.full_name or "there"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #2D3748; background-color: #F7FAFC; }}
            .container {{ max-width: 600px; margin: 20px auto; padding: 0; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #00C6FF 0%, #0072FF 100%); color: white; padding: 40px 30px; text-align: center; }}
            .content {{ padding: 40px 30px; }}
            .feature-list {{ margin: 30px 0; padding-left: 0; list-style-type: none; }}
            .feature-item {{ margin-bottom: 15px; padding-left: 30px; position: relative; }}
            .feature-item::before {{ content: "✓"; position: absolute; left: 0; color: #0072FF; font-weight: bold; font-size: 18px; }}
            .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #00C6FF 0%, #0072FF 100%); color: white; text-decoration: none; border-radius: 6px; font-weight: bold; text-align: center; box-shadow: 0 4px 10px rgba(0, 114, 255, 0.3); }}
            .footer {{ text-align: center; padding: 25px; color: #718096; font-size: 12px; background-color: #EDF2F7; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0; font-size: 26px;">🚀 Pro Trial Activated!</h1>
            </div>
            <div class="content">
                <p>Hi {name},</p>
                <p>Welcome to <strong>OutAudits Pro</strong>! Your 14-day free trial is officially active, and we've added <strong>10,000 credits</strong> to your account.</p>
                
                <h3 style="color: #1A202C; margin-top: 30px;">Here is what you can do with Pro:</h3>
                <ul class="feature-list">
                    <li class="feature-item"><strong>Deep Site Crawls:</strong> Crawl up to 500 pages per audit to check for broken links and metadata issues.</li>
                    <li class="feature-item"><strong>Competitor Comparison:</strong> Compare your domain alongside 3 competitors to discover gaps.</li>
                    <li class="feature-item"><strong>Rank Tracking:</strong> Track keyword positions daily across Google and Brave search.</li>
                    <li class="feature-item"><strong>White-Label Reports:</strong> Add your agency branding and logo to professional PDFs.</li>
                </ul>

                <p style="text-align: center; margin: 35px 0 20px;">
                    <a href="{FRONTEND_URL}/dashboard" class="button" style="color: white;">Go to Dashboard</a>
                </p>
            </div>
            <div class="footer">
                <p>Your free trial ends on {user.trial_ends_at.strftime('%Y-%m-%d') if user.trial_ends_at else '14 days'}.</p>
                <p>&copy; {datetime.now().year} OutAudits. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text = f"""
    Pro Trial Activated!
    
    Hi {name},
    
    Welcome to OutAudits Pro! Your 14-day free trial is active and we have added 10,000 credits to your account.
    
    With Pro, you can access:
    - Deep Site Crawls (up to 500 pages)
    - Competitor Comparisons (up to 3 competitors)
    - Daily Rank Tracking
    - White-label PDF reports
    
    Log in to start: {FRONTEND_URL}/dashboard
    """
    
    queue.enqueue(send_email, user.email, "🚀 Your Pro 14-day Free Trial has started!", html, text, retry = Retry(max=3, interval=[10, 30, 60]) )


def send_trial_day3_email(user):
    
    """Send Day 3 email explaining tips and features"""
    name = user.full_name or "there"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #2D3748; background-color: #F7FAFC; }}
            .container {{ max-width: 600px; margin: 20px auto; padding: 0; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center; }}
            .content {{ padding: 40px 30px; }}
            .tip-box {{ background-color: #F7FAFC; border-left: 4px solid #764ba2; padding: 20px; margin-bottom: 25px; border-radius: 0 8px 8px 0; }}
            .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 6px; font-weight: bold; text-align: center; }}
            .footer {{ text-align: center; padding: 25px; color: #718096; font-size: 12px; background-color: #EDF2F7; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0; font-size: 26px;">💡 Supercharge Your SEO</h1>
            </div>
            <div class="content">
                <p>Hi {name},</p>
                <p>You've been in your OutAudits Pro trial for 3 days! We want to make sure you're getting the absolute most value out of your remaining credits.</p>
                
                <div class="tip-box">
                    <h4 style="margin: 0 0 10px; color: #764ba2;">🔍 Tip #1: Setup Rank Tracking</h4>
                    <p style="margin: 0; font-size: 14px;">Monitor your keywords daily. Go to the Rank Tracking page, enter your primary keywords, and observe how your positions fluctuate.</p>
                </div>
                
                <div class="tip-box">
                    <h4 style="margin: 0 0 10px; color: #764ba2;">📊 Tip #2: Run a Competitor Report</h4>
                    <p style="margin: 0; font-size: 14px;">Don't audit in a vacuum! Compare your website's performance, load times, and SEO scores directly side-by-side with your competitors.</p>
                </div>

                <p style="text-align: center; margin: 35px 0 20px;">
                    <a href="{FRONTEND_URL}/dashboard" class="button" style="color: white;">Launch an Audit Now</a>
                </p>
            </div>
            <div class="footer">
                <p>&copy; {datetime.now().year} OutAudits. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text = f"""
    Supercharge Your SEO
    
    Hi {name},
    
    Here are a couple of quick tips to make the most of your OutAudits Pro trial:
    
    1. Setup Rank Tracking: Monitor keyword positions daily across search engines.
    2. Run a Competitor Report: Compare your scores and metrics against up to 3 competitors.
    
    Launch a check here: {FRONTEND_URL}/dashboard
    """
    
    queue.enqueue(send_email, user.email, "💡 Get the most out of your OutAudits Pro Trial", html, text, retry = Retry(max=3, interval=[10, 30, 60]) )


def send_trial_day10_email(user):
    
    """Send Day 10 upgrade reminder email"""
    name = user.full_name or "there"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #2D3748; background-color: #F7FAFC; }}
            .container {{ max-width: 600px; margin: 20px auto; padding: 0; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #FF512F 0%, #DD2476 100%); color: white; padding: 40px 30px; text-align: center; }}
            .content {{ padding: 40px 30px; }}
            .plan-table {{ width: 100%; border-collapse: collapse; margin: 25px 0; }}
            .plan-table th, .plan-table td {{ padding: 12px; border-bottom: 1px solid #E2E8F0; text-align: left; }}
            .plan-table th {{ background-color: #F7FAFC; font-weight: bold; color: #4A5568; }}
            .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #FF512F 0%, #DD2476 100%); color: white; text-decoration: none; border-radius: 6px; font-weight: bold; text-align: center; box-shadow: 0 4px 10px rgba(221, 36, 118, 0.3); }}
            .footer {{ text-align: center; padding: 25px; color: #718096; font-size: 12px; background-color: #EDF2F7; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0; font-size: 26px;">⏳ Your Trial is Wrapping Up</h1>
            </div>
            <div class="content">
                <p>Hi {name},</p>
                <p>Your 14-day OutAudits Pro trial will end in <strong>4 days</strong>. Don't lose access to your keyword histories and audit records!</p>
                
                <h3 style="color: #1A202C; margin-top: 30px;">Pro vs. Free Comparison:</h3>
                <table class="plan-table">
                    <thead>
                        <tr>
                            <th>Feature</th>
                            <th>Free Plan</th>
                            <th>Pro Plan</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Monthly Credits</strong></td>
                            <td>20</td>
                            <td>10,000</td>
                        </tr>
                        <tr>
                            <td><strong>Keyword Tracking</strong></td>
                            <td>None</td>
                            <td>Daily Tracking</td>
                        </tr>
                        <tr>
                            <td><strong>Crawl Page Limit</strong></td>
                            <td>None</td>
                            <td>500 pages</td>
                        </tr>
                        <tr>
                            <td><strong>Agency PDF Branding</strong></td>
                            <td>No</td>
                            <td>Yes</td>
                        </tr>
                    </tbody>
                </table>

                <p style="text-align: center; margin: 35px 0 20px;">
                    <a href="{FRONTEND_URL}/pricing" class="button" style="color: white;">Lock In Pro Plan ($29/mo)</a>
                </p>
            </div>
            <div class="footer">
                <p>&copy; {datetime.now().year} OutAudits. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text = f"""
    Your Trial is Wrapping Up
    
    Hi {name},
    
    Your 14-day OutAudits Pro trial will end in 4 days.
    
    Here is a quick overview of what you lose when you downgrade to Free:
    - Credits drop from 10,000 to just 20 per month.
    - Daily keyword rank tracking is disabled.
    - Crawls will no longer scan up to 500 pages.
    - Custom agency white-label reports are locked.
    
    Lock in Pro plan today for $29/mo: {FRONTEND_URL}/pricing
    """
    
    queue.enqueue(send_email, user.email, "⏳ 4 days left in your Pro Trial", html, text)


def send_trial_expiring_email(user):
    
    """Send Day 13 expiring soon email (contains 30% discount offer)"""
    name = user.full_name or "there"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #2D3748; background-color: #F7FAFC; }}
            .container {{ max-width: 600px; margin: 20px auto; padding: 0; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #f857a6 0%, #ff5858 100%); color: white; padding: 40px 30px; text-align: center; }}
            .content {{ padding: 40px 30px; }}
            .deal-box {{ background-color: #FFF5F5; border: 2px dashed #E53E3E; padding: 25px; margin: 25px 0; border-radius: 8px; text-align: center; }}
            .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #f857a6 0%, #ff5858 100%); color: white; text-decoration: none; border-radius: 6px; font-weight: bold; text-align: center; box-shadow: 0 4px 10px rgba(255, 88, 88, 0.3); }}
            .footer {{ text-align: center; padding: 25px; color: #718096; font-size: 12px; background-color: #EDF2F7; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0; font-size: 26px;">⚠️ Pro Trial Expires Tomorrow</h1>
            </div>
            <div class="content">
                <p>Hi {name},</p>
                <p>Your OutAudits Pro trial expires in exactly <strong>24 hours</strong>. After expiration, your plan will automatically revert to the Free tier, and unused trial credits will be removed.</p>
                
                <div class="deal-box">
                    <h3 style="color: #C53030; margin-top: 0; margin-bottom: 10px;">🎉 Exclusive 30% OFF Upgrade Deal</h3>
                    <p style="margin: 0 0 15px; font-size: 15px;">Upgrade within the next 3 days and get <strong>30% OFF</strong> your first month of the Pro plan.</p>
                    <p style="font-size: 24px; font-weight: bold; margin: 0; color: #2D3748;">$20.30 <span style="font-size: 15px; font-weight: normal; text-decoration: line-through; color: #A0AEC0;">$29.00</span></p>
                </div>

                <p style="text-align: center; margin: 35px 0 20px;">
                    <a href="{FRONTEND_URL}/pricing" class="button" style="color: white;">Claim 30% Off Upgrade</a>
                </p>
            </div>
            <div class="footer">
                <p>&copy; {datetime.now().year} OutAudits. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text = f"""
    Pro Trial Expires Tomorrow!
    
    Hi {name},
    
    Your OutAudits Pro trial expires in exactly 24 hours. Your plan will revert to the Free tier.
    
    To help you stay on Pro, we are giving you an exclusive 30% OFF your first month!
    Upgrade now for just $20.30 (normally $29.00).
    
    Claim discount: {FRONTEND_URL}/pricing
    """
    
    queue.enqueue(send_email, user.email, "⚠️ Action Required: Your Pro Trial expires tomorrow!", html, text)


def send_trial_expired_email(user):
    
    """Send Day 14 trial expired email"""
    name = user.full_name or "there"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #2D3748; background-color: #F7FAFC; }}
            .container {{ max-width: 600px; margin: 20px auto; padding: 0; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); overflow: hidden; }}
            .header {{ background: #4A5568; color: white; padding: 40px 30px; text-align: center; }}
            .content {{ padding: 40px 30px; }}
            .deal-box {{ background-color: #FFF5F5; border: 2px dashed #E53E3E; padding: 25px; margin: 25px 0; border-radius: 8px; text-align: center; }}
            .button {{ display: inline-block; padding: 15px 30px; background: #4A5568; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; text-align: center; }}
            .footer {{ text-align: center; padding: 25px; color: #718096; font-size: 12px; background-color: #EDF2F7; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0; font-size: 26px;">🔒 Your Pro Trial Has Expired</h1>
            </div>
            <div class="content">
                <p>Hi {name},</p>
                <p>Your 14-day OutAudits Pro trial has ended, and your account has reverted to the Free plan. To keep using advanced features and access your previous data, you can upgrade your plan.</p>
                
                <div class="deal-box">
                    <h3 style="color: #C53030; margin-top: 0; margin-bottom: 10px;">⏳ 30% OFF Upgrade Offer Still Active!</h3>
                    <p style="margin: 0 0 15px; font-size: 15px;">We are keeping your 30% discount active for the next **3 days**. Don't miss out!</p>
                    <p style="font-size: 24px; font-weight: bold; margin: 0; color: #2D3748;">$20.30 <span style="font-size: 15px; font-weight: normal; text-decoration: line-through; color: #A0AEC0;">$29.00</span></p>
                </div>

                <p style="text-align: center; margin: 35px 0 20px;">
                    <a href="{FRONTEND_URL}/pricing" class="button" style="color: white; background: linear-gradient(135deg, #f857a6 0%, #ff5858 100%);">Upgrade with 30% Discount</a>
                </p>
            </div>
            <div class="footer">
                <p>&copy; {datetime.now().year} OutAudits. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text = f"""
    Your Pro Trial Has Expired
    
    Hi {name},
    
    Your 14-day OutAudits Pro trial has ended and your account has reverted to the Free plan.
    
    To help you stay on Pro, your 30% discount remains active for the next 3 days!
    Upgrade now for just $20.30 (normally $29.00).
    
    Claim discount: {FRONTEND_URL}/pricing
    """
    
    queue.enqueue(send_email, user.email, "🔒 Your Pro Trial has expired — claim your 30% discount", html, text)


def send_audit_complete_email(
    email: str,
    audit_url: str,
    score: int,
    website_name: Optional[str] = None,
    user_name: Optional[str] = None
):
    """Send notification when an audit completes."""
    name = user_name or "there"
    site = website_name or "your website"
    emoji = "🎉" if score >= 90 else "✅" if score >= 70 else "⚠️"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #0075FF 0%, #8766FF 100%); color: white; padding: 30px; text-align: center; border-radius: 12px 12px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 12px 12px; }}
        .score {{ font-size: 42px; font-weight: bold; color: #1D4ED8; text-align: center; margin: 24px 0; }}
        .button {{ display: inline-block; padding: 14px 28px; background: #1D4ED8; color: white; text-decoration: none; border-radius: 8px; font-weight: 600; }}
        .footer {{ margin-top: 30px; color: #6B7280; font-size: 13px; text-align: center; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>{emoji} Audit Complete</h1>
          <p>Your SEO audit for {site} is ready.</p>
        </div>
        <div class="content">
          <p>Hi {name},</p>
          <p>Your website audit has completed successfully. Review the score and recommendations below:</p>
          <div class="score">{score}/100</div>
          <p style="text-align:center;">
            <a href="{audit_url}" class="button">View Full Audit Report</a>
          </p>
          <p>If you have questions, reply to this email and we’ll help you interpret the results.</p>
        </div>
        <div class="footer">
          <p>&copy; {datetime.now().year} OutAudits</p>
        </div>
      </div>
    </body>
    </html>
    """

    text = f"""
    Audit Complete

    Hi {name},

    Your SEO audit for {site} is complete.

    Score: {score}/100

    View the full report: {audit_url}
    """

    queue.enqueue(
        send_email,
        email,
        f"Your audit is ready — Score {score}/100",
        html,
        text,
        retry=Retry(max=3, interval=[10, 30, 60])
    )


def send_deep_crawl_complete_email(
    email: str,
    crawl_url: str,
    pages_crawled: int,
    issues_found: int,
    website_name: Optional[str] = None,
    user_name: Optional[str] = None
):
    """Send notification when a deep crawl completes."""
    name = user_name or "there"
    site = website_name or "your site"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #0F172A; color: white; padding: 30px; text-align: center; border-radius: 12px 12px 0 0; }}
        .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 12px 12px; }}
        .metrics {{ display: flex; justify-content: space-between; gap: 12px; margin: 24px 0; }}
        .metric-card {{ flex: 1; background: white; padding: 18px; border-radius: 10px; text-align: center; border: 1px solid #E2E8F0; }}
        .metric-value {{ font-size: 28px; font-weight: 700; color: #111827; }}
        .button {{ display: inline-block; padding: 14px 28px; background: #0F172A; color: white; text-decoration: none; border-radius: 8px; font-weight: 600; }}
        .footer {{ margin-top: 30px; color: #6B7280; font-size: 13px; text-align: center; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>Deep Crawl Complete</h1>
          <p>The crawl for {site} has finished.</p>
        </div>
        <div class="content">
          <p>Hi {name},</p>
          <p>Your deep crawl is complete. Here are the summary details:</p>
          <div class="metrics">
            <div class="metric-card">
              <div class="metric-value">{pages_crawled}</div>
              <div>Pages crawled</div>
            </div>
            <div class="metric-card">
              <div class="metric-value">{issues_found}</div>
              <div>Issues found</div>
            </div>
          </div>
          <p style="text-align:center;">
            <a href="{crawl_url}" class="button">View Crawl Report</a>
          </p>
        </div>
        <div class="footer">
          <p>&copy; {datetime.now().year} OutAudits</p>
        </div>
      </div>
    </body>
    </html>
    """

    text = f"""
    Deep Crawl Complete

    Hi {name},

    The deep crawl for {site} is finished.

    Pages crawled: {pages_crawled}
    Issues found: {issues_found}

    View the full report: {crawl_url}
    """

    queue.enqueue(
        send_email,
        email,
        "Deep crawl complete — your report is ready",
        html,
        text,
        retry=Retry(max=3, interval=[10, 30, 60])
    )


def send_comparison_complete_email(
    email: str,
    comparison_url: str,
    target_domain: str,
    competitor_count: int,
    user_name: Optional[str] = None
):
    """Send notification when competitor comparison completes."""
    name = user_name or "there"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #047857; color: white; padding: 30px; text-align: center; border-radius: 12px 12px 0 0; }}
        .content {{ background: #f0fdf4; padding: 30px; border-radius: 0 0 12px 12px; }}
        .highlight {{ font-weight: 700; color: #065f46; }}
        .button {{ display: inline-block; padding: 14px 28px; background: #047857; color: white; text-decoration: none; border-radius: 8px; font-weight: 600; }}
        .footer {{ margin-top: 30px; color: #4B5563; font-size: 13px; text-align: center; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>Competitor Comparison Ready</h1>
          <p>Your analysis is complete for {target_domain}.</p>
        </div>
        <div class="content">
          <p>Hi {name},</p>
          <p>The competitor comparison report is ready. You compared <span class="highlight">{target_domain}</span> against <span class="highlight">{competitor_count}</span> competitor(s).</p>
          <p style="text-align:center;">
            <a href="{comparison_url}" class="button">View Comparison Results</a>
          </p>
          <p>Use this report to identify opportunities, gaps, and quick wins.</p>
        </div>
        <div class="footer">
          <p>&copy; {datetime.now().year} OutAudits</p>
        </div>
      </div>
    </body>
    </html>
    """

    text = f"""
    Competitor Comparison Ready

    Hi {name},

    Your competitor comparison for {target_domain} is complete.
    Competitors compared: {competitor_count}

    View the full report: {comparison_url}
    """

    queue.enqueue(
        send_email,
        email,
        "Competitor comparison complete",
        html,
        text,
        retry=Retry(max=3, interval=[10, 30, 60])
    )


def send_rank_check_complete_email(
    email: str,
    report_url: str,
    domain: str,
    keywords_checked: int,
    top_keywords: Optional[list[str]] = None,
    user_name: Optional[str] = None
):
    """Send notification when a rank check completes."""
    name = user_name or "there"
    top_keywords_list = ""
    if top_keywords:
        top_keywords_list = "<ul>" + "".join(f"<li>{keyword}</li>" for keyword in top_keywords[:5]) + "</ul>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #9333EA; color: white; padding: 30px; text-align: center; border-radius: 12px 12px 0 0; }}
        .content {{ background: #f8f0fc; padding: 30px; border-radius: 0 0 12px 12px; }}
        .badge {{ display: inline-block; background: #fff; border-radius: 999px; padding: 8px 16px; color: #6D28D9; font-weight: 700; margin: 12px 0; }}
        .button {{ display: inline-block; padding: 14px 28px; background: #9333EA; color: white; text-decoration: none; border-radius: 8px; font-weight: 600; }}
        .footer {{ margin-top: 30px; color: #6B7280; font-size: 13px; text-align: center; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>Rank Check Complete</h1>
          <p>Your keyword ranking report for {domain} is ready.</p>
        </div>
        <div class="content">
          <p>Hi {name},</p>
          <p>Your rank check completed for <strong>{domain}</strong>.</p>
          <div class="badge">{keywords_checked} keywords checked</div>
          {top_keywords_list}
          <p style="text-align:center;">
            <a href="{report_url}" class="button">View Rank Report</a>
          </p>
        </div>
        <div class="footer">
          <p>&copy; {datetime.now().year} OutAudits</p>
        </div>
      </div>
    </body>
    </html>
    """

    text = f"""
    Rank Check Complete

    Hi {name},

    The rank check for {domain} is complete.
    Keywords checked: {keywords_checked}

    View your report: {report_url}
    """

    queue.enqueue(
        send_email,
        email,
        f"Rank check complete for {domain}",
        html,
        text,
        retry=Retry(max=3, interval=[10, 30, 60])
    )

def send_audit_widget_lead_email(agency_name: str, lead_email:str, website_url:str, 
                        job_id:str, audit_score: Optional[int], to_email:str,
                          lead_name: Optional[str] = None, lead_company: Optional[str] = None):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; color: #333; background: #f4f6fa; margin: 0; padding: 0; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 24px; }}
        .card {{ background: #ffffff; border-radius: 12px; border: 1px solid #e5e7eb; padding: 32px; }}
        .header {{ color: #111827; font-size: 22px; font-weight: 700; margin-bottom: 16px; }}
        .section-title {{ color: #6b7280; font-size: 14px; text-transform: uppercase; letter-spacing: 0.08em; margin: 24px 0 12px; }}
        .detail {{ margin-bottom: 12px; }}
        .label {{ color: #6b7280; font-size: 14px; }}
        .value {{ color: #111827; font-size: 15px; font-weight: 600; }}
        .button {{ display: inline-block; margin-top: 24px; padding: 14px 26px; background: #00A4C6; color: #ffffff; text-decoration: none; border-radius: 8px; }}
        .footer {{ margin-top: 32px; color: #9CA3AF; font-size: 13px; line-height: 1.5; }}
    </style>
    </head>
    <body>
    <div class="container">
        <div class="card">
        <div class="header">New Embedded Audit Lead</div>
        <p>Hi {agency_name},</p>
        <p>A new lead was captured from your embedded audit widget.</p>

        <div class="section-title">Lead Details</div>
        <div class="detail"><span class="label">Email:</span> <span class="value">{lead_email}</span></div>
        <div class="detail"><span class="label">Name:</span> <span class="value">{lead_name or 'N/A'}</span></div>
        <div class="detail"><span class="label">Company:</span> <span class="value">{lead_company or 'N/A'}</span></div>

        <div class="section-title">Audit</div>
        <div class="detail"><span class="label">Website:</span> <span class="value">{website_url}</span></div>
        <div class="detail"><span class="label">Audit ID:</span> <span class="value">{job_id}</span></div>
        <div class="detail"><span class="label">Score:</span> <span class="value">{audit_score if audit_score is not None else 'Pending'}</span></div>

        <p>If the audit is still processing, you can check the status in the dashboard once it completes.</p>

        <a href="{FRONTEND_URL}/audit/embed" class="button">View Lead in Dashboard</a>

        <div class="footer">
            This request was submitted through your embedded audit widget. 
            If you want to update your widget settings, visit your dashboard.
        </div>
        </div>
    </div>
    </body>
    </html>
    """

    text = f"""
    New Embedded Audit Lead

    Agency: {agency_name}
    Lead email: {lead_email}
    Lead name: {lead_name or 'N/A'}
    Company: {lead_company or 'N/A'}

    Website: {website_url}
    Audit ID: {job_id}
    Score: {audit_score if audit_score is not None else 'Pending'}

    View the lead in your dashboard:
    {FRONTEND_URL}/audit/embed
    """
    subject = f"New Embedded Audit Lead: {lead_email} from {website_url}"
    send_email(to_email, subject, html, text)



if __name__ == "__main__":
    
    # Example usage
    send_verification_email("alexngaikama913@gmail.com", "123456")