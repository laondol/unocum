import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { newsApi } from '../lib/api'
import type { NewsArticle, NewsComment } from '../lib/types'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

export default function NewsDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [article, setArticle] = useState<({ content?: string } & NewsArticle) | null>(null)
  const [comments, setComments] = useState<NewsComment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [commentText, setCommentText] = useState('')
  const [replyTo, setReplyTo] = useState<number | null>(null)
  const [sending, setSending] = useState(false)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true); setError('')
    try {
      const [a, c] = await Promise.all([
        newsApi.get(Number(id)),
        newsApi.getComments(Number(id)).catch(() => []),
      ])
      setArticle(a)
      setComments(Array.isArray(c) ? c : [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [id])

  useEffect(() => { load() }, [load])

  const handleVote = async (vote: 'like' | 'dislike') => {
    if (!article) return
    try {
      const res = await newsApi.vote(article.id, vote)
      if (res.status === 'success') {
        setArticle(prev => prev ? {
          ...prev,
          like_count: res.likes ?? prev.like_count,
          dislike_count: res.dislikes ?? prev.dislike_count,
        } : prev)
      }
    } catch { /* ignore */ }
  }

  const handleComment = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id || !commentText.trim()) return
    setSending(true)
    try {
      const fd = new FormData()
      fd.append('news_id', id)
      fd.append('content', commentText.trim())
      if (replyTo) fd.append('parent_id', String(replyTo))

      const res = await newsApi.comment(Number(id), commentText.trim(), replyTo || undefined)
      if (res.status === 'success') {
        setCommentText('')
        setReplyTo(null)
        const c = await newsApi.getComments(Number(id)).catch(() => [])
        setComments(Array.isArray(c) ? c : [])
      }
    } catch { alert('댓글 등록 실패') }
    finally { setSending(false) }
  }

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />
  if (!article) return <ErrorMessage message="뉴스를 찾을 수 없습니다." />

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <button className="btn btn-sm btn-outline-secondary mb-3" onClick={() => navigate('/news')}>
        ← 목록으로
      </button>

      <article className="card border-0 shadow-sm mb-4" style={{ borderRadius: 18, overflow: 'hidden' }}>
        {article.image_path && (
          <img src={article.image_path} className="card-img-top" style={{ height: 250, objectFit: 'cover' }} alt={article.title} />
        )}
        <div className="card-body p-4">
          <div className="d-flex flex-wrap gap-2 mb-3">
            <span className="badge bg-success-subtle text-success">{article.category}</span>
            {article.source_name && <span className="badge bg-light text-dark">{article.source_name}</span>}
          </div>
          <h2 className="fw-bold mb-3">{article.title}</h2>
          <div className="" style={{ fontSize: '1.05rem', lineHeight: 1.8 }}>
            {article.content || article.summary || ''}
          </div>
          <hr className="my-4" />
          <div className="d-flex flex-wrap align-items-center gap-3">
            <div className="d-flex gap-2">
              <button className="btn btn-outline-success" onClick={() => handleVote('like')}>
                👍 {article.like_count ?? 0}
              </button>
              <button className="btn btn-outline-danger" onClick={() => handleVote('dislike')}>
                👎 {article.dislike_count ?? 0}
              </button>
            </div>
          </div>
        </div>
      </article>

      <section className="card border-0 shadow-sm mb-4" style={{ borderRadius: 18 }}>
        <div className="card-body p-4">
          <h4 className="fw-bold mb-3">💬 주민 의견</h4>
          <form onSubmit={handleComment} className="mb-4">
            {replyTo && (
              <div className="small text-muted mb-2">
                ↳ 답글 작성 중
                <button type="button" className="btn btn-sm btn-link text-danger p-0 ms-2" onClick={() => setReplyTo(null)}>취소</button>
              </div>
            )}
            <textarea className="form-control mb-2" rows={3}
              placeholder="의견을 남겨주세요."
              value={commentText} onChange={e => setCommentText(e.target.value)} required />
            <button type="submit" className="btn btn-success float-end" disabled={sending || !commentText.trim()}>
              {sending ? '등록 중...' : '등록'}
            </button>
          </form>

          {comments.length === 0 ? (
            <p className="text-center text-muted py-5">아직 의견이 없습니다. 첫 의견을 남겨보세요.</p>
          ) : (
            <div>
              {comments.map(c => (
                <div key={c.id} className="border-bottom pb-3 mb-3">
                  <div className="d-flex justify-content-between">
                    <strong className="small">{c.author_name || '익명'}</strong>
                    <small className="text-muted">{c.created_at ? new Date(c.created_at).toLocaleString('ko-KR') : ''}</small>
                  </div>
                  <p className="mb-1 small">{c.content}</p>
                  <button className="btn btn-sm btn-link text-muted p-0" onClick={() => setReplyTo(c.id)}>↳ 답글</button>
                  {c.replies?.map(r => (
                    <div key={r.id} className="ms-4 mt-2 pt-2 border-start ps-3">
                      <div className="d-flex justify-content-between">
                        <strong className="small">{r.author_name || '익명'}</strong>
                        <small className="text-muted">{r.created_at ? new Date(r.created_at).toLocaleString('ko-KR') : ''}</small>
                      </div>
                      <p className="mb-0 small">{r.content}</p>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
