import { useState, useEffect } from 'react'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'
import type { VillageAlert } from '../lib/types'

const ALERT_TYPE_OPTIONS = [
  { value: '', label: '전체 유형' },
  { value: 'info', label: '정보' },
  { value: 'warning', label: '경고' },
  { value: 'danger', label: '위험' },
  { value: 'emergency', label: '긴급' },
]

const ACTIVE_OPTIONS = [
  { value: '', label: '전체' },
  { value: '1', label: '활성' },
  { value: '0', label: '비활성' },
]

const ALERT_TYPE_LABELS: Record<string, string> = {
  info: '정보', warning: '경고', danger: '위험', emergency: '긴급',
}

const ALERT_TYPE_COLORS: Record<string, string> = {
  info: 'info', warning: 'warning', danger: 'danger', emergency: 'dark',
}

const URGENCY_COLORS: Record<string, string> = {
  low: 'secondary', medium: 'info', high: 'warning', urgent: 'danger',
}

export default function AdminAlerts() {
  const [alerts, setAlerts] = useState<VillageAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [alertTypeFilter, setAlertTypeFilter] = useState('')
  const [isActiveFilter, setIsActiveFilter] = useState('')

  const fetchAlerts = async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      if (alertTypeFilter) params.set('alert_type', alertTypeFilter)
      if (isActiveFilter) params.set('is_active', isActiveFilter)
      const qs = params.toString()
      const res = await fetch(`/api/admin/alerts${qs ? '?' + qs : ''}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setAlerts(Array.isArray(data) ? data : [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchAlerts() }, [alertTypeFilter, isActiveFilter])

  return (
    <div className="px-0 px-md-2">
      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold mb-4">🚨 알림 관리</h5>

            <div className="d-flex gap-3 mb-4">
              <select
                className="form-select form-select-sm"
                style={{ maxWidth: 160 }}
                value={alertTypeFilter}
                onChange={e => setAlertTypeFilter(e.target.value)}
              >
                {ALERT_TYPE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
              <select
                className="form-select form-select-sm"
                style={{ maxWidth: 120 }}
                value={isActiveFilter}
                onChange={e => setIsActiveFilter(e.target.value)}
              >
                {ACTIVE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            {loading ? (
              <Loading />
            ) : error ? (
              <ErrorMessage message={error} onRetry={fetchAlerts} />
            ) : alerts.length === 0 ? (
              <div className="text-center py-5 text-muted">알림이 없습니다.</div>
            ) : (
              <div className="table-responsive">
                <table className="table table-hover align-middle mb-0" style={{ fontSize: '0.85rem' }}>
                  <thead className="table-light">
                    <tr>
                      <th>ID</th>
                      <th>제목</th>
                      <th>내용</th>
                      <th>동/리</th>
                      <th>유형</th>
                      <th>긴급도</th>
                      <th>작성자</th>
                      <th>활성여부</th>
                      <th>등록일</th>
                    </tr>
                  </thead>
                  <tbody>
                    {alerts.map(alert => (
                      <tr key={alert.id}>
                        <td className="text-muted small">{alert.id}</td>
                        <td className="fw-semibold">{alert.title}</td>
                        <td>
                          {alert.content ? (
                            <span className="text-muted">
                              {alert.content.length > 60
                                ? alert.content.substring(0, 60) + '…'
                                : alert.content}
                            </span>
                          ) : (
                            <span className="text-muted">-</span>
                          )}
                        </td>
                        <td>{(alert.town || '') + (alert.village ? ' ' + alert.village : '') || '-'}</td>
                        <td>
                          {alert.alert_type ? (
                            <span className={`badge bg-${ALERT_TYPE_COLORS[alert.alert_type] || 'secondary'}`}>
                              {ALERT_TYPE_LABELS[alert.alert_type] || alert.alert_type}
                            </span>
                          ) : (
                            <span className="text-muted">-</span>
                          )}
                        </td>
                        <td>
                          {alert.urgency ? (
                            <span className={`badge bg-${URGENCY_COLORS[alert.urgency] || 'secondary'}`}>
                              {alert.urgency}
                            </span>
                          ) : (
                            <span className="text-muted">-</span>
                          )}
                        </td>
                        <td>{alert.author_name || '-'}</td>
                        <td className="text-center">{alert.is_active ? '✅' : '❌'}</td>
                        <td className="small text-muted">
                          {alert.created_at ? new Date(alert.created_at).toLocaleDateString() : '-'}
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
