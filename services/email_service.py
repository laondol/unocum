import smtplib
from email.mime.text import MIMEText
from flask import current_app

class EmailService:
    @staticmethod
    def send(to, subject, body):
        smtp_host = current_app.config.get('SMTP_HOST')
        smtp_port = current_app.config.get('SMTP_PORT', 587)
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
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_addr, [to], msg.as_string())
            server.quit()
            current_app.logger.info(f"Email sent: {subject} → {to}")
            return True
        except Exception as e:
            current_app.logger.error(f"Email failed: {e}")
            print(f"[EMAIL FAIL] {subject} → {to}: {e}")
            return False
