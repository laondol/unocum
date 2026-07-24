import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

const COUNTDOWN = 600

const pages = [
  { label: '마을 메인', path: '/village' },
  { label: '활동 목록', path: '/village/events' },
  { label: '마을 관리', path: '/village/admin' },
  { label: '내 바람', path: '/village/my-wishes' },
]

export default function VillageQrPage() {
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const qrRef = useRef<HTMLDivElement>(null)
  const [selectedPage, setSelectedPage] = useState(pages[0].path)
  const [qrLoaded, setQrLoaded] = useState(false)
  const [qrError, setQrError] = useState('')
  const [countdown, setCountdown] = useState(COUNTDOWN)

  const managed = user?.managed_pages ?? []
  const hasAccess = managed.some(p => p.startsWith('village') || p.startsWith('vi_'))

  const baseUrl = window.location.origin

  const generateQr = () => {
    setQrLoaded(false)
    setQrError('')
    const url = `${baseUrl}${selectedPage}`
    const container = qrRef.current
    if (!container) return
    container.innerHTML = ''
    const win = window as any
    if (typeof win.QRCode === 'function') {
      try {
        new win.QRCode(container, {
          text: url,
          width: 256,
          height: 256,
          colorDark: '#198754',
          colorLight: '#ffffff',
          correctLevel: win.QRCode.CorrectLevel?.H || 3,
        })
        setQrLoaded(true)
      } catch {
        setQrError('QR 코드 생성 실패')
      }
    } else {
      setQrError('QRCode 라이브러리를 불러올 수 없습니다.')
    }
  }

  useEffect(() => {
    if (authLoading || !hasAccess) return
    setCountdown(COUNTDOWN)
    generateQr()
    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          generateQr()
          return COUNTDOWN
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [selectedPage, authLoading])

  useEffect(() => {
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js'
    script.async = true
    script.onload = () => {
      if (qrRef.current) generateQr()
    }
    script.onerror = () => setQrError('QRCode 라이브러리 로드 실패')
    document.head.appendChild(script)
    return () => {
      document.head.removeChild(script)
    }
  }, [])

  const minutes = Math.floor(countdown / 60)
  const seconds = countdown % 60

  if (authLoading) return <Loading />
  if (!hasAccess) return <ErrorMessage message="접근 권한이 없습니다." />

  return (
    <div style={{ maxWidth: 500, margin: '0 auto' }}>
      <div className="card border-0 shadow-sm p-4 text-center" style={{ borderRadius: 16 }}>
        <h4 className="fw-bold mb-3">QR 초대</h4>

        <div className="mb-3">
          <label className="small fw-bold mb-1">페이지 선택</label>
          <select className="form-select" value={selectedPage} onChange={e => { setSelectedPage(e.target.value); setCountdown(COUNTDOWN) }}>
            {pages.map(p => <option key={p.path} value={p.path}>{p.label}</option>)}
          </select>
        </div>

        <div className="mb-3 d-flex justify-content-center" ref={qrRef} style={{ minHeight: 256 }}>
          {qrError && <ErrorMessage message={qrError} />}
        </div>

        {qrLoaded && (
          <div className="mb-2">
            <span className={`badge fs-6 ${countdown < 60 ? 'bg-danger' : 'bg-success'}`}>
              {minutes}:{seconds.toString().padStart(2, '0')}
            </span>
            <p className="small text-muted mt-1">QR 코드는 10분마다 자동 갱신됩니다.</p>
          </div>
        )}

        <button className="btn btn-sm btn-outline-success me-2" onClick={() => { setCountdown(COUNTDOWN); generateQr() }}>
          새로고침
        </button>
        <button className="btn btn-sm btn-outline-secondary" onClick={() => navigate('/village/admin')}>
          ← 관리자
        </button>
      </div>
    </div>
  )
}
