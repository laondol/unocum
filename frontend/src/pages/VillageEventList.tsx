import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { villageApi } from '../lib/api'
import type { VillageEvent } from '../lib/types'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'
import EmptyState from '../components/common/EmptyState'

export default function VillageEventList() {
  const navigate = useNavigate()
  const [events, setEvents] = useState<VillageEvent[]>([])
  const [tab, setTab] = useState<'meeting' | 'activity'>('meeting')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const data = await villageApi.events()
      setEvents(Array.isArray(data) ? data : [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const filtered = events.filter(e => e.event_type === tab)

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h4 className="fw-bold mb-0">활동</h4>
        <button className="btn btn-sm btn-success" onClick={() => navigate('/village/events/create')}>+ 새로 만들기</button>
      </div>

      <ul className="nav nav-tabs mb-3">
        <li className="nav-item">
          <button className={`nav-link ${tab === 'meeting' ? 'active' : ''}`} onClick={() => setTab('meeting')}>회의</button>
        </li>
        <li className="nav-item">
          <button className={`nav-link ${tab === 'activity' ? 'active' : ''}`} onClick={() => setTab('activity')}>행사</button>
        </li>
      </ul>

      {filtered.length === 0 ? (
        <EmptyState icon="📋" title={`등록된 ${tab === 'meeting' ? '회의' : '행사'}이 없습니다.`} />
      ) : (
        filtered.map(e => (
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
              <div className="small text-muted mt-1">
                📍 {e.location || '미정'} | {{ upcoming: '예정', ongoing: '진행중', completed: '완료', afterparty: '뒤풀이' }[e.status as string] || ''}
              </div>
            </div>
          </div>
        ))
      )}

      <div className="text-center mt-3">
        <button className="btn btn-sm btn-outline-secondary" onClick={() => navigate('/village')}>← 마을지기</button>
      </div>
    </div>
  )
}
