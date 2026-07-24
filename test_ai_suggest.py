import os, sys, traceback, json
sys.path.insert(0, os.path.dirname(__file__))
os.environ['DB_MODE']='postgresql'
from flask import Flask, session
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.config['SECRET_KEY'] = 'test'
from models import db
db.init_app(app)

from route_modules.news_bp import news_bp
app.register_blueprint(news_bp)

with app.test_request_context('/admin/news/ai-suggest', method='POST', data={'tab': 'world'}):
    session['role'] = 'admin'
    session['user_id'] = 7
    session['username'] = 'test_admin'
    try:
        rv = news_bp.view_functions['admin_news_ai_suggest']()
        print('Status: OK')
        print('Response:', rv[0].decode() if hasattr(rv[0], 'decode') else rv)
    except Exception:
        traceback.print_exc()
