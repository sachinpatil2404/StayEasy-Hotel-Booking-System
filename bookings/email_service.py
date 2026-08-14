import os
import base64
from django.conf import settings
from django.core.mail import send_mail as django_send_mail, EmailMessage as DjangoEmailMessage

def send_email_via_resend(subject, html_content, to_emails, from_email=None, attachments=None):
    """
    Sends an email using Resend HTTP API (HTTPS port 443).
    Bypasses SMTP port restrictions on hosting services like Render Free.
    """
    api_key = getattr(settings, 'RESEND_API_KEY', '') or os.getenv('RESEND_API_KEY', '')
    if not api_key:
        return False

    try:
        import resend
        resend.api_key = api_key

        sender = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'StayEasy <onboarding@resend.dev>')
        if isinstance(to_emails, str):
            to_emails = [to_emails]

        payload = {
            "from": sender,
            "to": to_emails,
            "subject": subject,
            "html": html_content,
        }

        if attachments:
            resend_attachments = []
            for item in attachments:
                if len(item) >= 2:
                    fname = item[0]
                    content = item[1]
                    if isinstance(content, bytes):
                        content = base64.b64encode(content).decode('utf-8')
                    resend_attachments.append({
                        "filename": fname,
                        "content": content
                    })
            if resend_attachments:
                payload["attachments"] = resend_attachments

        resend.Emails.send(payload)
        return True
    except Exception as e:
        print(f"Resend HTTP Email Exception: {e}")
        return False


def send_otp_email(email, otp):
    """
    Sends OTP email using Resend HTTP API if configured, or falls back to Django send_mail.
    """
    subject = "Your Login OTP - StayEasy"
    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; max-width: 500px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 10px;">
        <h2 style="color: #4e63ff;">StayEasy Security</h2>
        <p>Hello,</p>
        <p>Your One-Time Password (OTP) for logging into StayEasy is:</p>
        <div style="background: #f1f5f9; padding: 15px; text-align: center; border-radius: 8px; font-size: 24px; font-weight: 800; letter-spacing: 4px; color: #1e293b;">
            {otp}
        </div>
        <p style="font-size: 12px; color: #64748b; margin-top: 15px;">This OTP is valid for 5 minutes. Do not share it with anyone.</p>
    </div>
    """

    if getattr(settings, 'RESEND_API_KEY', '') or os.getenv('RESEND_API_KEY', ''):
        success = send_email_via_resend(subject, html_content, [email])
        if success:
            return True

    try:
        django_send_mail(
            subject,
            f"Your OTP for login is: {otp}",
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@stayeasy.com'),
            [email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Django send_mail fallback error: {e}")
        return False
