from flask import Blueprint, request, jsonify, render_template, session, send_file
from models import Post

search_bp = Blueprint('search', __name__)

def _serve_spa():
    import os
    from flask import current_app, send_file
    path = os.path.join(current_app.root_path, 'frontend', 'dist', 'index.html')
    if os.path.exists(path):
        return send_file(path)
    from flask import render_template
    return render_template('intro.html')

@search_bp.route('/search')
def search():
    q = request.args.get('q', '').strip()
    results = {'posts': [], 'shares': [], 'news': []}
    if q:
        results['posts'] = Post.query.filter(
            db.or_(Post.title.ilike(f'%{q}%'), Post.content.ilike(f'%{q}%'))
        ).order_by(Post.created_at.desc()).limit(20).all()
        results['shares'] = ShareReport.query.filter(
            db.or_(ShareReport.title.ilike(f'%{q}%'), ShareReport.description.ilike(f'%{q}%'))
        ).order_by(ShareReport.created_at.desc()).limit(20).all()
        results['news'] = NewsArticle.query.filter(
            db.or_(NewsArticle.title.ilike(f'%{q}%'), NewsArticle.summary.ilike(f'%{q}%')),
            db.or_(NewsArticle.world_admin_approved == True, NewsArticle.kr_yp_admin_approved == True)
        ).order_by(NewsArticle.created_at.desc()).limit(20).all()
    return _serve_spa()

@search_bp.route('/api/rag/search')
def rag_search_api():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'hits': []})
    from services.rag import search
    hits = search(q, top_k=10)
    return jsonify({'hits': hits})

# --- [회원 프로필 & 쪽지] ---
