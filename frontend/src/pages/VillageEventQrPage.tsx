import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { villageApi } from '../lib/api'
import type { VillageEvent } from '../lib/types'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

export default function VillageEventQrPage() {
  const { eventId } = useParams<{ eventId: string }>()
  const navigate = useNavigate()
  const qrRef = useRef<HTMLDivElement>(null)
  const [event, setEvent] = useState<VillageEvent | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [qrError, setQrError] = useState('')

  useEffect(() => {
    if (!eventId) return
    setLoading(true); setError('')
    villageApi.events()
      .then(events => {
        const found = (Array.isArray(events) ? events : []).find((e: VillageEvent) => e.id === Number(eventId))
        if (found) setEvent(found)
        else setError('이벤트를 찾을 수 없습니다.')
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '불러오기 실패'))
      .finally(() => setLoading(false))
  }, [eventId])

  useEffect(() => {
    if (!event) return

    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js'
    script.async = true
    script.onload = () => {
      const container = qrRef.current
      if (!container) return
      container.innerHTML = ''
      const url = `${window.location.origin}/village/events/${event.id}`
      const win = window as any
      if (typeof win.QRCode === 'function') {
        new win.QRCode(container, {
          text: url,
          width: 256,
          height: 256,
          colorDark: '#198754',
          colorLight: '#ffffff',
          correctLevel: 3,
        })
      } else {
        setQrError('QRCode 라이브러리 로드 실패')
      }
    }
    script.onerror = () => setQrError('QRCode 라이브러리 로드 실패')
    document.head.appendChild(script)
    return () => { document.head.removeChild(script) }
  }, [event])

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} />

  return (
    <div style={{ maxWidth: 500, margin: '0 auto' }}>
      <div className="card border-0 shadow-sm p-4 text-center" style={{ borderRadius: 16 }}>
        <h4 className="fw-bold mb-3">출석 QR</h4>

        {event && (
          <div className="mb-3">
            <span className={`badge ${event.event_type === 'meeting' ? 'bg-info' : 'bg-warning'} mb-2`}>
              {event.event_type === 'meeting' ? '모임' : '활동'}
            </span>
            <h5>{event.title}</h5>
            <p className="small text-muted mb-1">
              {event.event_date ? new Date(event.event_date).toLocaleString('ko-KR') : ''}
            </p>
            <p className="small text-muted">📍 {event.location || '미정'}</p>
          </div>
        )}

        <div className="d-flex justify-content-center mb-3" ref={qrRef} style={{ minHeight: 256 }}>
          {qrError && <ErrorMessage message={qrError} />}
        </div>

        <p className="small text-muted">이 QR을 스캔하면 이벤트 페이지로 이동합니다.</p>

        <button className="btn btn-sm btn-outline-secondary" onClick={() => navigate(`/village/events/${eventId}`)}>
          ← 이벤트 상세
        </button>
      </div>
    </div>
  )
}
