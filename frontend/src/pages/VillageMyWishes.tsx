import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { villageApi } from '../lib/api'
import type { VillageWish } from '../lib/types'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'
import EmptyState from '../components/common/EmptyState'

export default function VillageMyWishes() {
  const navigate = useNavigate()
  const [wishes, setWishes] = useState<VillageWish[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const data = await villageApi.wishes()
      setWishes(Array.isArray(data) ? data : [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <h4 className="fw-bold mb-3">내가 보낸 마을 바람</h4>
      {wishes.length === 0 ? (
        <EmptyState icon="💭" title="아직 보낸 바람이 없습니다." />
      ) : (
        wishes.map(w => (
          <div key={w.id} className="card border-0 shadow-sm mb-2" style={{ borderRadius: 12, borderLeft: '4px solid #fd7e14' }}>
            <div className="card-body p-3">
              <div className="d-flex justify-content-between">
                <span className={`badge ${w.status === 'done' ? 'bg-success' : w.status === 'in_progress' ? 'bg-info' : w.status === 'rejected' ? 'bg-danger' : 'bg-secondary'}`}>
                  {{ pending: '대기중', in_progress: '진행중', done: '완료', rejected: '기각' }[w.status as string] || w.status}
                </span>
                <small className="text-muted">{w.created_at ? new Date(w.created_at).toLocaleString('ko-KR') : ''}</small>
              </div>
              <div className="mt-1">{w.content?.slice(0, 200)}</div>
              {w.reply && (
                <div className="mt-2 p-2 bg-light rounded small">
                  <strong>마을지기 답변:</strong> {w.reply}
                </div>
              )}
            </div>
          </div>
        ))
      )}
      <div className="text-center mt-3">
        <button className="btn btn-sm btn-outline-secondary" onClick={() => navigate('/village')}>← 마을 페이지</button>
      </div>
    </div>
  )
}
