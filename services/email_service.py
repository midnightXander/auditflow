"""
Email Service - Send verification, password reset, and notification emails
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@auditflow.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


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
                <h1>Welcome to AuditFlow!</h1>
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
                <p>&copy; {datetime.now().year} AuditFlow. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text = f"""
    Welcome to AuditFlow!
    
    Hi {name},
    
    Thanks for signing up! Please verify your email address by clicking the link below:
    
    {verify_url}
    
    This link will expire in 24 hours.
    
    If you didn't create an account, you can safely ignore this email.
    """
    
    send_email(email, "Verify your AuditFlow account", html, text)


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
                <p>&copy; {datetime.now().year} AuditFlow. All rights reserved.</p>
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
    
    send_email(email, "Reset your AuditFlow password", html, text)


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
                <p>&copy; {datetime.now().year} AuditFlow. All rights reserved.</p>
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
    
    send_email(email, f"Your audit is ready! Score: {score}/100", html, text)


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
    
    send_email(email, f"⚠️ Only {credits_remaining} credits remaining", html)