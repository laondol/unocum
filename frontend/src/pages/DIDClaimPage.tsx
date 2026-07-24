import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'

export default function DIDClaimPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState<'checking' | 'success' | 'error'>('checking')

  useEffect(() => {
    const sessionId = searchParams.get('session')
    if (!sessionId) { setStatus('error'); return }
    fetch('/api/did/qr-session/claim', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessionId }),
    }).then(r => r.json()).then(d => {
      if (d.success) { setStatus('success'); setTimeout(() => navigate('/my/did'), 2000) }
      else setStatus('error')
    }).catch(() => setStatus('error'))
  }, [])

  return (
    <div className="text-center py-5" style={{ maxWidth: 400, margin: '0 auto' }}>
      {status === 'checking' && <div>🔄 QR 세션 확인 중...</div>}
      {status === 'success' && <div className="alert alert-success">✅ VC 발급이 요청되었습니다! DID 페이지로 이동합니다.</div>}
      {status === 'error' && <div className="alert alert-danger">❌ 유효하지 않거나 만료된 QR입니다.</div>}
    </div>
  )
}
