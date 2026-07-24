import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'
import EmptyState from '../components/common/EmptyState'

interface FriendData {
  friends: { id: number; name: string; town: string; village: string }[]
  requests: { id: number; name: string }[]
}

export default function FriendsList() {
  const navigate = useNavigate()
  const [data, setData] = useState<FriendData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res = await fetch('/friends/list').then(r => r.json())
      setData(res)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const handleAction = async (url: string, confirmMsg?: string) => {
    if (confirmMsg && !confirm(confirmMsg)) return
    try {
      const res = await fetch(url, { method: 'POST' }).then(r => r.json())
      if (res.status === 'success') load()
      else alert(res.msg || '오류')
    } catch { alert('오류가 발생했습니다.') }
  }

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h3 className="fw-bold text-success mb-0">내 벗 관리</h3>
        <button className="btn btn-sm btn-outline-primary" onClick={() => navigate('/friends/map')}>벗 위치 지도</button>
      </div>

      {data?.requests && data.requests.length > 0 && (
        <div className="card border-0 shadow-sm mb-4 border-start border-4 border-warning" style={{ borderRadius: 18 }}>
          <div className="card-body p-4">
            <h5 className="fw-bold mb-3 text-warning">벗 신청 대기 ({data.requests.length})</h5>
            {data.requests.map(r => (
              <div key={r.id} className="d-flex justify-content-between align-items-center p-2 bg-light rounded mb-2">
                <span className="fw-bold">{r.name}</span>
                <div className="d-flex gap-1">
                  <button className="btn btn-sm btn-success" onClick={() => handleAction(`/friends/accept/${r.id}`)}>수락</button>
                  <button className="btn btn-sm btn-outline-danger" onClick={() => handleAction(`/friends/reject/${r.id}`, '거절하시겠습니까?')}>거절</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 18 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold mb-3">내 벗 ({data?.friends.length || 0}명)</h5>
          {data?.friends && data.friends.length > 0 ? (
            <div className="list-group list-group-flush">
              {data.friends.map(f => (
                <div key={f.id} className="list-group-item d-flex justify-content-between align-items-center px-0">
                  <span className="fw-bold">{f.name}</span>
                  <button className="btn btn-sm btn-outline-danger"
                    onClick={() => handleAction(`/friends/remove/${f.id}`, '벗 관계를 삭제하시겠습니까?')}>✕ 삭제</button>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState icon="👥" title="아직 벗이 없습니다." />
          )}
        </div>
      </div>

      <div className="card border-0 shadow-sm" style={{ borderRadius: 18 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold mb-3">그룹</h5>
          <p className="text-muted small">그룹 기능은 곧 추가됩니다.</p>
        </div>
      </div>
    </div>
  )
}
