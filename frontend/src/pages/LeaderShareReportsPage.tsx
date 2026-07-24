import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
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
  latitude: number
  longitude: number
  image_path: string | null
  drawing_path: string | null
  ai_category: string
  ai_confidence: number
  ai_danger_alert: boolean
  status: 'pending' | 'approved' | 'rejected'
  created_at: string
}

const statusBadge = (s: ShareReport['status']) => {
  if (s === 'pending') return <span className="badge bg-warning text-dark">승인대기</span>
  if (s === 'approved') return <span className="badge bg-success">승인완료</span>
  return <span className="badge bg-danger">반려</span>
}

export default function LeaderShareReportsPage() {
  const { user, loading: authLoading } = useAuth()
  const [reports, setReports] = useState<ShareReport[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [toggling, setToggling] = useState<number | null>(null)

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

  useEffect(() => { if (!authLoading) load() }, [authLoading])

  const toggleStatus = async (id: number, action: 'approve' | 'reject') => {
    setToggling(id)
    try {
      const res = await fetch(`/share-report/toggle/${id}/${action}`).then(r => r.json())
      if (res.status === 'success' || res.success) {
        setReports(prev => prev.map(r =>
          r.id === id ? { ...r, status: action === 'approve' ? 'approved' : 'rejected' as ShareReport['status'] } : r
        ))
      } else {
        alert(res.error || res.msg || '처리 실패')
      }
    } catch {
      alert('처리 실패')
    } finally {
      setToggling(null)
    }
  }

  if (authLoading || loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />
  if (!user || (user.role !== 'admin' && user.role !== 'leader')) {
    return <ErrorMessage message="접근 권한이 없습니다." />
  }

  return (
    <div className="container mt-4">
      <h4 className="fw-bold mb-4">📋 공유마당 관리</h4>
      {reports.length === 0 ? (
        <EmptyState icon="📋" title="등록된 공유글이 없습니다" />
      ) : (
        <div className="table-responsive">
          <table className="table table-hover align-middle">
            <thead className="table-light">
              <tr>
                <th>ID</th>
                <th>제목/내용</th>
                <th>공유자</th>
                <th>위치</th>
                <th>사진</th>
                <th>그림</th>
                <th>AI분류</th>
                <th>신뢰도</th>
                <th>위험</th>
                <th>상태</th>
                <th>일시</th>
                <th>처리</th>
              </tr>
            </thead>
            <tbody>
              {reports.map(r => (
                <tr key={r.id} style={r.ai_danger_alert ? { backgroundColor: '#ffeef0' } : undefined}>
                  <td className="small">{r.id}</td>
                  <td>
                    <strong className="small">{r.title}</strong>
                    {r.description && <div className="text-muted small">{r.description.substring(0, 60)}</div>}
                  </td>
                  <td className="small">{r.author_name}</td>
                  <td className="small">
                    {r.latitude && r.longitude
                      ? `${r.latitude.toFixed(4)}, ${r.longitude.toFixed(4)}`
                      : '-'}
                    <div className="text-muted">{r.village || r.town || '-'}</div>
                  </td>
                  <td>
                    {r.image_path ? (
                      <img src={r.image_path} alt="" style={{ width: 60, height: 45, objectFit: 'cover', borderRadius: 6 }} />
                    ) : <span className="text-muted small">-</span>}
                  </td>
                  <td>
                    {r.drawing_path ? (
                      <img src={r.drawing_path} alt="" style={{ width: 60, height: 45, objectFit: 'cover', borderRadius: 6 }} />
                    ) : <span className="text-muted small">-</span>}
                  </td>
                  <td>{r.ai_category && <span className="badge bg-light text-dark border">{r.ai_category}</span>}</td>
                  <td className="small">{r.ai_confidence ? `${(r.ai_confidence * 100).toFixed(0)}%` : '-'}</td>
                  <td>{r.ai_danger_alert ? <span className="badge bg-danger">⚠️ 위험</span> : <span className="text-muted small">-</span>}</td>
                  <td>{statusBadge(r.status)}</td>
                  <td className="small">{new Date(r.created_at).toLocaleDateString('ko-KR')}</td>
                  <td>
                    <div className="d-flex gap-1">
                      <button
                        className="btn btn-sm btn-outline-success"
                        disabled={r.status === 'approved' || toggling === r.id}
                        onClick={() => toggleStatus(r.id, 'approve')}
                      >
                        승인
                      </button>
                      <button
                        className="btn btn-sm btn-outline-danger"
                        disabled={r.status === 'rejected' || toggling === r.id}
                        onClick={() => toggleStatus(r.id, 'reject')}
                      >
                        반려
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
