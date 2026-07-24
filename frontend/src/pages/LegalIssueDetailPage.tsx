import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

interface IssueComment {
  id?: number
  content: string
  author_name?: string
  created_at?: string
}

interface LaborIssueDetail {
  id: number
  title: string
  content: string
  author_name?: string
  created_at?: string
  comments?: IssueComment[] | string
}

export default function LegalIssueDetailPage() {
  const { postId } = useParams<{ postId: string }>()
  const navigate = useNavigate()
  const [issue, setIssue] = useState<LaborIssueDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [commentText, setCommentText] = useState('')
  const [sending, setSending] = useState(false)

  const load = useCallback(async () => {
    if (!postId) return
    setLoading(true); setError('')
    try {
      const res = await fetch(`/api/legal/issues/${postId}`)
      if (!res.ok) throw new Error('불러오기 실패')
      const data = await res.json()
      setIssue(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [postId])

  useEffect(() => { load() }, [load])

  const handleComment = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!postId || !commentText.trim()) return
    setSending(true)
    try {
      const fd = new FormData()
      fd.append('content', commentText.trim())
      const res = await fetch(`/api/legal/issues/comment/${postId}`, { method: 'POST', body: fd })
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

  const parseComments = (): IssueComment[] => {
    if (!issue?.comments) return []
    if (Array.isArray(issue.comments)) return issue.comments
    if (typeof issue.comments === 'string') {
      return issue.comments.split('\n').filter(Boolean).map(c => ({ content: c }))
    }
    return []
  }

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />
  if (!issue) return <ErrorMessage message="게시글을 찾을 수 없습니다." />

  const comments = parseComments()

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h4 className="fw-bold mb-2">{issue.title}</h4>
          <div className="d-flex gap-3 small text-muted mb-3">
            <span>{issue.author_name || '익명'}</span>
            <span>{issue.created_at ? new Date(issue.created_at).toLocaleString('ko-KR') : ''}</span>
          </div>
          <hr />
          <div className="mb-4" style={{ lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>{issue.content}</div>

          {comments.length > 0 && (
            <div className="mt-4">
              <h6 className="fw-bold mb-3">댓글 ({comments.length})</h6>
              {comments.map((c, i) => (
                <div key={c.id || i} className="mb-2 p-3 bg-light rounded">
                  {c.author_name && (
                    <div className="small fw-bold mb-1">{c.author_name}</div>
                  )}
                  <p className="mb-0 small">{c.content}</p>
                  {c.created_at && (
                    <small className="text-muted">{new Date(c.created_at).toLocaleString('ko-KR')}</small>
                  )}
                </div>
              ))}
            </div>
          )}

          <form onSubmit={handleComment} className="mt-4">
            <textarea
              className="form-control form-control-sm mb-2"
              rows={3}
              placeholder="댓글을 작성하세요..."
              value={commentText}
              onChange={e => setCommentText(e.target.value)}
            />
            <button type="submit" className="btn btn-success btn-sm" disabled={sending || !commentText.trim()}>
              {sending ? '등록 중...' : '댓글 등록'}
            </button>
          </form>
        </div>
      </div>
      <div className="text-center mt-3">
        <button className="btn btn-sm btn-outline-secondary" onClick={() => navigate('/legal/issues')}>
          ← 목록으로
        </button>
      </div>
    </div>
  )
}
