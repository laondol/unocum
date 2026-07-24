import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import type { Post, Comment } from '../lib/types'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

export default function ViewPage() {
  const { postId } = useParams<{ postId: string }>()
  const { user } = useAuth()
  const [post, setPost] = useState<Post | null>(null)
  const [comments, setComments] = useState<Comment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [commentText, setCommentText] = useState('')
  const [sending, setSending] = useState(false)

  const load = useCallback(async () => {
    if (!postId) return
    setLoading(true); setError('')
    try {
      const res = await fetch(`/api/board/post/${postId}`)
      if (!res.ok) throw new Error('불러오기 실패')
      const data = await res.json()
      setPost(data.post || data)
      setComments(data.comments || [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [postId])

  useEffect(() => { load() }, [load])

  const handleVote = async (type: 'like' | 'dislike') => {
    if (!postId) return
    try {
      const res = await fetch(`/post/${type}/${postId}`, { method: 'POST' })
      const data = await res.json()
      if (data.status === 'success') load()
    } catch { alert('투표 중 오류') }
  }

  const handleComment = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!postId || !commentText.trim()) return
    setSending(true)
    try {
      const fd = new FormData()
      fd.append('content', commentText.trim())
      const res = await fetch(`/comment/${postId}`, { method: 'POST', body: fd })
      const data = await res.json()
      if (data.status === 'success') {
        setCommentText('')
        load()
      } else {
        alert(data.msg || '댓글 등록 실패')
      }
    } catch { alert('댓글 등록 중 오류') }
    finally { setSending(false) }
  }

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />
  if (!post) return <ErrorMessage message="게시글을 찾을 수 없습니다." />
  if (post.status === 'hidden' || (post as any).is_visible === false) {
    return (
      <div className="text-center py-5">
        <div className="fs-1 mb-3">🔒</div>
        <h5 className="fw-bold">접근 권한이 없습니다</h5>
      </div>
    )
  }

  const stages = ['제안', '현실화', '하고있는', '했던거']
  const stageIndex = stages.indexOf(post.status || '')
  const progress = stageIndex >= 0 ? ((stageIndex + 1) / stages.length) * 100 : 0
  const isAdminOrLeader = user?.role === 'admin' || user?.role === 'leader'
  const aiSummary = post.ai_summary || ''
  const showAiSummary = (post.total_score ?? 0) > -50

  const renderFileAttachments = () => {
    const filePath = post.file_path
    if (!filePath) return null
    const ext = filePath.split('.').pop()?.toLowerCase()
    if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext || '')) {
      return (
        <div className="mb-3">
          <img src={filePath} className="img-fluid rounded" style={{ maxHeight: 400 }} alt="attachment" />
        </div>
      )
    }
    const isPdf = ext === 'pdf'
    return (
      <div className="mb-3">
        <a href={filePath} className="btn btn-sm btn-outline-primary" target="_blank" rel="noopener noreferrer">
          {isPdf ? '📄 PDF 보기' : '📎 파일 다운로드'}
        </a>
      </div>
    )
  }

  return (
    <div className="row g-4" style={{ maxWidth: 1000, margin: '0 auto' }}>
      <div className="col-lg-8">
        <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
          <div className="card-body p-4">
            {post.category && <span className="badge bg-success mb-2">{post.category}</span>}
            <h3 className="fw-bold mb-2">{post.title}</h3>
            <div className="d-flex gap-3 small text-muted mb-3">
              <span>{post.author_name || '익명'}</span>
              <span>{post.created_at ? new Date(post.created_at).toLocaleString('ko-KR') : ''}</span>
            </div>

            <div className="d-flex gap-2 mb-4">
              <button className="btn btn-outline-success btn-sm" onClick={() => handleVote('like')}>
                👍 {post.like_count ?? 0}
              </button>
              <button className="btn btn-outline-danger btn-sm" onClick={() => handleVote('dislike')}>
                👎 {post.dislike_count ?? 0}
              </button>
            </div>

            {post.total_score != null && post.total_score <= -50 || aiSummary && showAiSummary ? (
              <div className="p-3 bg-light rounded mb-3 border-start border-5 border-info">
                <strong>🤖 AI 요약</strong>
                {post.total_score != null && post.total_score <= -50 ? (
                  <p className="mb-0 mt-1 small">게시불가</p>
                ) : post.ai_score === 0 ? (
                  <p className="mb-0 mt-1 small">검토 진행 중</p>
                ) : (
                  <p className="mb-0 mt-1 small">{aiSummary}</p>
                )}
              </div>
            ) : null}

            {renderFileAttachments()}

            <div className="mb-4" style={{ lineHeight: 1.8 }} dangerouslySetInnerHTML={{ __html: post.content }} />

            <div className="text-center">
              <button className="btn btn-success btn-lg px-5">이 제안에 동의합니다</button>
            </div>
          </div>
        </div>

        <div className="card border-0 shadow-sm mt-4" style={{ borderRadius: 16 }}>
          <div className="card-body p-4">
            <h5 className="fw-bold mb-3">댓글 ({comments.length})</h5>

            <form onSubmit={handleComment} className="mb-4">
              <textarea
                className="form-control mb-2"
                rows={3}
                placeholder="댓글을 작성하세요..."
                value={commentText}
                onChange={e => setCommentText(e.target.value)}
              />
              <button type="submit" className="btn btn-success btn-sm" disabled={sending || !commentText.trim()}>
                {sending ? '등록 중...' : '댓글 등록'}
              </button>
            </form>

            {comments.map(c => (
              <div key={c.id} className="mb-3 p-3 bg-light rounded">
                <div className="d-flex justify-content-between small mb-1">
                  <strong>{c.author || '익명'}</strong>
                  <span className="text-muted">{c.created_at ? new Date(c.created_at).toLocaleString('ko-KR') : ''}</span>
                </div>
                <p className="mb-0">{c.content}</p>
                {c.replies && c.replies.map(r => (
                  <div key={r.id} className="mt-2 ps-3 border-start border-3">
                    <div className="d-flex justify-content-between small">
                      <strong>{r.author || '익명'}</strong>
                      <span className="text-muted">{r.created_at ? new Date(r.created_at).toLocaleString('ko-KR') : ''}</span>
                    </div>
                    <p className="mb-0">{r.content}</p>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="col-lg-4">
        <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
          <div className="card-body p-4">
            <h6 className="fw-bold mb-3">진행 상태</h6>
            <div className="mb-3">
              {stages.map((stage, i) => (
                <div key={stage} className="d-flex align-items-center mb-2">
                  <div
                    className="rounded-circle me-2"
                    style={{
                      width: 20, height: 20,
                      background: i <= stageIndex ? '#198754' : '#dee2e6',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      color: '#fff', fontSize: '0.65rem',
                    }}
                  >
                    {i + 1}
                  </div>
                  <small className={i <= stageIndex ? 'fw-bold' : 'text-muted'}>{stage}</small>
                </div>
              ))}
              <div className="progress mt-2" style={{ height: 6 }}>
                <div className="progress-bar bg-success" style={{ width: `${progress}%` }} />
              </div>
            </div>

            {post.total_score != null && (
              <div className="mb-2">
                <small className="text-muted">총 점수</small>
                <div className={`fw-bold ${post.total_score >= 0 ? 'text-success' : 'text-danger'}`}>
                  {post.total_score > 0 ? '+' : ''}{post.total_score}
                </div>
              </div>
            )}

            {isAdminOrLeader && post.total_score != null && (
              <div className="mt-3 pt-3 border-top">
                <small className="text-muted">관리자 점수</small>
                <div className="d-flex gap-3 mt-1 small">
                  {post.admin_score != null && <span>관리자: {post.admin_score}</span>}
                  {post.leader_score != null && <span>리더: {post.leader_score}</span>}
                  {post.member_score != null && <span>멤버: {post.member_score}</span>}
                </div>
                <div className="fw-bold mt-1">최종: {post.total_score}</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
