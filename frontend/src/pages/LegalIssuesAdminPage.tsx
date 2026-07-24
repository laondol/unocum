import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

interface LaborPost {
  id: number
  title: string
  content?: string
  author_name?: string
  labor_approved?: boolean
  created_at?: string
}

export default function LegalIssuesAdminPage() {
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()
  const [tab, setTab] = useState<'suggest' | 'url' | 'write' | 'list'>('list')
  const [posts, setPosts] = useState<LaborPost[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [suggestResult, setSuggestResult] = useState('')
  const [suggestLoading, setSuggestLoading] = useState(false)

  const [importUrl, setImportUrl] = useState('')
  const [importLoading, setImportLoading] = useState(false)

  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [sending, setSending] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res = await fetch('/api/legal/issues')
      if (!res.ok) throw new Error('불러오기 실패')
      const data = await res.json()
      setPosts(Array.isArray(data) ? data : data.issues || [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { if (tab === 'list') load() }, [tab, load])

  useEffect(() => {
    if (!authLoading && (!user || (user.role !== 'admin' && user.role !== 'leader'))) {
      navigate('/legal/issues')
    }
  }, [user, authLoading, navigate])

  const handleAiSuggest = async () => {
    setSuggestLoading(true); setSuggestResult('')
    try {
      const res = await fetch('/legal/issues/ai-suggest', { method: 'POST' })
      const data = await res.json()
      setSuggestResult(data.suggestion || data.result || JSON.stringify(data))
    } catch { setSuggestResult('AI 추천 중 오류가 발생했습니다.') }
    finally { setSuggestLoading(false) }
  }

  const handleImportUrl = async () => {
    if (!importUrl.trim()) return
    setImportLoading(true)
    try {
      const fd = new FormData()
      fd.append('url', importUrl.trim())
      const res = await fetch('/legal/issues/import-url', { method: 'POST', body: fd })
      const data = await res.json()
      if (data.status === 'success') {
        setImportUrl('')
        alert('가져오기 성공')
      } else {
        alert(data.msg || '가져오기 실패')
      }
    } catch { alert('URL 가져오기 중 오류') }
    finally { setImportLoading(false) }
  }

  const handleWrite = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !content.trim()) return
    setSending(true)
    try {
      const fd = new FormData()
      fd.append('title', title.trim())
      fd.append('content', content.trim())
      const res = await fetch('/api/legal/issues/write', { method: 'POST', body: fd })
      const data = await res.json()
      if (data.id || data.status === 'success') {
        setTitle('')
        setContent('')
        alert('등록 성공')
        setTab('list')
      } else {
        alert(data.msg || '등록 실패')
      }
    } catch { alert('등록 중 오류') }
    finally { setSending(false) }
  }

  const handleToggle = async (id: number) => {
    try {
      const res = await fetch(`/legal/issues/toggle/${id}`, { method: 'POST' })
      const data = await res.json()
      if (data.status === 'success') load()
      else alert(data.msg || '토글 실패')
    } catch { alert('상태 변경 중 오류') }
  }

  if (authLoading) return <Loading />

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h4 className="fw-bold mb-3">노동 게시판 관리</h4>

      <ul className="nav nav-tabs mb-4">
        <li className="nav-item">
          <button className={`nav-link ${tab === 'suggest' ? 'active' : ''}`} onClick={() => setTab('suggest')}>
            AI 추천
          </button>
        </li>
        <li className="nav-item">
          <button className={`nav-link ${tab === 'url' ? 'active' : ''}`} onClick={() => setTab('url')}>
            URL 가져오기
          </button>
        </li>
        <li className="nav-item">
          <button className={`nav-link ${tab === 'write' ? 'active' : ''}`} onClick={() => setTab('write')}>
            직접작성
          </button>
        </li>
        <li className="nav-item">
          <button className={`nav-link ${tab === 'list' ? 'active' : ''}`} onClick={() => setTab('list')}>
            목록
          </button>
        </li>
      </ul>

      {tab === 'suggest' && (
        <div className="card border-0 shadow-sm p-4" style={{ borderRadius: 16 }}>
          <p className="small text-muted mb-3">AI가 추천하는 노동 이슈를 확인합니다.</p>
          <button className="btn btn-info mb-3" onClick={handleAiSuggest} disabled={suggestLoading}>
            {suggestLoading ? '추천 중...' : 'AI 추천 받기'}
          </button>
          {suggestResult && (
            <div className="p-3 bg-light rounded" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
              {suggestResult}
            </div>
          )}
        </div>
      )}

      {tab === 'url' && (
        <div className="card border-0 shadow-sm p-4" style={{ borderRadius: 16 }}>
          <div className="mb-3">
            <label className="form-label small fw-bold">URL</label>
            <div className="d-flex gap-2">
              <input className="form-control" value={importUrl} onChange={e => setImportUrl(e.target.value)} placeholder="가져올 URL" />
              <button className="btn btn-info" onClick={handleImportUrl} disabled={importLoading || !importUrl.trim()}>
                {importLoading ? '가져오는 중...' : '가져오기'}
              </button>
            </div>
          </div>
        </div>
      )}

      {tab === 'write' && (
        <form onSubmit={handleWrite} className="card border-0 shadow-sm p-4" style={{ borderRadius: 16 }}>
          <div className="mb-3">
            <label className="form-label small fw-bold">제목</label>
            <input className="form-control" value={title} onChange={e => setTitle(e.target.value)} placeholder="제목" />
          </div>
          <div className="mb-3">
            <label className="form-label small fw-bold">내용</label>
            <textarea className="form-control" rows={10} value={content} onChange={e => setContent(e.target.value)} placeholder="내용" />
          </div>
          <button type="submit" className="btn btn-success w-100" disabled={sending || !title.trim() || !content.trim()}>
            {sending ? '등록 중...' : '등록'}
          </button>
        </form>
      )}

      {tab === 'list' && (
        <>
          {loading && <Loading />}
          {error && <ErrorMessage message={error} onRetry={load} />}
          {!loading && !error && (
            <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
              <div className="table-responsive">
                <table className="table table-hover align-middle mb-0 small">
                  <thead className="table-light">
                    <tr><th>#</th><th>제목</th><th>작성자</th><th>상태</th><th>관리</th></tr>
                  </thead>
                  <tbody>
                    {posts.map(p => (
                      <tr key={p.id}>
                        <td>{p.id}</td>
                        <td>
                          <span className="text-decoration-none" style={{ cursor: 'pointer' }}
                            onClick={() => navigate(`/legal/issues/${p.id}`)}>
                            {p.title}
                          </span>
                        </td>
                        <td>{p.author_name || '익명'}</td>
                        <td>
                          {p.labor_approved
                            ? <span className="badge bg-success">게시</span>
                            : <span className="badge bg-secondary">미게시</span>}
                        </td>
                        <td>
                          <button className="btn btn-sm btn-outline-primary py-0"
                            onClick={() => handleToggle(p.id)}>
                            {p.labor_approved ? '미게시로' : '게시로'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {posts.length === 0 && <div className="text-center py-4 text-muted">등록된 게시글이 없습니다.</div>}
            </div>
          )}
        </>
      )}
    </div>
  )
}
