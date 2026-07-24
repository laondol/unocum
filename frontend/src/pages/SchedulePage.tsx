import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'
import EmptyState from '../components/common/EmptyState'

interface ScheduleItem {
  id: number | string; title: string; description?: string; memo?: string; location?: string
  event_date: string; end_date?: string; color?: string; is_allday?: boolean
  is_recurring?: boolean; repeat_type?: string; repeat_interval?: number
  repeat_infinite?: boolean; repeat_weekdays?: number; repeat_week_of_month?: number
  repeat_month_of_year?: number; reminder_minutes?: number; exceptions?: string
}

const DAYS = ['일', '월', '화', '수', '목', '금', '토']
const COLOR_MAP: Record<string, string> = { red: '#dc3545', blue: '#0d6efd', green: '#198754', gray: '#adb5bd', info: '#0dcaf0' }

export default function SchedulePage() {
  const navigate = useNavigate()
  const [schedules, setSchedules] = useState<ScheduleItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [year, setYear] = useState(new Date().getFullYear())
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [selectedDay, setSelectedDay] = useState<number | null>(new Date().getDate())
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | string | null>(null)
  const [showDelModal, setShowDelModal] = useState<number | string | null>(null)
  const [saving, setSaving] = useState(false)
  const formRef = useRef<HTMLDivElement>(null)

  const [formTitle, setFormTitle] = useState('')
  const [formDate, setFormDate] = useState('')
  const [formEndDate, setFormEndDate] = useState('')
  const [formStartTime, setFormStartTime] = useState('')
  const [formEndTime, setFormEndTime] = useState('')
  const [formLocation, setFormLocation] = useState('')
  const [formMemo, setFormMemo] = useState('')
  const [formAllDay, setFormAllDay] = useState(false)
  const [formRecurring, setFormRecurring] = useState(false)
  const [formRepeatType, setFormRepeatType] = useState('')
  const [formReminder, setFormReminder] = useState(0)

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const d = await fetch('/api/bot/schedule').then(r => r.json())
      setSchedules(Array.isArray(d.schedules) ? d.schedules : [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const daysInMonth = new Date(year, month, 0).getDate()
  const firstDay = new Date(year, month - 1, 1).getDay()

  const eventsForDay = (day: number) => {
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    return schedules.filter(s => (s.event_date || '').startsWith(dateStr))
  }

  const changeMonth = (delta: number) => {
    let m = month + delta
    let y = year
    if (m < 1) { m = 12; y-- }
    if (m > 12) { m = 1; y++ }
    setYear(y); setMonth(m)
  }

  const openAdd = (day?: number) => {
    setEditingId(null)
    setFormTitle(''); setFormLocation(''); setFormMemo(''); setFormAllDay(false)
    setFormRecurring(false); setFormRepeatType(''); setFormReminder(0)
    setFormEndDate(''); setFormStartTime(''); setFormEndTime('')
    const d = day || selectedDay || 1
    setFormDate(`${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`)
    setShowForm(true)
    setTimeout(() => formRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
  }

  const openEdit = (s: ScheduleItem) => {
    setEditingId(s.id)
    setFormTitle(s.title)
    const dt = s.event_date || ''
    setFormDate(dt.slice(0, 10))
    setFormStartTime(dt.length > 10 ? dt.slice(11, 16) : '')
    if (s.end_date) {
      setFormEndDate(s.end_date.slice(0, 10))
      setFormEndTime(s.end_date.length > 10 ? s.end_date.slice(11, 16) : '')
    } else {
      setFormEndDate(''); setFormEndTime('')
    }
    setFormLocation(s.location || '')
    setFormMemo(s.memo || '')
    setFormAllDay(s.is_allday || false)
    setFormRecurring(s.is_recurring || false)
    setFormRepeatType(s.repeat_type || '')
    setFormReminder(s.reminder_minutes || 0)
    setShowForm(true)
    setTimeout(() => formRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
  }

  const handleSave = async () => {
    if (!formTitle.trim()) return alert('제목을 입력하세요')
    setSaving(true)
    try {
      const body: Record<string, unknown> = {
        title: formTitle.trim(),
        location: formLocation,
        memo: formMemo,
        is_allday: formAllDay,
        is_recurring: formRecurring,
        repeat_type: formRepeatType,
        reminder_minutes: formReminder,
      }
      const eventDate = formDate + (formStartTime && !formAllDay ? `T${formStartTime}:00` : 'T00:00:00')
      body.event_date = eventDate
      if (formEndDate) {
        body.end_date = formEndDate + (formEndTime && !formAllDay ? `T${formEndTime}:00` : 'T23:59:00')
      }
      if (editingId) {
        body.id = typeof editingId === 'string' ? parseInt(editingId.split('_')[0]) : editingId
        await fetch('/api/bot/schedule/update', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(r => r.json())
      } else {
        await fetch('/api/bot/schedule', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(r => r.json())
      }
      setShowForm(false); setEditingId(null); load()
    } catch { alert('저장 실패') }
    finally { setSaving(false) }
  }

  const handleDelete = async (mode?: string) => {
    const id = showDelModal
    if (!id) return
    try {
      const body: Record<string, unknown> = { id: typeof id === 'string' ? parseInt(id.split('_')[0]) : id }
      const isRecurring = schedules.find(s => s.id === id)?.is_recurring
      if (isRecurring && mode) body.mode = mode
      if (!isRecurring || mode) {
        await fetch('/api/bot/schedule/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(r => r.json())
        setShowDelModal(null); load()
      }
    } catch { alert('삭제 실패') }
  }

  const deleteClick = (id: number | string) => {
    const s = schedules.find(s => s.id === id)
    if (s?.is_recurring) { setShowDelModal(id) }
    else if (confirm('삭제하시겠습니까?')) {
      fetch('/api/bot/schedule/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }) })
        .then(r => r.json()).then(() => load())
    }
  }

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <div className="d-flex gap-2 mb-3">
        <button className="btn btn-sm btn-outline-secondary" onClick={() => setShowForm(false)}>달력</button>
        <button className="btn btn-sm btn-success" onClick={() => openAdd()}>+ 일정등록</button>
        <button className="btn btn-sm btn-outline-secondary ms-auto" onClick={() => navigate('/user/' + (window as unknown as Record<string, unknown>).userId || '')}>내 프로필</button>
      </div>

      {!showForm ? (
        <>
          <div className="d-flex justify-content-between align-items-center mb-2">
            <button className="btn btn-sm btn-outline-secondary" onClick={() => changeMonth(-1)}>◀</button>
            <span className="fw-bold">{year}년 {month}월</span>
            <button className="btn btn-sm btn-outline-secondary" onClick={() => changeMonth(1)}>▶</button>
          </div>

          <div className="d-grid mb-2" style={{ gridTemplateColumns: 'repeat(7, 1fr)', gap: 2 }}>
            {DAYS.map(d => <div key={d} className="text-center small fw-bold text-muted py-1">{d}</div>)}
            {Array.from({ length: firstDay }).map((_, i) => <div key={`e${i}`} />)}
            {Array.from({ length: daysInMonth }).map((_, i) => {
              const day = i + 1
              const today = new Date()
              const isToday = year === today.getFullYear() && month === today.getMonth() + 1 && day === today.getDate()
              const events = eventsForDay(day)
              const isSelected = selectedDay === day
              return (
                <div key={day}
                  onClick={() => setSelectedDay(day)}
                  style={{
                    textAlign: 'center', padding: '6px 2px', borderRadius: 8, cursor: 'pointer',
                    background: isSelected ? '#0d6efd' : isToday ? '#d4f4ec' : undefined,
                    color: isSelected ? '#fff' : undefined,
                    fontWeight: isToday ? 700 : undefined,
                  }}>
                  {day}
                  {events.length > 0 && (
                    <div style={{ display: 'flex', justifyContent: 'center', gap: 2, marginTop: 2 }}>
                      {[...new Set(events.map(e => e.color || 'gray'))].slice(0, 3).map(c => (
                        <div key={c} style={{ width: 5, height: 5, borderRadius: '50%', background: COLOR_MAP[c] || '#adb5bd' }} />
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          <div className="d-flex justify-content-between align-items-center mb-2">
            <strong>{selectedDay ? `${year}년 ${month}월 ${selectedDay}일` : ''}</strong>
            <button className="btn btn-sm btn-outline-success" onClick={() => openAdd()}>+ 추가</button>
          </div>

          <div>
            {selectedDay && eventsForDay(selectedDay).length === 0 && (
              <EmptyState icon="📅" title="등록된 일정이 없습니다." />
            )}
            {selectedDay && (() => {
              const dayScheds = eventsForDay(selectedDay).sort((a, b) => (a.event_date || '').localeCompare(b.event_date || ''))
              return dayScheds.length === 0 ? (
                <EmptyState icon="📅" title="등록된 일정이 없습니다." />
              ) : dayScheds.map((s, idx) => {
                let transitBtns: React.ReactNode = null
                const isTransit = (s.title && (s.title.includes('이동') || s.title.includes('집으로'))) && s.content
                if (isTransit) {
                  try {
                    const r = JSON.parse(s.content)
                    if (r && r.from_lat && r.to_lat) {
                      const dl = encodeURIComponent(s.departure_location || '출발')
                      const al = encodeURIComponent(s.return_location || s.location || '도착')
                      const fromLat = parseFloat(r.from_lat).toFixed(7)
                      const fromLng = parseFloat(r.from_lng).toFixed(7)
                      const toLat = parseFloat(r.to_lat).toFixed(7)
                      const toLng = parseFloat(r.to_lng).toFixed(7)
                      const ts = s.end_date || s.event_date
                      let arrTs = ''
                      if (ts) {
                        try {
                          const parts = ts.split(' ')
                          const dp = parts[0].split('-')
                          const tp = parts[1].split(':')
                          const d = new Date(Date.UTC(parseInt(dp[0]), parseInt(dp[1]) - 1, parseInt(dp[2]), parseInt(tp[0]), parseInt(tp[1])))
                          if (!isNaN(d.getTime())) arrTs = Math.floor(d.getTime() / 1000).toString()
                        } catch {}
                      }
                      const isHome = s.title.includes('집으로')
                      const dataParam = isHome
                        ? '!3m1!4b1!4m4!4m3!2m1!6e2!3e3'
                        : '!3m1!4b1!4m6!4m5!2m3!6e1!7e2!8j' + (arrTs || '') + '!3e3'
                      transitBtns = (
                        <div className="d-flex gap-1 mt-1 flex-wrap">
                          <a className="btn btn-sm btn-outline-danger py-0" target="_blank" rel="noopener noreferrer"
                            href={`https://www.google.co.kr/maps/dir/${fromLat},${fromLng}/${toLat},${toLng}/data=${dataParam}`}>🌐Google</a>
                          <a className="btn btn-sm btn-outline-info py-0" target="_blank" rel="noopener noreferrer"
                            href={`https://map.naver.com/p/directions/${r.from_lng},${r.from_lat},${dl}/${r.to_lng},${r.to_lat},${al}/-/transit`}>🗺️네이버</a>
                          <a className="btn btn-sm btn-outline-success py-0" target="_blank" rel="noopener noreferrer"
                            href={`https://map.kakao.com/link/by/traffic/${dl},${r.from_lat},${r.from_lng}/${al},${r.to_lat},${r.to_lng}`}>📱카카오</a>
                        </div>
                      )
                    }
                  } catch {}
                }
                return (
                  <div key={s.id}>
                    <div className="card border-0 shadow-sm mb-1" style={{
                      borderRadius: 12,
                      borderLeft: `3px solid ${COLOR_MAP[s.color || 'gray'] || '#adb5bd'}`,
                    }}>
                      <div className="card-body p-3">
                        <div className="d-flex justify-content-between align-items-start">
                          <div>
                            <strong>{s.title}</strong>
                            {s.is_recurring && <span className="badge bg-light text-dark ms-1" style={{ fontSize: '0.65rem' }}>🔄</span>}
                          </div>
                          <div className="d-flex gap-1">
                            <button className="btn btn-sm btn-outline-secondary py-0 px-1" onClick={() => openEdit(s)}>✏️</button>
                            <button className="btn btn-sm btn-outline-danger py-0 px-1" onClick={() => deleteClick(s.id)}>🗑️</button>
                          </div>
                        </div>
                        <div className="small text-muted mt-1">
                          {s.event_date && (
                            <span>{new Date(s.event_date).toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                          )}
                          {s.location && <span> · 📍 {s.location}</span>}
                        </div>
                        {(s.description || s.memo) && (
                          <div className="small text-muted mt-1" style={{ whiteSpace: 'pre-wrap' }} dangerouslySetInnerHTML={{ __html: (s.description || s.memo || '').replace(/\n/g, '<br>') }} />
                        )}
                        {transitBtns}
                      </div>
                    </div>

                  </div>
                )
              })
            })()}
          </div>
        </>
      ) : (
        <div ref={formRef} className="card p-3" style={{ borderRadius: 16 }}>
          <h6 className="mb-3">{editingId ? '일정 수정' : '새 일정'}</h6>
          <input className="form-control form-control-sm mb-2" placeholder="제목" value={formTitle} onChange={e => setFormTitle(e.target.value)} />
          <div className="row g-2 mb-2">
            <div className="col-5">
              <label className="small d-block">날짜</label>
              <input type="date" className="form-control form-control-sm" value={formDate} onChange={e => setFormDate(e.target.value)} />
            </div>
            <div className="col-4">
              <label className="small d-block">시간</label>
              <input type="time" className="form-control form-control-sm" value={formStartTime} onChange={e => setFormStartTime(e.target.value)} disabled={formAllDay} />
            </div>
            <div className="col-3 d-flex align-items-end">
              <label className="small"><input type="checkbox" checked={formAllDay} onChange={e => setFormAllDay(e.target.checked)} /> 종일</label>
            </div>
          </div>
          <div className="row g-2 mb-2">
            <div className="col-5">
              <label className="small d-block">종료일</label>
              <input type="date" className="form-control form-control-sm" value={formEndDate} onChange={e => setFormEndDate(e.target.value)} />
            </div>
            <div className="col-4">
              <label className="small d-block">종료시간</label>
              <input type="time" className="form-control form-control-sm" value={formEndTime} onChange={e => setFormEndTime(e.target.value)} disabled={formAllDay} />
            </div>
          </div>
          <input className="form-control form-control-sm mb-2" placeholder="장소" value={formLocation} onChange={e => setFormLocation(e.target.value)} />
          <div className="mb-2">
            <label className="small d-block">메모</label>
            <textarea className="form-control form-control-sm" rows={3} value={formMemo} onChange={e => setFormMemo(e.target.value)} />
          </div>
          <div className="row g-2 mb-2">
            <div className="col-6">
              <label className="small d-block">알림</label>
              <select className="form-control form-control-sm" value={formReminder} onChange={e => setFormReminder(Number(e.target.value))}>
                <option value={0}>알림 안 함</option>
                <option value={-1}>정각</option>
                <option value={10}>10분 전</option>
                <option value={30}>30분 전</option>
                <option value={60}>1시간 전</option>
                <option value={1440}>1일 전</option>
              </select>
            </div>
            <div className="col-6 d-flex align-items-end gap-2">
              <label className="small"><input type="checkbox" checked={formRecurring} onChange={e => setFormRecurring(e.target.checked)} /> 반복</label>
              {formRecurring && (
                <select className="form-control form-control-sm" style={{ width: 'auto' }} value={formRepeatType} onChange={e => setFormRepeatType(e.target.value)}>
                  <option value="">선택</option>
                  <option value="daily">매일</option>
                  <option value="weekly">매주</option>
                  <option value="monthly">매월</option>
                  <option value="yearly">매년</option>
                </select>
              )}
            </div>
          </div>
          <div className="d-flex gap-2">
            <button className="btn btn-sm btn-success" onClick={handleSave} disabled={saving}>{saving ? '저장 중...' : '저장'}</button>
            <button className="btn btn-sm btn-outline-secondary" onClick={() => { setShowForm(false); setEditingId(null) }}>취소</button>
          </div>
        </div>
      )}

      {showDelModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: '#fff', borderRadius: 12, padding: 16, width: 280, maxWidth: '90%', boxShadow: '0 8px 24px rgba(0,0,0,0.2)' }}>
            <div className="fw-bold mb-1">반복 일정 삭제</div>
            <div className="small text-muted mb-3">어떤 범위를 삭제할까요?</div>
            <button className="btn btn-sm btn-danger w-100 mb-2" onClick={() => handleDelete('all')}>전체 삭제</button>
            <button className="btn btn-sm btn-outline-danger w-100 mb-2" onClick={() => handleDelete('this_after')}>이 일정 포함 이후</button>
            <button className="btn btn-sm btn-outline-secondary w-100 mb-2" onClick={() => handleDelete('this_only')}>이 일정만</button>
            <button className="btn btn-sm btn-light w-100" onClick={() => setShowDelModal(null)}>취소</button>
          </div>
        </div>
      )}
    </div>
  )
}
