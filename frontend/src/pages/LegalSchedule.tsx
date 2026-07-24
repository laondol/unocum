import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { legalApi } from '../lib/api'
import type { LegalAppointment } from '../lib/types'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

export default function LegalSchedule() {
  const navigate = useNavigate()
  const [schedules, setSchedules] = useState<{ available_dates: string[]; time_slots: { start: string; end: string }[] } | null>(null)
  const [myAppointments, setMyAppointments] = useState<LegalAppointment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [location, setLocation] = useState('')
  const [locationDetail, setLocationDetail] = useState('')
  const [selectedDate, setSelectedDate] = useState('')
  const [selectedTime, setSelectedTime] = useState('')
  const [content, setContent] = useState('')
  const [sending, setSending] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [s, a] = await Promise.all([
        legalApi.schedules(),
        legalApi.appointments().catch(() => []),
      ])
      setSchedules(s)
      setMyAppointments(Array.isArray(a) ? a : [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name || !email || !selectedDate || !selectedTime) return
    setSending(true)
    try {
      const fd = new FormData()
      fd.append('name', name)
      fd.append('email', email)
      fd.append('phone', phone)
      fd.append('location', location)
      fd.append('location_detail', locationDetail)
      fd.append('date', selectedDate)
      fd.append('time_slot', selectedTime)
      fd.append('content', content)
      const res = await fetch('/legal/appointment/book', { method: 'POST', body: fd }).then(r => r.json())
      if (res.status === 'success') {
        alert('예약이 신청되었습니다.')
        load()
      } else {
        alert(res.msg || res.error || '예약 실패')
      }
    } catch { alert('예약 중 오류 발생') }
    finally { setSending(false) }
  }

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <h4 className="fw-bold mb-3">방문상담 예약</h4>

      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label small fw-bold">제목</label>
              <input type="text" name="title" className="form-control form-control-sm" placeholder="상담 제목" required />
            </div>
            <div className="row g-2 mb-3">
              <div className="col-6">
                <label className="form-label small fw-bold">이름</label>
                <input type="text" className="form-control" value={name} onChange={e => setName(e.target.value)} required />
              </div>
              <div className="col-6">
                <label className="form-label small fw-bold">이메일</label>
                <input type="email" className="form-control" value={email} onChange={e => setEmail(e.target.value)} required />
                <label className="form-label small fw-bold mt-1">연락처</label>
                <input type="tel" className="form-control" value={phone} onChange={e => setPhone(e.target.value)} placeholder="010-1234-5678" />
              </div>
            </div>

            <div className="mb-3">
              <label className="form-label small fw-bold">상담 장소</label>
              <div className="row g-2">
                <div className="col-6">
                  <select className="form-select" value={location} onChange={e => setLocation(e.target.value)} required>
                    <option value="">장소 선택</option>
                    <option value="법률사무소">법률사무소 방문</option>
                    <option value="출장">출장 상담 (별도 출장비)</option>
                    <option value="온라인">온라인 화상상담</option>
                  </select>
                </div>
                <div className="col-6">
                  <input type="text" className="form-control" value={locationDetail} onChange={e => setLocationDetail(e.target.value)} placeholder="상세 주소 (출장 시)" />
                </div>
              </div>
            </div>

            <div className="mb-3">
              <label className="form-label small fw-bold">예약 희망일</label>
              <select className="form-select" value={selectedDate} onChange={e => setSelectedDate(e.target.value)} required>
                <option value="">날짜 선택</option>
                {schedules?.available_dates.map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
              <div className="form-text">노무사 일정이 없는 날짜만 표시됩니다. (평일 10:00~16:00)</div>
            </div>

            <div className="mb-3">
              <label className="form-label small fw-bold">희망 시간대</label>
              <select className="form-select" value={selectedTime} onChange={e => setSelectedTime(e.target.value)} required>
                <option value="">시간 선택</option>
                {schedules?.time_slots.map(s => (
                  <option key={s.start} value={`${s.start}-${s.end}`}>{s.start}~{s.end}</option>
                ))}
              </select>
            </div>

            <div className="mb-3">
              <label className="form-label small fw-bold">상담 내용</label>
              <textarea className="form-control" rows={4} value={content} onChange={e => setContent(e.target.value)} placeholder="간단한 상담 내용을 적어주세요." />
            </div>

            <button type="submit" className="btn btn-success w-100 py-2 fw-bold" disabled={sending}>
              {sending ? '예약 중...' : '예약 신청하기'}
            </button>
          </form>
        </div>
      </div>

      <div className="text-center mt-3">
        <button className="btn btn-sm btn-outline-secondary" onClick={() => navigate('/legal')}>← 법률사무소</button>
      </div>

      {myAppointments.length > 0 && (
        <div className="card border-0 shadow-sm p-4 mt-4" style={{ borderRadius: 16 }}>
          <h5 className="fw-bold mb-3">내 상담 예약</h5>
          {myAppointments.map(a => (
            <div key={a.id} className="p-2 mb-2 border rounded small">
              <div className="d-flex justify-content-between">
                <strong>{a.content || '상담'}</strong>
                <span className={`badge bg-${a.status === 'approved' ? 'success' : a.status === 'pending' ? 'warning' : 'secondary'}`}>
                  {{ pending: '대기', approved: '승인', rejected: '거절' }[a.status as string] || a.status}
                </span>
              </div>
              <div className="text-muted">{a.date} {a.time_slot} | {a.location || '미정'}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
