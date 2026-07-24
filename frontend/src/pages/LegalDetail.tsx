import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { legalApi } from '../lib/api'
import type { LegalPost } from '../lib/types'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

export default function LegalDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [post, setPost] = useState<LegalPost | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [comment, setComment] = useState('')

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true); setError('')
    try {
      const data = await legalApi.get(Number(id))
      setPost(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [id])

  useEffect(() => { load() }, [load])

  const handleComment = async () => {
    if (!id || !comment.trim()) return
    try {
      const res = await legalApi.comment(Number(id), comment.trim())
      if (res.status === 'success') { setComment(''); load() }
    } catch { alert('댓글 등록 실패') }
  }

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />
  if (!post) return <ErrorMessage message="게시글을 찾을 수 없습니다." />

  const comments = ((post as any).comments || '').split('\n').filter(Boolean)

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h4 className="fw-bold">{post.title}</h4>
          <div className="small text-muted mb-3">
            {post.author_name || '익명'} | {post.created_at ? new Date(post.created_at).toLocaleString('ko-KR') : ''}
            {post.is_public && <span className="badge bg-info ms-2">공개</span>}
            {post.status === 'flagged' && <span className="badge bg-warning ms-1">검토필요</span>}
          </div>
          <hr />
          <div className="mb-4" style={{ lineHeight: 1.8 }}>{post.content}</div>

          {post.answer && (
            <div className="bg-success bg-opacity-10 p-3 rounded" style={{ borderLeft: '4px solid #198754' }}>
              <h6 className="fw-bold text-success">노무사 이훈 답변</h6>
              <div style={{ lineHeight: 1.8 }}>{post.answer}</div>
              {(post as any).fee && <div className="mt-2"><strong>상담비</strong> : {(post as any).fee.toLocaleString()}원</div>}
              <small className="text-muted">답변일: {post.answered_at ? new Date(post.answered_at).toLocaleString('ko-KR') : ''}</small>
            </div>
          )}

          {comments.length > 0 && (
            <>
              <h6 className="fw-bold mt-4 mb-2">답글</h6>
              {comments.map((c: any, i: number) => (
                <div key={i} className="card border-0 shadow-sm mb-2" style={{ borderRadius: 8, background: '#f8f9fa' }}>
                  <div className="card-body p-2 small">
                    <div style={{ lineHeight: 1.6 }}>{c}</div>
                  </div>
                </div>
              ))}
            </>
          )}

          <div className="mt-3">
            <textarea className="form-control form-control-sm mb-2" rows={2}
              placeholder="답글을 작성하세요..." value={comment} onChange={e => setComment(e.target.value)} />
            <button className="btn btn-sm btn-success" onClick={handleComment} disabled={!comment.trim()}>등록</button>
          </div>
        </div>
      </div>
      <div className="text-center mt-3">
        <button className="btn btn-sm btn-outline-secondary" onClick={() => navigate('/legal')}>← 목록</button>
      </div>
    </div>
  )
}
