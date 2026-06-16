from authlib.integrations.flask_client import OAuth
from flask import current_app

oauth = OAuth()

def init_oauth(app):
    oauth.init_app(app)

    google_conf = app.config.get('GOOGLE_OAUTH')
    kakao_conf = app.config.get('KAKAO_OAUTH')
    naver_conf = app.config.get('NAVER_OAUTH')

    if google_conf and google_conf.get('client_id'):
        oauth.register(
            name='google',
            client_id=google_conf['client_id'],
            client_secret=google_conf['client_secret'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )

    if kakao_conf and kakao_conf.get('client_id'):
        oauth.register(
            name='kakao',
            client_id=kakao_conf['client_id'],
            client_secret=kakao_conf.get('client_secret'),
            authorize_url='https://kauth.kakao.com/oauth/authorize',
            access_token_url='https://kauth.kakao.com/oauth/token',
            userinfo_endpoint='https://kapi.kakao.com/v2/user/me',
            client_kwargs={'scope': 'profile_nickname account_email'},
        )

    if naver_conf and naver_conf.get('client_id'):
        oauth.register(
            name='naver',
            client_id=naver_conf['client_id'],
            client_secret=naver_conf['client_secret'],
            authorize_url='https://nid.naver.com/oauth2.0/authorize',
            access_token_url='https://nid.naver.com/oauth2.0/token',
            userinfo_endpoint='https://openapi.naver.com/v1/nid/me',
            client_kwargs={'scope': 'email name'},
        )
