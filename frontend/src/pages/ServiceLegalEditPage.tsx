import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function ServiceLegalEditPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [content, setContent] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  if (user?.role !== 'admin' && user?.role !== 'leader') {
    return (
      <div className="alert alert-danger text-center py-4">
        <div className="fs-3 mb-2">⚠️</div>
        <p>관리자만 접근할 수 있습니다.</p>
        <button className="btn btn-sm btn-outline-danger" onClick={() => navigate('/service/legal')}>돌아가기</button>
      </div>
    )
  }

  const handleSave = async () => {
    setError(''); setMessage(''); setLoading(true)
    try {
      const res = await fetch('/service/legal/edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.error || data.msg || '저장 실패'); return }
      setMessage('저장되었습니다.')
    } catch { setError('서버 연결 실패') }
    finally { setLoading(false) }
  }

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <h4 className="fw-bold mb-3" style={{ color: '#198754' }}>법률상담소 페이지 편집</h4>

      {error && <div className="alert alert-danger py-2 small">{error}</div>}
      {message && <div className="alert alert-success py-2 small">{message}</div>}

      <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <label className="form-label small fw-bold">페이지 내용</label>
          <textarea
            className="form-control font-monospace"
            rows={16}
            value={content}
            onChange={e => setContent(e.target.value)}
            placeholder="HTML 형식으로 내용을 입력하세요."
          />
        </div>
      </div>

      <div className="d-flex gap-2">
        <button className="btn btn-success px-4 py-2 fw-bold" onClick={handleSave} disabled={loading}>
          {loading ? '저장 중...' : '저장'}
        </button>
        <button className="btn btn-outline-secondary px-4 py-2" onClick={() => navigate('/service/legal')}>미리보기</button>
      </div>
    </div>
  )
}
