import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'
import EmptyState from '../components/common/EmptyState'

interface Appointment {
  id: number
  name: string
  email: string
  phone: string
  date: string
  time_slot: string
  location: string
  content: string
  status: string
  fee: number | null
  travel_allowance: number | null
}

interface DaySchedule {
  day: number
  enabled: boolean
  start: string
  end: string
}

const DAY_NAMES = ['월', '화', '수', '목', '금', '토', '일']

export default function PsychoAdminAppointmentsPage() {
  const { user, loading: authLoading } = useAuth()
  const [tab, setTab] = useState<'appointments' | 'schedule' | 'calendar'>('appointments')
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [apprFee, setApprFee] = useState('')
  const [apprTravel, setApprTravel] = useState('')
  const [processing, setProcessing] = useState<number | null>(null)

  const [weekSchedule, setWeekSchedule] = useState<DaySchedule[]>(
    Array.from({ length: 7 }, (_, i) => ({ day: i + 1, enabled: false, start: '09:00', end: '18:00' }))
  )
  const [savingSchedule, setSavingSchedule] = useState(false)

  const [calFile, setCalFile] = useState<File | null>(null)
  const [calId, setCalId] = useState('')
  const [savingCal, setSavingCal] = useState(false)

  const loadAppointments = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/psycho/appointments')
      if (!res.ok) throw new Error('불러오기 실패')
      const data = await res.json()
      setAppointments(Array.isArray(data) ? data : data.appointments || [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally {
      setLoading(false)
    }
  }

  const loadSchedule = async () => {
    try {
      const res = await fetch('/api/psycho/schedules')
      if (!res.ok) return
      const data = await res.json()
      if (data.schedule && Array.isArray(data.schedule)) {
        setWeekSchedule(prev => {
          const updated = [...prev]
          data.schedule.forEach((s: DaySchedule) => {
            const idx = updated.findIndex(u => u.day === s.day)
            if (idx >= 0) updated[idx] = { ...updated[idx], ...s }
          })
          return updated
        })
      }
    } catch {}
  }

  const loadCalendarConfig = async () => {
    try {
      const res = await fetch('/api/psycho/calendar-config')
      if (!res.ok) return
      const data = await res.json()
      if (data.calendar_id) setCalId(data.calendar_id)
    } catch {}
  }

  useEffect(() => {
    if (!authLoading) {
      loadAppointments()
      loadSchedule()
      loadCalendarConfig()
    }
  }, [authLoading])

  const handleApprove = async (id: number) => {
    setProcessing(id)
    try {
      const fd = new FormData()
      if (apprFee) fd.append('fee', apprFee)
      if (apprTravel) fd.append('travel_allowance', apprTravel)
      const res = await fetch(`/psycho/appointment/${id}/approve`, { method: 'POST', body: fd }).then(r => r.json())
      if (res.status === 'success' || res.success) {
        setApprFee(''); setApprTravel(''); loadAppointments()
      } else alert(res.error || '승인 실패')
    } catch { alert('승인 실패') }
    finally { setProcessing(null) }
  }

  const handleReject = async (id: number) => {
    if (!confirm('예약을 거절하시겠습니까?')) return
    setProcessing(id)
    try {
      const res = await fetch(`/psycho/appointment/${id}/reject`, { method: 'POST' }).then(r => r.json())
      if (res.status === 'success' || res.success) loadAppointments()
      else alert(res.error || '거절 실패')
    } catch { alert('거절 실패') }
    finally { setProcessing(null) }
  }

  const handleSaveSchedule = async () => {
    setSavingSchedule(true)
    try {
      const res = await fetch('/api/psycho/admin/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ schedule: weekSchedule.filter(s => s.enabled) }),
      }).then(r => r.json())
      if (res.status === 'success' || res.success) alert('✅ 상담 시간이 저장되었습니다.')
      else alert(res.error || '저장 실패')
    } catch { alert('저장 실패') }
    finally { setSavingSchedule(false) }
  }

  const handleSaveCalendar = async () => {
    setSavingCal(true)
    try {
      const fd = new FormData()
      if (calFile) fd.append('service_account_json', calFile)
      if (calId) fd.append('calendar_id', calId)
      const res = await fetch('/api/psycho/admin/calendar-config', { method: 'POST', body: fd }).then(r => r.json())
      if (res.status === 'success' || res.success) alert('✅ 구글 캘린더 설정이 저장되었습니다.')
      else alert(res.error || '저장 실패')
    } catch { alert('저장 실패') }
    finally { setSavingCal(false) }
  }

  const pendingApps = appointments.filter(a => a.status === 'pending' || !a.status)
  const approvedApps = appointments.filter(a => a.status === 'approved')

  if (authLoading || loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={loadAppointments} />
  if (!user || (user.role !== 'admin' && user.role !== 'leader')) {
    return <ErrorMessage message="접근 권한이 없습니다." />
  }

  return (
    <div className="container mt-4" style={{ maxWidth: 800 }}>
      <h4 className="fw-bold mb-4">🧑‍⚕️ 심리상담 예약 관리</h4>

      <ul className="nav nav-tabs mb-4">
        <li className="nav-item">
          <button className={`nav-link ${tab === 'appointments' ? 'active fw-bold' : ''}`} onClick={() => setTab('appointments')}>
            예약 관리
          </button>
        </li>
        <li className="nav-item">
          <button className={`nav-link ${tab === 'schedule' ? 'active fw-bold' : ''}`} onClick={() => setTab('schedule')}>
            상담시간 설정
          </button>
        </li>
        <li className="nav-item">
          <button className={`nav-link ${tab === 'calendar' ? 'active fw-bold' : ''}`} onClick={() => setTab('calendar')}>
            구글 캘린더
          </button>
        </li>
      </ul>

      {tab === 'appointments' && (
        <>
          <h6 className="fw-bold mb-3">대기 중인 예약</h6>
          {pendingApps.length === 0 ? (
            <EmptyState icon="✅" title="대기 중인 예약이 없습니다" />
          ) : (
            <div className="row g-3 mb-4">
              {pendingApps.map(a => (
                <div key={a.id} className="col-12">
                  <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
                    <div className="card-body p-4">
                      <div className="d-flex justify-content-between mb-2">
                        <div>
                          <strong>{a.name}</strong>
                          <span className="text-muted small ms-2">📧 {a.email}</span>
                          {a.phone && <span className="text-muted small ms-2">📞 {a.phone}</span>}
                        </div>
                      </div>
                      <div className="small text-muted mb-2">
                        📅 {a.date} {a.time_slot} | 📍 {a.location || '-'}
                      </div>
                      {a.content && <p className="small text-muted mb-3">{a.content}</p>}
                      <div className="d-flex gap-2 align-items-center flex-wrap">
                        <input type="number" className="form-control form-control-sm" style={{ width: 120 }} placeholder="상담비"
                          value={apprFee} onChange={e => setApprFee(e.target.value)} />
                        <input type="number" className="form-control form-control-sm" style={{ width: 120 }} placeholder="교통비"
                          value={apprTravel} onChange={e => setApprTravel(e.target.value)} />
                        <button className="btn btn-sm btn-success" onClick={() => handleApprove(a.id)} disabled={processing === a.id}>
                          승인
                        </button>
                        <button className="btn btn-sm btn-outline-danger" onClick={() => handleReject(a.id)} disabled={processing === a.id}>
                          거절
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          <h6 className="fw-bold mb-3">승인된 예약</h6>
          {approvedApps.length === 0 ? (
            <EmptyState icon="📋" title="승인된 예약이 없습니다" />
          ) : (
            <div className="row g-3">
              {approvedApps.map(a => (
                <div key={a.id} className="col-12 col-md-6">
                  <div className="card border-0 shadow-sm" style={{ borderRadius: 16, borderLeft: '3px solid #198754' }}>
                    <div className="card-body p-3">
                      <strong>{a.name}</strong>
                      <div className="small text-muted">📧 {a.email}</div>
                      <div className="small text-muted">📅 {a.date} {a.time_slot}</div>
                      {a.fee && <span className="badge bg-light text-dark border mt-1">상담비: {a.fee.toLocaleString()}원</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {tab === 'schedule' && (
        <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
          <div className="card-body p-4">
            <h6 className="fw-bold mb-3">요일별 상담 가능 시간</h6>
            <div className="table-responsive">
              <table className="table align-middle">
                <thead className="table-light">
                  <tr>
                    <th>요일</th>
                    <th>활성</th>
                    <th>시작</th>
                    <th>종료</th>
                  </tr>
                </thead>
                <tbody>
                  {weekSchedule.map((s, i) => (
                    <tr key={s.day}>
                      <td className="fw-bold">{DAY_NAMES[i]}</td>
                      <td>
                        <input type="checkbox" className="form-check-input" checked={s.enabled}
                          onChange={e => {
                            const updated = [...weekSchedule]
                            updated[i] = { ...updated[i], enabled: e.target.checked }
                            setWeekSchedule(updated)
                          }} />
                      </td>
                      <td>
                        <select className="form-select form-select-sm" value={s.start}
                          onChange={e => {
                            const updated = [...weekSchedule]
                            updated[i] = { ...updated[i], start: e.target.value }
                            setWeekSchedule(updated)
                          }} disabled={!s.enabled}>
                          {Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, '0')}:00`).map(t => (
                            <option key={t} value={t}>{t}</option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <select className="form-select form-select-sm" value={s.end}
                          onChange={e => {
                            const updated = [...weekSchedule]
                            updated[i] = { ...updated[i], end: e.target.value }
                            setWeekSchedule(updated)
                          }} disabled={!s.enabled}>
                          {Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, '0')}:00`).map(t => (
                            <option key={t} value={t}>{t}</option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <button className="btn btn-primary" onClick={handleSaveSchedule} disabled={savingSchedule}>
              {savingSchedule ? '저장 중...' : '저장'}
            </button>
          </div>
        </div>
      )}

      {tab === 'calendar' && (
        <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
          <div className="card-body p-4">
            <h6 className="fw-bold mb-3">🔗 구글 캘린더 연동</h6>
            <div className="mb-3">
              <label className="small text-muted d-block mb-1">서비스 계정 JSON 파일</label>
              <input type="file" className="form-control" accept=".json"
                onChange={e => setCalFile(e.target.files?.[0] || null)} />
            </div>
            <div className="mb-3">
              <label className="small text-muted d-block mb-1">캘린더 ID</label>
              <input type="text" className="form-control" value={calId}
                onChange={e => setCalId(e.target.value)} placeholder="예: abc@group.calendar.google.com" />
            </div>
            <button className="btn btn-primary" onClick={handleSaveCalendar} disabled={savingCal}>
              {savingCal ? '저장 중...' : '저장'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
