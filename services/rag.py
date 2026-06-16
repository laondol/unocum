import os, json, threading
from datetime import datetime

_embedder = None
_chroma_client = None
_collection = None
_lock = threading.Lock()
COLLECTION_NAME = "yp_community"
CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'chroma')

def _get_embedder():
    global _embedder
    if _embedder is None:
        try:
            import psutil
            mem = psutil.virtual_memory()
            if mem.available < 300 * 1024 * 1024:
                print(f"[RAG] 메모리 부족으로 임베더 로딩 스킵 (available: {mem.available // 1024 // 1024}MB)")
                return None
        except ImportError:
            pass
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', device='cpu')
    return _embedder

def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        import chromadb
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = _chroma_client.get_or_create_collection(name=COLLECTION_NAME)
    return _collection

def _chunk_text(text, max_len=512):
    words = text.split()
    chunks, chunk = [], []
    for w in words:
        chunk.append(w)
        if len(' '.join(chunk)) > max_len:
            chunks.append(' '.join(chunk[:-1]))
            chunk = [chunk[-1]]
    if chunk:
        chunks.append(' '.join(chunk))
    return chunks or [text]

def index_item(item_id, title, content, source_type, url='', author='', created_at=''):
    try:
        col = _get_collection()
        texts = _chunk_text(f"{title}\n{content}")
        embedder = _get_embedder()
        for i, txt in enumerate(texts):
            doc_id = f"{source_type}_{item_id}_{i}"
            meta = {
                'source_type': source_type,
                'item_id': str(item_id),
                'title': title[:200],
                'url': url[:300],
                'author': author[:50],
                'created_at': str(created_at or ''),
                'chunk_index': i
            }
            emb = embedder.encode(txt).tolist()
            col.upsert(ids=[doc_id], embeddings=[emb], metadatas=[meta], documents=[txt])
    except Exception as e:
        print(f"[RAG INDEX] error: {e}")

def remove_item(source_type, item_id):
    try:
        col = _get_collection()
        col.delete(where={'source_type': source_type, 'item_id': str(item_id)})
    except Exception as e:
        print(f"[RAG REMOVE] error: {e}")

def search(query, top_k=5, source_type=None):
    try:
        col = _get_collection()
        embedder = _get_embedder()
        q_emb = embedder.encode(query).tolist()
        where = {'source_type': source_type} if source_type else None
        results = col.query(query_embeddings=[q_emb], n_results=top_k, where=where)
        hits = []
        if results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                hits.append({
                    'id': results['ids'][0][i],
                    'score': results['distances'][0][i] if results['distances'] else 0,
                    'title': results['metadatas'][0][i].get('title', ''),
                    'source_type': results['metadatas'][0][i].get('source_type', ''),
                    'item_id': results['metadatas'][0][i].get('item_id', ''),
                    'text': results['documents'][0][i][:300],
                    'url': results['metadatas'][0][i].get('url', ''),
                    'author': results['metadatas'][0][i].get('author', ''),
                })
        return hits
    except Exception as e:
        print(f"[RAG SEARCH] error: {e}")
        return []

def rebuild_index(app):
    with app.app_context():
        from models import Post, NewsArticle, ShareReport
        try:
            col = _get_collection()
            col.delete(where={})
        except:
            pass
        posts = Post.query.all()
        for p in posts:
            index_item(p.id, p.title or '', p.content or '', 'post', url=f"/post/{p.id}", author=p.author_name or '', created_at=str(p.created_at))
        articles = NewsArticle.query.all()
        for a in articles:
            index_item(a.id, a.title or '', a.summary or '', 'news', url=f"/news/{a.id}", created_at=str(a.created_at))
        shares = ShareReport.query.filter_by(status='approved').all()
        for s in shares:
            index_item(s.id, s.title or '', s.description or '', 'share', url=f"/share/detail/{s.id}", author=s.author_name or '', created_at=str(s.created_at))
        print(f"[RAG] 인덱스 재구축 완료: posts={len(posts)}, news={len(articles)}, shares={len(shares)}")

def build_context(query, top_k=3):
    hits = search(query, top_k=top_k)
    if not hits:
        return ""
    lines = []
    for h in hits:
        lines.append(f"[{h['source_type']}] {h['title']} (작성자: {h['author'] or 'N/A'})")
        lines.append(h['text'])
        lines.append("---")
    return "\n".join(lines)