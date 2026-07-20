import os
import requests
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app
from datetime import datetime
from sqlalchemy import or_
from models import db, NewsArticle, NewsComment, NewsRecommendation, NewsVote, Post, User, Message
from services.ai_service import call_ai_judge
from services.point_service import add_points

news_bp = Blueprint('news', __name__)

@news_bp.route('/admin/news')
def admin_news():
    if session.get('role') not in ['admin', 'leader']:
        return "권한 없음", 403
    page = request.args.get('page', 1, type=int)
    tab = request.args.get('tab', 'all')
    query = NewsArticle.query
    if tab == 'all':
        query = query.filter(or_(NewsArticle.is_ai_generated == False, NewsArticle.is_selected == True))
    elif tab == 'world':
        query = query.filter(NewsArticle.category.in_(['세계뉴스', '환경뉴스', '건강정보', '복지정보', '농업정보', '관광소식']))
    elif tab == 'kr_yp':
        query = query.filter(NewsArticle.category.in_(['대한민국뉴스', '양평소식', '정책정보', '지역소식']))
    news_list = query.order_by(NewsArticle.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin_news.html', news_list=news_list, tab=tab)

@news_bp.route('/admin/news/ai-suggest', methods=['POST'])
def admin_news_ai_suggest():
    if session.get('role') not in ['admin', 'leader']:
        return jsonify({"status": "error", "msg": "권한 없음"}), 403
    tab = request.form.get('tab', 'world')
    # 회원들이 많이 추천한 인기 카테고리/키워드 수집
    trending_context = ''
    try:
        top_cats = db.session.query(NewsArticle.category, db.func.count(NewsVote.id)).join(NewsVote, NewsVote.news_id == NewsArticle.id).filter(NewsVote.vote == 'like').group_by(NewsArticle.category).order_by(db.func.count(NewsVote.id).desc()).limit(3).all()
        if top_cats:
            cats = [c[0] for c in top_cats if c[0]]
            trending_context = ', '.join(cats)
    except:
        pass
    from services.news_service import ai_search_news
    suggestions = ai_search_news(news_type=tab, trending_context=trending_context)
    if not suggestions:
        return jsonify({"status": "error", "msg": "AI 주제 제안 실패. Groq 서버를 확인하세요."})
    from services.naver_news import search_news
    count = 0
    for item in suggestions:
        title = item.get('title', '')
        if not title:
            continue
        search_lang = 'en' if tab == 'world' else 'ko'
        news_results, news_source = search_news(title, display=1, language=search_lang)
        if news_results:
            real = news_results[0]
            category = item.get('category', '세계뉴스')
            if tab == 'kr_yp' and category not in ['대한민국뉴스', '양평소식', '정책정보', '지역소식']:
                category = '대한민국뉴스'
            elif tab == 'world' and category not in ['세계뉴스', '환경뉴스', '건강정보', '복지정보', '농업정보', '관광소식']:
                category = '세계뉴스'
            ai_reason = item.get('reason', '')
            # 세계뉴스는 영문→한글 번역
            raw_title = real.get('title', title)
            raw_desc = real.get('description', '')
            if tab == 'world' and raw_title:
                try:
                    from services.news_service import _groq_text
                    trans = _groq_text(
                        "Translate English news to natural Korean. Output JSON only.",
                        f"Translate to Korean:\nEN title: {raw_title[:200]}\nEN description: {raw_desc[:500]}\n\nJSON: {{\"title\": \"번역된 제목\", \"description\": \"번역된 내용\"}}",
                        format_json=True
                    )
                    if trans:
                        raw_title = trans.get('title', raw_title) or raw_title
                        raw_desc = trans.get('description', raw_desc) or raw_desc
                except:
                    pass
            article = NewsArticle(
                title=raw_title,
                summary=(raw_desc or '')[:200],
                content=f"<p>{(raw_desc or '')[:1000]}</p>",
                category=category,
                source_url=real.get('url', ''),
                is_ai_generated=False,
                is_selected=True,
                world_admin_approved=False,  # 관리자 승인 대기
                world_ai_approved=False,     # AI 검토 대기
                ai_reason=ai_reason,
                created_by=session.get('user_id'),
                source_name=news_source
            )
            # 한자/일본어 정리
            try:
                from services.news_service import clean_cjk_text
                cleaned_title, cleaned_summary, cleaned_content = clean_cjk_text(article.title, article.summary, article.content)
                article.title = cleaned_title or article.title
                article.summary = cleaned_summary or article.summary
                article.content = cleaned_content or article.content
            except:
                pass
            # AI 승인 자동 True
            if tab == 'world':
                article.world_ai_approved = True
            elif tab == 'kr_yp':
                article.kr_yp_ai_approved = True
            db.session.add(article)
            count += 1
    db.session.commit()
    return jsonify({"status": "success", "count": count, "msg": f"✅ 실제 뉴스 {count}개를 가져왔습니다{' (영문→한글 번역 완료)' if tab == 'world' else ''}."})

@news_bp.route('/admin/news/toggle/<int:news_id>')
def admin_news_toggle(news_id):
    if session.get('role') not in ['admin', 'leader']:
        return "권한 없음", 403
    article = NewsArticle.query.get_or_404(news_id)
    article.is_selected = not article.is_selected
    article.updated_at = datetime.now()
    db.session.commit()
    return redirect(url_for('.admin_news'))

@news_bp.route('/admin/news/approve/<int:news_id>/<string:tab>/<string:approver>')
def admin_news_approve(news_id, tab, approver):
    if session.get('role') not in ['admin', 'leader']:
        return "권한 없음", 403
    article = NewsArticle.query.get_or_404(news_id)
    if tab == 'world':
        if approver == 'ai':
            article.world_ai_approved = not article.world_ai_approved
        elif approver == 'admin':
            article.world_admin_approved = not article.world_admin_approved
    elif tab == 'kr_yp':
        if approver == 'ai':
            article.kr_yp_ai_approved = not article.kr_yp_ai_approved
        elif approver == 'admin':
            article.kr_yp_admin_approved = not article.kr_yp_admin_approved
    article.updated_at = datetime.now()
    db.session.commit()
    return redirect(url_for('admin_news', tab=tab))

@news_bp.route('/admin/news/delete/<int:news_id>')
def admin_news_delete(news_id):
    if session.get('role') not in ['admin', 'leader']:
        return "권한 없음", 403
    article = NewsArticle.query.get_or_404(news_id)
    if article.image_path:
        img_path = os.path.join(current_app.root_path, article.image_path.lstrip('/'))
        try:
            if os.path.exists(img_path): os.remove(img_path)
        except: pass
    db.session.delete(article)
    db.session.commit()
    return redirect(url_for('.admin_news'))

@news_bp.route('/admin/news/create', methods=['GET', 'POST'])
def admin_news_create():
    if session.get('role') not in ['admin', 'leader']:
        return "권한 없음", 403
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            return "<script>alert('제목을 입력하세요.'); history.back();</script>"
        from services.security import validate_upload, secure_save
        img_path = None
        if 'image' in request.files:
            file = request.files['image']
            ok, msg = validate_upload(file)
            if ok:
                try:
                    img_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'news')
                    if not os.path.exists(img_dir): os.makedirs(img_dir)
                    img_path = secure_save(file, img_dir)
                except Exception:
                    pass
        article = NewsArticle(
            title=title,
            summary=request.form.get('summary', ''),
            content=request.form.get('content', ''),
            source_url=request.form.get('source_url', ''),
            source_name=request.form.get('source_name', ''),
            image_path=img_path,
            category=request.form.get('category', '세계뉴스'),
            ai_reason=request.form.get('ai_reason', ''),
            is_selected='is_selected' in request.form,
            created_by=session.get('user_id')
        )
        try:
            ai_res = call_ai_judge(title, request.form.get('content', '')[:500])
            article.ai_score = ai_res.get('score', 0)
        except:
            article.ai_score = 0
        # 한자/일본어 정리
        try:
            from services.news_service import clean_cjk_text
            cleaned_title, cleaned_summary, cleaned_content = clean_cjk_text(article.title, article.summary, article.content)
            article.title = cleaned_title or article.title
            article.summary = cleaned_summary or article.summary
            article.content = cleaned_content or article.content
        except:
            pass
        db.session.add(article)
        db.session.commit()
        return redirect(url_for('.admin_news'))
    return render_template('admin_news_create.html', article=None)

@news_bp.route('/admin/news/edit/<int:news_id>', methods=['GET', 'POST'])
def admin_news_edit(news_id):
    if session.get('role') not in ['admin', 'leader']:
        return "권한 없음", 403
    article = NewsArticle.query.get_or_404(news_id)
    translated = ''
    if request.args.get('translate') == '1' and article.source_url:
        try:
            import requests as req
            r = req.get(article.source_url, headers={'User-Agent':'Mozilla/5.0'}, timeout=10)
            text = r.text[:3000]
            key = current_app.config.get('GROQ_API_KEY','')
            if key:
                prompt = f"다음 내용을 한국어로 번역하세요. 원문 그대로 상세히 번역하세요.\n\n{text}"
                rr = req.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
                    json={"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":prompt}],"max_tokens":1500},
                    timeout=30)
                if rr.status_code == 200:
                    translated = rr.json()["choices"][0]["message"]["content"]
        except: pass
    if request.method == 'POST':
        article.title = request.form.get('title', '').strip()
        article.summary = request.form.get('summary', '')
        article.content = request.form.get('content', '')
        article.source_url = request.form.get('source_url', '')
        article.source_name = request.form.get('source_name', '')
        article.category = request.form.get('category', '세계뉴스')
        article.ai_reason = request.form.get('ai_reason', '')
        article.is_selected = 'is_selected' in request.form
        article.updated_at = datetime.now()
        if 'image' in request.files:
            file = request.files['image']
            from services.security import validate_upload, secure_save
            ok, msg = validate_upload(file)
            if ok:
                try:
                    img_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'news')
                    if not os.path.exists(img_dir): os.makedirs(img_dir)
                    article.image_path = secure_save(file, img_dir)
                except Exception:
                    pass
        try:
            ai_res = call_ai_judge(article.title, article.content[:500])
            article.ai_score = ai_res.get('score', 0)
        except:
            article.ai_score = 0
        # 한자/일본어 정리
        try:
            from services.news_service import clean_cjk_text
            cleaned_title, cleaned_summary, cleaned_content = clean_cjk_text(article.title, article.summary, article.content)
            article.title = cleaned_title or article.title
            article.summary = cleaned_summary or article.summary
            article.content = cleaned_content or article.content
        except:
            pass
        db.session.commit()
        return redirect(url_for('.admin_news'))
    return render_template('admin_news_create.html', article=article, translated=translated)

@news_bp.route('/admin/news/clean-cjk', methods=['POST'])
def admin_news_clean_cjk():
    if session.get('role') not in ['admin', 'leader']:
        return jsonify({"status": "error", "msg": "권한 없음"}), 403
    from services.news_service import clean_cjk_text
    tab = request.form.get('tab', 'all')
    query = NewsArticle.query
    if tab == 'world':
        query = query.filter(NewsArticle.category.in_(['세계뉴스', '환경뉴스', '건강정보', '복지정보', '농업정보', '관광소식']))
    elif tab == 'kr_yp':
        query = query.filter(NewsArticle.category.in_(['대한민국뉴스', '양평소식', '정책정보', '지역소식']))
    articles = query.all()
    count = 0
    for a in articles:
        try:
            cleaned_title, cleaned_summary, cleaned_content = clean_cjk_text(a.title, a.summary, a.content)
            if cleaned_title and cleaned_title != a.title:
                a.title = cleaned_title
            if cleaned_summary and cleaned_summary != a.summary:
                a.summary = cleaned_summary
            if cleaned_content and cleaned_content != a.content:
                a.content = cleaned_content
            a.updated_at = datetime.now()
            count += 1
        except:
            pass
    db.session.commit()
    return jsonify({"status": "success", "count": count, "msg": f"✅ 뉴스 {count}개 한자/일본어 정리 완료"})

@news_bp.route('/admin/news/import-url', methods=['POST'])
def admin_news_import_url():
    if session.get('role') not in ['admin', 'leader']:
        return jsonify({"status": "error", "msg": "권한 없음"}), 403
    url = request.form.get('url', '').strip()
    tab = request.form.get('tab', 'world')
    if not url:
        return jsonify({"status": "error", "msg": "URL을 입력하세요."})
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'utf-8'
        text = resp.text
    except Exception as e:
        return jsonify({"status": "error", "msg": f"페이지를 가져올 수 없습니다: {str(e)}"})
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(text, 'html.parser')
        # 제거할 태그
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript', 'form', 'button']): tag.decompose()
        # 제거할 클래스/아이디 패턴 (UI/광고/네비게이션)
        for pattern in ['gnb', 'lnb', 'menu', 'navi', 'sidebar', 'footer', 'header', 'banner', 'ad ', 'wrap_', 'search', 'comment', 'reply', 'btn_', 'link_']:
            for el in soup.find_all(class_=lambda c: c and pattern in str(c).lower()):
                el.decompose()
            for el in soup.find_all(id=lambda i: i and pattern in str(i).lower()):
                el.decompose()
        # 본문 영역 우선 추출 시도
        main_area = soup.find('article') or soup.find('main') or soup.find('[role="main"]')
        raw_text = main_area.get_text(separator='\n', strip=True) if main_area else soup.get_text(separator='\n', strip=True)
        # 한 줄에 2글자 미만 or 특정 UI 키워드 줄 제거
        ui_keywords = ['본문 바로가기', '카테고리 이동', 'MY메뉴', '검색', '공유하기', 'URL복사', '신고하기',
                       '메뉴 열기', '메뉴 닫기', '이웃추가', '폰트 크기', '폰트크기', '블로그', '카페',
                       '메일', '뉴스', '지도', '로그인', 'MY', '메뉴', '펼쳐보기', '더보기']
        lines = [l for l in raw_text.split('\n')
                 if len(l.strip()) >= 3
                 and not any(kw in l for kw in ui_keywords)]
        body_text = '\n'.join(lines)[:3000]
    except:
        body_text = text[:2000]
    from services.news_service import ai_summarize_url
    result = ai_summarize_url(body_text[:3000])
    if not result:
        result = {"title": "URL에서 가져온 기사", "summary": "AI 요약 실패", "category": "세계뉴스", "is_useful": True}
    # URL을 가져온 탭에 맞게 카테고리 지정
    category = result.get('category', '세계뉴스')
    if tab == 'kr_yp' and category not in ['대한민국뉴스', '양평소식', '정책정보', '지역소식']:
        category = '대한민국뉴스'
    article = NewsArticle(
        title=result.get('title', '가져온 기사'),
        summary=result.get('summary', ''),
        content=f"<p>{body_text[:2000].replace(chr(10), '</p><p>')}</p>",
        source_url=url,
        category=category,
        is_selected=True,
        is_ai_generated=True,
        created_by=session.get('user_id')
    )
    # 한자/일본어 정리
    try:
        from services.news_service import clean_cjk_text
        cleaned_title, cleaned_summary, cleaned_content = clean_cjk_text(article.title, article.summary, article.content)
        article.title = cleaned_title or article.title
        article.summary = cleaned_summary or article.summary
        article.content = cleaned_content or article.content
    except:
        pass
    # AI 승인 자동 True
    if tab == 'world':
        article.world_ai_approved = True
    elif tab == 'kr_yp':
        article.kr_yp_ai_approved = True
    db.session.add(article)
    db.session.commit()
    return jsonify({"status": "success", "news_id": article.id})

@news_bp.route('/news/like/<int:news_id>', methods=['POST'])
def news_like(news_id):
    if not session.get('username'):
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    uid = session['user_id']
    article = NewsArticle.query.get_or_404(news_id)
    existing = NewsVote.query.filter_by(user_id=uid, news_id=news_id).first()
    if existing:
        if existing.vote == 'like':
            return jsonify({"status": "success", "msg": "이미 추천했습니다.", "likes": article.like_count, "dislikes": article.dislike_count})
        existing.vote = 'like'
        article.like_count += 1
        article.dislike_count = max(0, article.dislike_count - 1)
        add_points(uid, 5, 'like', '뉴스 좋아요', news_id)
    else:
        db.session.add(NewsVote(user_id=uid, news_id=news_id, vote='like'))
        article.like_count += 1
        add_points(uid, 5, 'like', '뉴스 좋아요', news_id)
    db.session.commit()
    return jsonify({"status": "success", "likes": article.like_count, "dislikes": article.dislike_count})

@news_bp.route('/news/dislike/<int:news_id>', methods=['POST'])
def news_dislike(news_id):
    if not session.get('username'):
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    uid = session['user_id']
    article = NewsArticle.query.get_or_404(news_id)
    existing = NewsVote.query.filter_by(user_id=uid, news_id=news_id).first()
    if existing:
        if existing.vote == 'dislike':
            return jsonify({"status": "success", "msg": "이미 싫어요했습니다.", "likes": article.like_count, "dislikes": article.dislike_count})
        existing.vote = 'dislike'
        article.dislike_count += 1
        article.like_count = max(0, article.like_count - 1)
    else:
        db.session.add(NewsVote(user_id=uid, news_id=news_id, vote='dislike'))
        article.dislike_count += 1
    db.session.commit()
    return jsonify({"status": "success", "likes": article.like_count, "dislikes": article.dislike_count})

@news_bp.route('/news/<int:news_id>')
def news_detail(news_id):
    article = NewsArticle.query.get_or_404(news_id)
    comments = NewsComment.query.filter_by(news_id=news_id).order_by(NewsComment.created_at.asc()).all()
    return render_template('news_detail.html', article=article, comments=comments)

@news_bp.route('/news/comment', methods=['POST'])
def news_comment():
    if not session.get('username'):
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    news_id = request.form.get('news_id', type=int)
    content = request.form.get('content', '').strip()
    parent_id = request.form.get('parent_id', type=int)
    
    if not news_id or not content:
        return jsonify({"status": "error", "msg": "내용을 입력하세요."})
    
    # AI 검토
    ai_res = call_ai_judge("", content, is_comment=True)
    is_hidden = ai_res.get('score', 0) <= -50
    
    comment = NewsComment(
        news_id=news_id,
        user_id=session.get('user_id'),
        author_name=session.get('username'),
        content=content,
        parent_id=parent_id if parent_id else None,
        ai_score=ai_res.get('score', 0),
        is_hidden=is_hidden
    )
    db.session.add(comment)
    add_points(session['user_id'], 10, 'comment', '뉴스 댓글 작성', news_id)
    db.session.commit()
    
    return jsonify({
        "status": "success",
        "ai_score": ai_res.get('score', 0),
        "is_hidden": is_hidden
    })

@news_bp.route('/news/<int:news_id>/comments')
def news_comments_fragment(news_id):
    comments = NewsComment.query.filter_by(news_id=news_id).order_by(NewsComment.created_at.asc()).all()
    return render_template('news_comment_item.html', comments=comments)

@news_bp.route('/api/news/content/<int:news_id>')
def api_news_content(news_id):
    a = NewsArticle.query.get_or_404(news_id)
    return jsonify({
        'title': a.title,
        'content': a.content or '본문 내용이 없습니다.',
        'category': a.category,
        'summary': a.summary or ''
    })

def _get_news_with_recs(news_list):
    """각 뉴스에 승인된 추천링크 로드"""
    for a in news_list.items:
        a.recs = NewsRecommendation.query.filter_by(news_id=a.id, is_approved=True).order_by(NewsRecommendation.created_at.desc()).limit(3).all()
    return news_list

@news_bp.route('/world-news')
def world_news():
    page = request.args.get('page', 1, type=int)
    news_list = NewsArticle.query.filter(NewsArticle.is_selected == True, NewsArticle.world_admin_approved == True, NewsArticle.category.in_(['세계뉴스', '환경뉴스', '건강정보', '복지정보', '농업정보', '관광소식'])).order_by(NewsArticle.like_count.desc(), NewsArticle.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template('world_news.html', news_list=_get_news_with_recs(news_list), title="세계 뉴스")

@news_bp.route('/yp-news')
def yp_news():
    page = request.args.get('page', 1, type=int)
    news_list = NewsArticle.query.filter(NewsArticle.is_selected == True, db.or_(NewsArticle.world_admin_approved == True, NewsArticle.kr_yp_admin_approved == True)).order_by(NewsArticle.like_count.desc(), NewsArticle.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template('yp_news.html', news_list=_get_news_with_recs(news_list), title="양평 소식")

@news_bp.route('/kr-yp-news')
def kr_yp_news():
    page = request.args.get('page', 1, type=int)
    news_list = NewsArticle.query.filter(
        NewsArticle.is_selected == True,
        NewsArticle.kr_yp_admin_approved == True,
        NewsArticle.category.in_(['대한민국뉴스', '양평소식', '정책정보', '지역소식'])
    ).order_by(NewsArticle.like_count.desc(), NewsArticle.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template('kr_yp_news.html', news_list=_get_news_with_recs(news_list), title="대한민국과양평")

@news_bp.route('/news/<int:news_id>/recommend', methods=['POST'])
def news_recommend(news_id):
    if not session.get('username'):
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    article = NewsArticle.query.get_or_404(news_id)
    title = request.form.get('title', '').strip()
    url = request.form.get('url', '').strip()
    description = request.form.get('description', '').strip()
    if not title or not url:
        return jsonify({"status": "error", "msg": "제목과 URL을 입력하세요."})
    rec = NewsRecommendation(
        news_id=news_id,
        user_id=session.get('user_id'),
        author_name=session.get('username'),
        title=title,
        url=url,
        description=description
    )
    db.session.add(rec)
    db.session.commit()
    return jsonify({"status": "success", "msg": "추천링크가 접수되었습니다. 관리자 승인 후 게시됩니다."})

@news_bp.route('/news/<int:news_id>/recommendations')
def news_recommendations_fragment(news_id):
    recs = NewsRecommendation.query.filter_by(news_id=news_id, is_approved=True).order_by(NewsRecommendation.created_at.desc()).all()
    return render_template('news_recommendation_item.html', recommendations=recs)

@news_bp.route('/admin/news/recommendations')
def admin_news_recommendations():
    if session.get('role') not in ['admin', 'leader']:
        return "권한 없음", 403
    page = request.args.get('page', 1, type=int)
    recs = NewsRecommendation.query.filter_by(is_approved=False).order_by(NewsRecommendation.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin_news_recommendations.html', recs=recs)

@news_bp.route('/admin/news/recommendation/approve/<int:rec_id>')
def admin_news_recommendation_approve(rec_id):
    if session.get('role') not in ['admin', 'leader']:
        return "권한 없음", 403
    rec = NewsRecommendation.query.get_or_404(rec_id)
    rec.is_approved = True
    rec.approved_by = session.get('user_id')
    rec.approved_at = datetime.now()
    db.session.commit()
    return redirect(url_for('.admin_news_recommendations'))

@news_bp.route('/admin/news/recommendation/reject/<int:rec_id>')
def admin_news_recommendation_reject(rec_id):
    if session.get('role') not in ['admin', 'leader']:
        return "권한 없음", 403
    rec = NewsRecommendation.query.get_or_404(rec_id)
    db.session.delete(rec)
    db.session.commit()
    return redirect(url_for('.admin_news_recommendations'))

