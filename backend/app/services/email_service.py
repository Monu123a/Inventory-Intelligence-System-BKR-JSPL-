import smtplib
import ssl
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.schema import CompanySettings

class EmailService:
    @staticmethod
    def send_email_with_attachment(
        db: Session,
        company_id: int,
        to_email: str,
        subject: str,
        body: str,
        attachment_filename: str,
        attachment_content: bytes,
        content_type: str = "application/pdf"
    ):
        settings = db.query(CompanySettings).filter(CompanySettings.company_id == company_id).first()
        if not settings or not settings.smtp_settings:
            raise HTTPException(status_code=400, detail="SMTP settings not configured for this company")
        
        smtp = settings.smtp_settings
        host = smtp.get("host")
        port = smtp.get("port")
        username = smtp.get("username")
        password = smtp.get("password")
        use_tls = smtp.get("use_tls", True)
        from_email = smtp.get("from_email", username)

        if not all([host, port, username, password]):
            raise HTTPException(status_code=400, detail="Incomplete SMTP configuration")

        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment_content)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{attachment_filename}"')
        msg.attach(part)

        try:
            server = smtplib.SMTP(host, int(port))
            if use_tls:
                context = ssl.create_default_context()
                server.starttls(context=context)
            server.login(username, password)
            server.send_message(msg)
            server.quit()
        except Exception as e:
            logging.error(f"Email sending failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to send email. Please check SMTP configuration.")
