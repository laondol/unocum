import { useState, useEffect, useCallback } from 'react'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'
import EmptyState from '../components/common/EmptyState'

interface Recommendation {
  id: number
  news_id: number
  title: string
  url: string
  description?: string
  author_name?: string
  created_at?: string
}

export default function AdminNewsRecommendations() {
  const [recs, setRecs] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res = await fetch('/api/news/recommendations/pending')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setRecs(Array.isArray(data) ? data : [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const handleApprove = async (id: number) => {
    try {
      const res = await fetch(`/admin/news/recommendation/approve/${id}`)
      if (res.ok) {
        setRecs(prev => prev.filter(r => r.id !== id))
      } else {
        alert('승인 처리 실패')
      }
    } catch { alert('오류가 발생했습니다.') }
  }

  const handleReject = async (id: number) => {
    if (!confirm('이 추천링크를 반려하시겠습니까?')) return
    try {
      const res = await fetch(`/admin/news/recommendation/reject/${id}`)
      if (res.ok) {
        setRecs(prev => prev.filter(r => r.id !== id))
      } else {
        alert('반려 처리 실패')
      }
    } catch { alert('오류가 발생했습니다.') }
  }

  return (
    <div className="px-0 px-md-2">
      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold mb-4">📎 추천링크 승인 관리</h5>

          {loading ? (
            <Loading />
          ) : error ? (
            <ErrorMessage message={error} onRetry={load} />
          ) : recs.length === 0 ? (
            <EmptyState icon="📎" title="대기 중인 추천링크가 없습니다." />
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0" style={{ fontSize: '0.85rem' }}>
                <thead className="table-light">
                  <tr className="text-center small">
                    <th style={{ width: '5%' }}>ID</th>
                    <th style={{ width: '30%' }}>추천링크</th>
                    <th style={{ width: '10%' }}>추천인</th>
                    <th style={{ width: '25%' }}>설명</th>
                    <th style={{ width: '15%' }}>신청일</th>
                    <th style={{ width: '15%' }}>처리</th>
                  </tr>
                </thead>
                <tbody>
                  {recs.map(r => (
                    <tr key={r.id} className="text-center">
                      <td className="text-muted">{r.id}</td>
                      <td className="text-start ps-3">
                        <div className="fw-bold text-dark">
                          <a href={r.url} target="_blank" rel="noopener noreferrer">
                            {r.title.length > 40 ? r.title.slice(0, 40) + '...' : r.title}
                          </a>
                        </div>
                      </td>
                      <td>{r.author_name || '-'}</td>
                      <td className="text-start ps-2 small text-muted">
                        {r.description ? (r.description.length > 50 ? r.description.slice(0, 50) + '...' : r.description) : '-'}
                      </td>
                      <td className="small text-muted">
                        {r.created_at ? new Date(r.created_at).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-'}
                      </td>
                      <td>
                        <button className="btn btn-sm btn-success me-1" onClick={() => handleApprove(r.id)}>승인</button>
                        <button className="btn btn-sm btn-outline-danger" onClick={() => handleReject(r.id)}>반려</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
