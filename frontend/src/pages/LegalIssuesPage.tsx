import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'
import EmptyState from '../components/common/EmptyState'

interface LaborIssue {
  id: number
  title: string
  content?: string
  author_name?: string
  comment_count?: number
  labor_approved?: boolean
  created_at?: string
}

export default function LegalIssuesPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [issues, setIssues] = useState<LaborIssue[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [aiKeyword, setAiKeyword] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [showAiModal, setShowAiModal] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res = await fetch('/api/legal/issues')
      if (!res.ok) throw new Error('불러오기 실패')
      const data = await res.json()
      setIssues(Array.isArray(data) ? data : data.issues || [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const handleAiImport = async () => {
    if (!aiKeyword.trim()) return
    setAiLoading(true)
    try {
      const fd = new FormData()
      fd.append('keyword', aiKeyword.trim())
      const res = await fetch('/legal/issues/write', { method: 'POST', body: fd })
      const data = await res.json()
      if (data.status === 'success') {
        setShowAiModal(false)
        setAiKeyword('')
        load()
      } else {
        alert(data.msg || 'AI 가져오기 실패')
      }
    } catch { alert('AI 가져오기 중 오류') }
    finally { setAiLoading(false) }
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    return `${d.getMonth() + 1}/${d.getDate()}`
  }

  const isAdmin = user?.role === 'admin' || user?.role === 'leader'

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h4 className="fw-bold mb-0">노동 게시판</h4>
        <div className="d-flex gap-2">
          {isAdmin && (
            <button className="btn btn-sm btn-outline-info" onClick={() => setShowAiModal(true)}>
              AI 가져오기
            </button>
          )}
          <button className="btn btn-sm btn-success" onClick={() => navigate('/legal/issues/write')}>
            글쓰기
          </button>
        </div>
      </div>

      {issues.length === 0 ? (
        <EmptyState icon="📋" title="등록된 게시글이 없습니다." />
      ) : (
        <div className="row g-3">
          {issues.map(issue => (
            <div key={issue.id} className="col-12">
              <div
                className="card border-0 shadow-sm"
                style={{ borderRadius: 12, cursor: 'pointer' }}
                onClick={() => navigate(`/legal/issues/${issue.id}`)}
              >
                <div className="card-body p-3">
                  <div className="d-flex justify-content-between align-items-start">
                    <h6 className="fw-bold mb-1">{issue.title}</h6>
                    <span className="small text-muted">{formatDate(issue.created_at)}</span>
                  </div>
                  <div className="d-flex justify-content-between align-items-center mt-2">
                    <small className="text-muted">{issue.author_name || '익명'}</small>
                    <small className="text-muted">
                      💬 {issue.comment_count ?? 0}
                    </small>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showAiModal && (
        <div className="modal fade show d-block" tabIndex={-1} style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content" style={{ borderRadius: 16 }}>
              <div className="modal-header">
                <h5 className="fw-bold">AI 자동 가져오기</h5>
                <button type="button" className="btn-close" onClick={() => { setShowAiModal(false); setAiKeyword('') }} />
              </div>
              <div className="modal-body">
                <label className="form-label small fw-bold">키워드 입력</label>
                <input
                  className="form-control"
                  placeholder="검색할 키워드를 입력하세요..."
                  value={aiKeyword}
                  onChange={e => setAiKeyword(e.target.value)}
                />
              </div>
              <div className="modal-footer">
                <button className="btn btn-sm btn-secondary" onClick={() => { setShowAiModal(false); setAiKeyword('') }}>취소</button>
                <button className="btn btn-sm btn-success" onClick={handleAiImport} disabled={aiLoading || !aiKeyword.trim()}>
                  {aiLoading ? '가져오는 중...' : '가져오기'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
