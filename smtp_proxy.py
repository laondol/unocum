import asyncio, smtplib, ssl, logging, os
from aiosmtpd.controller import Controller

logging.basicConfig(level=logging.INFO, format='[SMTP-PROXY] %(asctime)s %(message)s')
log = logging.getLogger('smtp.proxy')

RELAY_HOST = os.getenv('SMTP_HOST', 'smtp.cafe24.com')
RELAY_PORT = int(os.getenv('SMTP_PORT', '587'))
RELAY_USER = os.getenv('SMTP_USERNAME', 'yp@unocum.kr')
RELAY_PASS = os.getenv('SMTP_PASSWORD', 'cafe0811*')
FROM_ADDR = os.getenv('MAIL_FROM', 'yp@unocum.kr')
LISTEN_PORT = int(os.getenv('PROXY_PORT', '1027'))

def authenticator(server, session, envelope, mechanism, auth_data):
    log.info(f"AUTH {mechanism} from {session.peer}")
    return True

class RelayHandler:
    async def handle_DATA(self, server, session, envelope):
        mail_to = envelope.rcpt_tos
        mail_from = envelope.mail_from
        payload = envelope.content.decode('utf-8', errors='replace')
        log.info(f"Relaying to {mail_to} via {RELAY_HOST}:{RELAY_PORT}")
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'):
                ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
            ctx.set_ciphers('DEFAULT:@SECLEVEL=0')
            with smtplib.SMTP(RELAY_HOST, RELAY_PORT, timeout=15) as s:
                s.starttls(context=ctx)
                s.login(RELAY_USER, RELAY_PASS)
                s.sendmail(mail_from or FROM_ADDR, mail_to, payload)
            log.info(f"Delivered to {mail_to}")
            return '250 OK'
        except Exception as e:
            log.error(f"Relay failed: {e}")
            return f'554 Relay failed: {e}'

if __name__ == '__main__':
    controller = Controller(RelayHandler(), hostname='127.0.0.1', port=LISTEN_PORT, authenticator=authenticator, auth_required=True)
    controller.start()
    log.info(f"SMTP proxy listening on 127.0.0.1:{LISTEN_PORT} -> {RELAY_HOST}:{RELAY_PORT}")
    try:
        asyncio.new_event_loop().run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        controller.stop()
