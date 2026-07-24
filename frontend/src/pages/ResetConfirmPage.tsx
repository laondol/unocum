import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

export default function ResetConfirmPage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!token) setError('유효하지 않은 링크입니다. 토큰이 누락되었습니다.')
  }, [token])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) { setError('토큰이 유효하지 않습니다.'); return }
    if (password.length < 8) { setError('비밀번호는 8자 이상이어야 합니다.'); return }
    if (password !== confirm) { setError('비밀번호가 일치하지 않습니다.'); return }
    setError(''); setMessage(''); setLoading(true)
    try {
      const res = await fetch('/reset-password/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, password }),
      })
      const data = await res.json()
      if (!res.ok) {
        if (res.status === 400 && (data.msg || '').includes('expired')) {
          setError('링크가 만료되었습니다. 다시 비밀번호 찾기를 시도해주세요.')
        } else {
          setError(data.error || data.msg || '비밀번호 재설정 실패')
        }
        return
      }
      setMessage('비밀번호가 성공적으로 변경되었습니다. 로그인 페이지로 이동합니다.')
      setTimeout(() => navigate('/login'), 1500)
    } catch { setError('서버 연결 실패') }
    finally { setLoading(false) }
  }

  return (
    <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '70vh' }}>
      <div className="card border-0 shadow-sm" style={{ maxWidth: 420, width: '100%', borderRadius: 16 }}>
        <div className="card-body p-4">
          <h4 className="fw-bold text-center mb-1" style={{ color: '#198754' }}>새 비밀번호 설정</h4>
          <p className="text-muted text-center small mb-4">새로운 비밀번호를 입력해주세요.</p>

          {error && <div className="alert alert-danger py-2 small">{error}</div>}
          {message && <div className="alert alert-success py-2 small">{message}</div>}

          {!message && (
            <form onSubmit={handleSubmit}>
              <div className="mb-3">
                <label className="form-label small fw-bold">새 비밀번호</label>
                <input type="password" className="form-control" value={password} onChange={e => setPassword(e.target.value)} placeholder="8자 이상" minLength={8} required autoFocus />
              </div>
              <div className="mb-3">
                <label className="form-label small fw-bold">비밀번호 확인</label>
                <input type="password" className="form-control" value={confirm} onChange={e => setConfirm(e.target.value)} placeholder="다시 입력" required />
              </div>
              <button type="submit" className="btn btn-success w-100 py-2 fw-bold" disabled={loading}>
                {loading ? '처리 중...' : '비밀번호 변경'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
