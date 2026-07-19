from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app
from models import db, LegalPost, User, Message

legal_bp = Blueprint('legal', __name__)

@legal_bp.route('/legal/issues')
def legal_issues():
    posts = LegalPost.query.filter(LegalPost.password == '', LegalPost.labor_approved == True).order_by(LegalPost.created_at.desc()).limit(30).all()
    return render_template('labor_board.html', posts=posts)

@legal_bp.route('/legal/issues/write', methods=['GET','POST'])
def legal_issues_write():
    if session.get('role') not in ('admin','leader'):
        return "<script>alert('관리자만 작성할 수 있습니다.'); history.back();</script>"
    if request.method == 'POST':
        title = request.form['title']
        content = request.form.get('content','').strip()
        # AI로 노동 관련 내용 가져오기
        if not content:
            keyword = request.form.get('keyword', title)
            try:
                from openai import OpenAI
                client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=current_app.config.get('GROQ_API_KEY',''))
                resp = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role":"system","content":"한국의 최신 노동 관련 이슈에 대해 500자 내외로 정리해줘. 마크다운 없이 일반 텍스트로."},
                              {"role":"user","content":keyword}],
                    temperature=0.5, max_tokens=600
                )
                content = resp.choices[0].message.content
            except Exception as e:
                content = f'AI 콘텐츠 생성 실패: {e}'
        post = LegalPost(title=title, content=content, email=session.get('email',''),
                       author_name=session.get('real_name') or session.get('username','이훈노무사'),
                       user_id=session.get('user_id'), password='')
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('.'))
    return render_template('labor_write.html')

@legal_bp.route('/legal/issues/<int:post_id>')
def legal_issue_detail(post_id):
    post = LegalPost.query.get_or_404(post_id)
    return render_template('labor_detail.html', post=post)

@legal_bp.route('/legal/issues/comment/<int:post_id>', methods=['POST'])
def legal_issue_comment(post_id):
    content = request.form.get('content','').strip()
    if not content:
        return redirect(url_for('legal_issue_detail', post_id=post_id))
    from services.ai_service import moderate_comment
    ok, reason = moderate_comment(content)
    if not ok:
        return f"<script>alert('{reason}'); history.back();</script>"
    post = LegalPost.query.get_or_404(post_id)
    comments = post.comments or ''
    name = session.get('real_name') or session.get('username','익명')
    comments += f'\n[{name}] {content} ({datetime.now().strftime("%m/%d %H:%M")})'
    post.comments = comments
    db.session.commit()
    from services.email_service import EmailService
    EmailService.send('daerilee@gmail.com', f'[노동이슈 댓글] {post.title}',
        f'작성자: {name}\n내용: {content}\n게시글: {post.title}')
    return redirect(url_for('legal_issue_detail', post_id=post_id))

@legal_bp.route('/legal/issues/admin')
def legal_issues_admin():
    if session.get('role') not in ['admin', 'leader']:
        return "권한 없음", 403
    posts = LegalPost.query.filter(LegalPost.password == '').order_by(LegalPost.created_at.desc()).limit(50).all()
    return render_template('labor_admin.html', posts=posts)

@legal_bp.route('/legal/issues/ai-suggest', methods=['POST'])
def legal_issues_ai_suggest():
    if session.get('role') not in ['admin', 'leader']:
        return jsonify({"error":"권한 없음"}), 403
    count = 0
    try:
        import requests as req_lib
        naver_id = current_app.config.get('NAVER_SEARCH_CLIENT_ID','')
        naver_secret = current_app.config.get('NAVER_SEARCH_CLIENT_SECRET','')
        if naver_id and naver_secret:
            # 여러 키워드로 검색
            keywords = ['노동법', '임금체불', '부당해고', '노동위원회']
            all_items = []
            for kw in keywords:
                try:
                    resp = req_lib.get('https://openapi.naver.com/v1/search/news.json',
                        headers={'X-Naver-Client-Id':naver_id,'X-Naver-Client-Secret':naver_secret},
                        params={'query':kw,'display':5,'sort':'date'}, timeout=10)
                    items = resp.json().get('items',[])
                    all_items.extend(items)
                except:
                    pass
            # 중복 제거 (link 기준)
            seen_links = set()
            unique_items = []
            for item in all_items:
                link = item.get('link','')
                if link not in seen_links:
                    seen_links.add(link)
                    unique_items.append(item)
            # 최대 10개
            for item in unique_items[:10]:
                title = item.get('title','').replace('<b>','').replace('</b>','')
                desc = item.get('description','').replace('<b>','').replace('</b>','')
                link = item.get('link','')
                content = f'{desc}\n\n<a href="{link}" target="_blank">원문보기</a>'
                post = LegalPost(title=title, content=content, email=session.get('email',''),
                                author_name=session.get('real_name','이훈노무사'),
                                user_id=session.get('user_id'), password='', labor_approved=False)
                db.session.add(post)
                count += 1
            db.session.commit()
            if count == 0:
                return jsonify({"status":"error","error":"검색 결과를 찾지 못했습니다."})
        else:
            # Naver API 없는 경우 AI로 대체
            from openai import OpenAI
            client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=current_app.config.get('GROQ_API_KEY',''))
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role":"system","content":"한국 최신 노동 이슈 10개. JSON: [{\"title\":\"...\",\"content\":\"...\"}]"},
                          {"role":"user","content":"노동법 임금체불 부당해고"}],
                temperature=0.7, max_tokens=2000
            )
            import json as _json
            items = _json.loads(resp.choices[0].message.content)
            for item in items:
                post = LegalPost(title=item['title'], content=item['content'], email=session.get('email',''),
                                author_name=session.get('real_name','이훈노무사'),
                                user_id=session.get('user_id'), password='', labor_approved=False)
                db.session.add(post)
                count += 1
            db.session.commit()
            if count == 0:
                return jsonify({"status":"error","error":"AI 생성 결과를 찾지 못했습니다."})
    except Exception as e:
        return jsonify({"status":"error","error":f"오류: {str(e)[:80]}"})
    return jsonify({"status":"success","count":count})

@legal_bp.route('/legal/issues/import-url', methods=['POST'])
def legal_issues_import_url():
    if session.get('role') not in ['admin', 'leader']:
        return jsonify({"error":"권한 없음"}), 403
    url = request.form.get('url','').strip()
    if not url:
        return jsonify({"error":"URL 필요"})
    try:
        import requests as req_lib
        from bs4 import BeautifulSoup
        resp = req_lib.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        title = soup.title.string if soup.title else url[:50]
        # 본문 추출 시도
        body = ''
        for p in soup.find_all('p')[:10]:
            if len(p.get_text(strip=True)) > 20:
                body += p.get_text(strip=True) + '\n'
        content = body[:2000] or title
    except Exception as e:
        title, content = url[:50], f'URL 가져오기 실패: {e}'
    post = LegalPost(title=title, content=content, email=session.get('email',''),
                    author_name=session.get('real_name','이훈노무사'),
                    user_id=session.get('user_id'), password='', labor_approved=False)
    db.session.add(post)
    db.session.commit()
    return jsonify({"status":"success","id":post.id})

@legal_bp.route('/legal/issues/toggle/<int:post_id>', methods=['POST'])
def legal_issues_toggle(post_id):
    if session.get('role') not in ['admin', 'leader']:
        return jsonify({"error":"권한 없음"}), 403
    post = LegalPost.query.get_or_404(post_id)
    post.labor_approved = not post.labor_approved
    db.session.commit()
    return jsonify({"status":"success","approved":post.labor_approved})

# --- [심리상담소] ---
