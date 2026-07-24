import { useState, useEffect } from 'react'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'
import EmptyState from '../components/common/EmptyState'

interface ShareReport {
  id: number
  title: string
  description: string
  author_name: string
  town: string
  village: string
  status: 'pending' | 'approved' | 'rejected'
  ai_danger_alert: boolean
  image_path: string | null
  drawing_path: string | null
  video_path: string | null
  ai_category: string
  ai_summary: string
  is_moderated: boolean
  moderation_result: string | null
  created_at: string
  updated_at: string
}

const statusBadge = (s: ShareReport['status']) => {
  if (s === 'pending') return <span className="badge bg-warning text-dark">승인대기</span>
  if (s === 'approved') return <span className="badge bg-success">승인완료</span>
  return <span className="badge bg-danger">반려</span>
}

const truncate = (text: string, max: number) =>
  text.length > max ? text.slice(0, max) + '…' : text

export default function AdminShareReports() {
  const [reports, setReports] = useState<ShareReport[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/admin/share-reports')
      if (!res.ok) throw new Error('불러오기 실패')
      const data = await res.json()
      setReports(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  if (loading) return (
    <div className="px-0 px-md-2">
      <Loading />
    </div>
  )

  if (error) return (
    <div className="px-0 px-md-2">
      <ErrorMessage message={error} onRetry={load} />
    </div>
  )

  return (
    <div className="px-0 px-md-2">
      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold mb-4">📍 공유마당 관리</h5>

          {reports.length === 0 ? (
            <EmptyState icon="📍" title="등록된 공유글이 없습니다" />
          ) : (
            <div className="row g-3">
              {reports.map(r => (
                <div key={r.id} className="col-12 col-lg-6">
                  <div className="card h-100 border-0 shadow-xs" style={{ borderRadius: 12, background: '#fafafa' }}>
                    <div className="card-body p-3">
                      <div className="d-flex justify-content-between align-items-start mb-2">
                        <h6 className="fw-bold mb-0">{r.title}</h6>
                        <div className="d-flex gap-1 flex-shrink-0">
                          {statusBadge(r.status)}
                          {r.ai_danger_alert && <span className="badge bg-danger">⚠️</span>}
                        </div>
                      </div>

                      <p className="text-muted small mb-2">{truncate(r.description, 80)}</p>

                      <div className="d-flex flex-wrap gap-2 mb-2">
                        <span className="small text-secondary">👤 {r.author_name}</span>
                        <span className="small text-secondary">📍 {r.village || r.town || '-'}</span>
                        {r.video_path && <span className="badge bg-info text-dark">🎬 동영상</span>}
                      </div>

                      {(r.image_path || r.drawing_path) && (
                        <div className="d-flex gap-2 mb-2">
                          {r.image_path && (
                            <img
                              src={r.image_path}
                              alt=""
                              style={{ width: 80, height: 60, objectFit: 'cover', borderRadius: 8 }}
                            />
                          )}
                          {r.drawing_path && (
                            <img
                              src={r.drawing_path}
                              alt=""
                              style={{ width: 80, height: 60, objectFit: 'cover', borderRadius: 8 }}
                            />
                          )}
                        </div>
                      )}

                      {r.ai_category && (
                        <div className="mb-1">
                          <span className="badge bg-light text-dark me-1">🏷️ {r.ai_category}</span>
                        </div>
                      )}

                      {r.ai_summary && (
                        <p className="small text-muted mb-2">{truncate(r.ai_summary, 100)}</p>
                      )}

                      <div className="d-flex justify-content-between align-items-center border-top pt-2 mt-1">
                        <span
                          className="small"
                          title={r.moderation_result ? `검토 결과: ${r.moderation_result}` : undefined}
                          style={{ cursor: r.moderation_result ? 'help' : undefined }}
                        >
                          {r.is_moderated ? '✅ 검토완료' : '⏳ 검토대기'}
                        </span>
                        <span className="small text-muted">
                          {new Date(r.created_at).toLocaleDateString('ko-KR')}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
