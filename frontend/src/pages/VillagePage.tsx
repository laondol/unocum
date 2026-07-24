import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { villageApi } from '../lib/api'
import type { VillageAlert, VillageEvent } from '../lib/types'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

export default function VillagePage() {
  const navigate = useNavigate()
  const [alerts, setAlerts] = useState<VillageAlert[]>([])
  const [events, setEvents] = useState<VillageEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [a, e] = await Promise.all([
        villageApi.alerts().catch(() => []),
        villageApi.events().catch(() => []),
      ])
      setAlerts(Array.isArray(a) ? a : [])
      setEvents(Array.isArray(e) ? e : [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h4 className="fw-bold mb-3">마을 페이지</h4>
          <p className="text-muted small">마을 활동, 알림, 일정을 확인하세요.</p>
          <div className="d-flex gap-2 flex-wrap">
            <button className="btn btn-sm btn-outline-success" onClick={() => navigate('/village/events')}>활동 보기</button>
            <button className="btn btn-sm btn-outline-primary" onClick={() => navigate('/village/my-wishes')}>내 바람</button>
          </div>
        </div>
      </div>

      {alerts.length > 0 && (
        <div className="mb-4">
          <h5 className="fw-bold mb-3">알림</h5>
          {alerts.map(a => (
            <div key={a.id} className={`card border-0 shadow-sm mb-2 ${a.urgency === 'high' ? 'border-start border-danger border-4' : ''}`} style={{ borderRadius: 12 }}>
              <div className="card-body p-3">
                <div className="d-flex justify-content-between">
                  <strong>{a.title}</strong>
                  <small className="text-muted">{a.created_at ? new Date(a.created_at).toLocaleDateString('ko-KR') : ''}</small>
                </div>
                {a.content && <p className="small text-muted mt-1 mb-0">{a.content}</p>}
              </div>
            </div>
          ))}
        </div>
      )}

      {events.length > 0 && (
        <div>
          <h5 className="fw-bold mb-3">최근 활동</h5>
          {events.slice(0, 5).map(e => (
            <div key={e.id} className="card border-0 shadow-sm mb-2" style={{ borderRadius: 12, cursor: 'pointer' }}
              onClick={() => navigate(`/village/events/${e.id}`)}>
              <div className="card-body p-3">
                <div className="d-flex justify-content-between">
                  <div>
                    <span className={`badge ${e.event_type === 'meeting' ? 'bg-info' : 'bg-warning'} me-1`}>
                      {e.event_type === 'meeting' ? '회의' : '행사'}
                    </span>
                    <strong>{e.title}</strong>
                  </div>
                  <small className="text-muted">{e.event_date ? new Date(e.event_date).toLocaleString('ko-KR') : ''}</small>
                </div>
                <div className="small text-muted mt-1">📍 {e.location || '미정'}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
