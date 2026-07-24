import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { villageApi } from '../lib/api'
import type { VillageEvent } from '../lib/types'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

export default function VillageEventDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [event, setEvent] = useState<VillageEvent | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true); setError('')
    try {
      const events = await villageApi.events()
      const found = (Array.isArray(events) ? events : []).find((e: VillageEvent) => e.id === Number(id))
      if (found) setEvent(found)
      else setError('이벤트를 찾을 수 없습니다.')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [id])

  useEffect(() => { load() }, [load])

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />
  if (!event) return <ErrorMessage message="이벤트를 찾을 수 없습니다." />

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <div className="d-flex justify-content-between align-items-start">
            <div>
              <span className={`badge ${event.event_type === 'meeting' ? 'bg-info' : 'bg-warning'} mb-2`}>
                {event.event_type === 'meeting' ? '회의' : '행사'}
              </span>
              <h4 className="fw-bold">{event.title}</h4>
            </div>
            <div className="text-end small text-muted">
              <div>{event.event_date ? new Date(event.event_date).toLocaleString('ko-KR') : ''}</div>
              <div>📍 {event.location || '미정'}</div>
            </div>
          </div>
          <p className="mt-2">{event.description || ''}</p>
        </div>
      </div>

      <div className="text-center mt-3">
        <button className="btn btn-sm btn-outline-secondary" onClick={() => navigate('/village/events')}>← 목록</button>
      </div>
    </div>
  )
}
