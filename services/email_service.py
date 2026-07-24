import smtplib
import ssl
import os
from email.mime.text import MIMEText
from flask import current_app

_DEV_MODE = os.environ.get('DEV_MODE') == '1'

class EmailService:
    @staticmethod
    def send(to, subject, body):
        if _DEV_MODE:
            print(f"[DEV EMAIL] To: {to}")
            print(f"[DEV EMAIL] Subject: {subject}")
            print(f"[DEV EMAIL] Body:\\n{body}")
            print(f"[DEV EMAIL] ---")
            return True

        smtp_host = current_app.config.get('SMTP_HOST')
        smtp_port = int(current_app.config.get('SMTP_PORT', 587))
        smtp_user = current_app.config.get('SMTP_USERNAME')
        smtp_pass = current_app.config.get('SMTP_PASSWORD')
        from_addr = current_app.config.get('MAIL_FROM', 'yp@unocum.kr')

        if not smtp_user or not smtp_pass:
            current_app.logger.warning(f"SMTP 미설정: {subject} → {to}")
            print(f"[EMAIL] To: {to}, Subject: {subject}")
            return False

        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = from_addr
        msg['To'] = to

        try:
            use_ssl = (smtp_port == 465)
            if use_ssl:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
            else:
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'):
                    ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
                ctx.set_ciphers('DEFAULT:@SECLEVEL=0')
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                server.starttls(context=ctx)
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_addr, [to], msg.as_string())
            server.quit()
            current_app.logger.info(f"Email sent: {subject} → {to}")
            return True
        except Exception as e:
            current_app.logger.error(f"Email failed: {e}")
            print(f"[EMAIL FAIL] {subject} → {to}: {e}")
            return False
