import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import ErrorMessage from '../components/common/ErrorMessage'

export default function LegalIssueWritePage() {
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()
  const [tab, setTab] = useState<'direct' | 'url' | 'ai'>('direct')
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [url, setUrl] = useState('')
  const [keyword, setKeyword] = useState('')
  const [sending, setSending] = useState(false)
  const [summarizing, setSummarizing] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!authLoading && (!user || (user.role !== 'admin' && user.role !== 'leader'))) {
      navigate('/legal/issues')
    }
  }, [user, authLoading, navigate])

  const handleSummarize = async () => {
    if (!url.trim()) return
    setSummarizing(true)
    try {
      const res = await fetch('/api/news/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      })
      const data = await res.json()
      if (data.status === 'success') {
        if (data.title) setTitle(data.title)
        if (data.summary) setContent(data.summary)
      } else {
        alert(data.msg || '요약 실패')
      }
    } catch { alert('URL 요약 중 오류') }
    finally { setSummarizing(false) }
  }

  const handleAiWrite = async () => {
    if (!keyword.trim()) return
    setSending(true)
    try {
      const fd = new FormData()
      fd.append('keyword', keyword.trim())
      fd.append('title', title.trim() || keyword.trim())
      const res = await fetch('/api/legal/issues/write', { method: 'POST', body: fd })
      const data = await res.json()
      if (data.id || data.status === 'success') {
        navigate('/legal/issues')
      } else {
        alert(data.msg || 'AI 작성 실패')
      }
    } catch { alert('AI 작성 중 오류') }
    finally { setSending(false) }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !content.trim()) return
    setSending(true); setError('')
    try {
      const fd = new FormData()
      fd.append('title', title.trim())
      fd.append('content', content.trim())
      const res = await fetch('/api/legal/issues/write', { method: 'POST', body: fd })
      const data = await res.json()
      if (data.id || data.status === 'success') {
        navigate('/legal/issues')
      } else {
        setError(data.msg || '등록 실패')
      }
    } catch { setError('등록 중 오류가 발생했습니다.') }
    finally { setSending(false) }
  }

  if (authLoading) return null

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <h4 className="fw-bold mb-3">노동 게시글 작성</h4>

      <ul className="nav nav-tabs mb-4">
        <li className="nav-item">
          <button className={`nav-link ${tab === 'direct' ? 'active' : ''}`} onClick={() => setTab('direct')}>
            직접작성
          </button>
        </li>
        <li className="nav-item">
          <button className={`nav-link ${tab === 'url' ? 'active' : ''}`} onClick={() => setTab('url')}>
            URL 요약
          </button>
        </li>
        <li className="nav-item">
          <button className={`nav-link ${tab === 'ai' ? 'active' : ''}`} onClick={() => setTab('ai')}>
            AI 작성
          </button>
        </li>
      </ul>

      {error && <ErrorMessage message={error} />}

      {tab === 'direct' && (
        <form onSubmit={handleSubmit} className="card border-0 shadow-sm p-4" style={{ borderRadius: 16 }}>
          <div className="mb-3">
            <label className="form-label small fw-bold">제목</label>
            <input className="form-control" value={title} onChange={e => setTitle(e.target.value)} placeholder="제목을 입력하세요" />
          </div>
          <div className="mb-3">
            <label className="form-label small fw-bold">내용</label>
            <textarea className="form-control" rows={10} value={content} onChange={e => setContent(e.target.value)} placeholder="내용을 입력하세요" />
          </div>
          <button type="submit" className="btn btn-success w-100" disabled={sending || !title.trim() || !content.trim()}>
            {sending ? '등록 중...' : '등록'}
          </button>
        </form>
      )}

      {tab === 'url' && (
        <div className="card border-0 shadow-sm p-4" style={{ borderRadius: 16 }}>
          <div className="mb-3">
            <label className="form-label small fw-bold">URL</label>
            <div className="d-flex gap-2">
              <input className="form-control" value={url} onChange={e => setUrl(e.target.value)} placeholder="요약할 URL을 입력하세요" />
              <button className="btn btn-info" onClick={handleSummarize} disabled={summarizing || !url.trim()}>
                {summarizing ? '요약 중...' : '요약'}
              </button>
            </div>
          </div>
          <div className="mb-3">
            <label className="form-label small fw-bold">제목</label>
            <input className="form-control" value={title} onChange={e => setTitle(e.target.value)} />
          </div>
          <div className="mb-3">
            <label className="form-label small fw-bold">내용</label>
            <textarea className="form-control" rows={10} value={content} onChange={e => setContent(e.target.value)} />
          </div>
          <button className="btn btn-success w-100" onClick={handleSubmit} disabled={sending || !title.trim() || !content.trim()}>
            {sending ? '등록 중...' : '등록'}
          </button>
        </div>
      )}

      {tab === 'ai' && (
        <div className="card border-0 shadow-sm p-4" style={{ borderRadius: 16 }}>
          <div className="mb-3">
            <label className="form-label small fw-bold">키워드</label>
            <input className="form-control" value={keyword} onChange={e => setKeyword(e.target.value)} placeholder="키워드를 입력하세요" />
          </div>
          <div className="mb-3">
            <label className="form-label small fw-bold">제목 (선택)</label>
            <input className="form-control" value={title} onChange={e => setTitle(e.target.value)} placeholder="비워두면 키워드가 제목으로 사용됩니다" />
          </div>
          <button className="btn btn-success w-100" onClick={handleAiWrite} disabled={sending || !keyword.trim()}>
            {sending ? 'AI 작성 중...' : 'AI로 작성'}
          </button>
        </div>
      )}

      <button className="btn btn-sm btn-outline-secondary mt-3" onClick={() => navigate('/legal/issues')}>
        ← 목록으로
      </button>
    </div>
  )
}
