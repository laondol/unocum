import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'

export default function GoPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const url = searchParams.get('url') || '/'
  const title = searchParams.get('title') || ''
  const back = searchParams.get('back') || '/'
  const [countdown, setCountdown] = useState(3)

  useEffect(() => {
    if (countdown <= 0) {
      window.open(url, '_blank')
      return
    }
    const timer = setTimeout(() => setCountdown(countdown - 1), 1000)
    return () => clearTimeout(timer)
  }, [countdown, url])

  const handleGo = () => {
    window.open(url, '_blank')
    setCountdown(0)
  }

  return (
    <div style={{ background: '#f8f9fa', display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
      <div className="card border-0 shadow" style={{ maxWidth: 420, width: '100%', borderRadius: 20 }}>
        <div className="card-body text-center p-4">
          <div className="fs-1 mb-3">🔗</div>
          <h5 className="fw-bold mb-2">외부 페이지로 이동합니다</h5>
          <p className="text-muted small mb-1">{title}</p>
          <p className="text-muted small mb-3" style={{ wordBreak: 'break-all' }}>
            {url.substring(0, 80)}{url.length > 80 ? '...' : ''}
          </p>
          <div className="d-grid gap-2">
            <button className="btn btn-primary" onClick={handleGo}>
              {countdown > 0 ? `이동하기 (${countdown}초)` : '이동 완료'}
            </button>
            <button className="btn btn-outline-secondary" onClick={() => navigate(back)}>
              ← 돌아가기
            </button>
          </div>
          <small className="text-muted d-block mt-3">열린 페이지를 닫으면 이전 화면으로 돌아옵니다.</small>
        </div>
      </div>
    </div>
  )
}
