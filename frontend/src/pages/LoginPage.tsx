import { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function LoginPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { refresh } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
        credentials: 'include',
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.error || data.msg || '로그인 실패')
        return
      }
      await refresh()
      const next = searchParams.get('next') || '/intro'
      navigate(next)
    } catch {
      setError('서버 연결에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '70vh' }}>
      <div className="card border-0 shadow-sm" style={{ maxWidth: 420, width: '100%', borderRadius: 16 }}>
        <div className="card-body p-4">
          <h4 className="fw-bold text-center mb-1 text-success">함께사는양평 로그인</h4>
          <p className="text-muted text-center small mb-4">양평의 맑은 소통에 참여하세요.</p>

          {error && <div className="alert alert-danger text-center py-2 small">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <input type="text" className="form-control form-control-lg bg-light border-0"
                value={username} onChange={e => setUsername(e.target.value)}
                placeholder="이메일" required />
            </div>
            <div className="mb-4">
              <input type="password" className="form-control form-control-lg bg-light border-0"
                value={password} onChange={e => setPassword(e.target.value)}
                placeholder="비밀번호" required />
            </div>
            <button type="submit" className="btn btn-success w-100 py-3 fw-bold" disabled={loading}
              style={{ borderRadius: 12 }}>
              {loading ? '로그인 중...' : '로그인'}
            </button>
          </form>

          <div className="text-center mt-3">
            <Link to="/reset-password" className="text-muted small text-decoration-none d-block mb-1">비밀번호 찾기</Link>
            <span className="text-muted small">아직 회원이 아니신가요? </span>
            <Link to="/register" className="text-success fw-bold small text-decoration-none">회원 가입하기</Link>
            <div className="mt-1">
              <Link to="/terms" className="text-muted small text-decoration-none">회원약관 및 닢 규칙</Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
