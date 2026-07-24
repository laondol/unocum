import { useState } from 'react'
import { Link } from 'react-router-dom'

export default function ResetPasswordPage() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [debugUrl, setDebugUrl] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) { setError('이메일을 입력해주세요.'); return }
    setError(''); setMessage(''); setLoading(true); setDebugUrl('')
    try {
      const res = await fetch('/reset-password/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.error || data.msg || '전송 실패'); return }
      setMessage(data.msg || '재설정 링크가 이메일로 전송되었습니다.')
      if (data.debug_url) setDebugUrl(data.debug_url)
    } catch { setError('서버 연결 실패') }
    finally { setLoading(false) }
  }

  return (
    <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '70vh' }}>
      <div className="card border-0 shadow-sm" style={{ maxWidth: 420, width: '100%', borderRadius: 16 }}>
        <div className="card-body p-4">
          <h4 className="fw-bold text-center mb-1" style={{ color: '#198754' }}>비밀번호 재설정</h4>
          <p className="text-muted text-center small mb-4">가입한 이메일을 입력하면 재설정 링크를 보내드립니다.</p>

          {error && <div className="alert alert-danger py-2 small">{error}</div>}
          {message && <div className="alert alert-success py-2 small">{message}</div>}
          {debugUrl && (
            <div className="alert alert-info py-2 small mb-3">
              <a href={debugUrl} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-outline-primary">
                🔗 직접 링크 열기
              </a>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label small fw-bold">이메일</label>
              <input
                type="email"
                className="form-control"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="가입한 이메일 주소"
                required
                autoFocus
              />
            </div>
            <button type="submit" className="btn btn-success w-100 py-2 fw-bold" disabled={loading}>
              {loading ? '전송 중...' : '재설정 링크 받기'}
            </button>
          </form>

          <div className="text-center mt-3">
            <Link to="/login" className="text-decoration-none text-muted small">← 로그인으로</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
