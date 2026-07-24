import { useState, useEffect, useCallback } from 'react'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'
import EmptyState from '../components/common/EmptyState'

interface ScheduleEvent {
  id: number | string
  title: string
  description?: string
  memo?: string
  location?: string
  event_date: string
  end_date?: string
  color?: string
  is_allday?: boolean
  is_recurring?: boolean
  repeat_type?: string
  reminder_minutes?: number
}

interface Friend {
  id: number
  name: string
  username: string
}

interface PlanItem {
  title: string
  loc: string
  time: string
  dur: number
}

interface PlanResult {
  date: string
  from: string
  to: string
  leave_time: string
  plan: {
    title: string
    arrive: string
    dur: number
    travel_min: number
    leave_when: string
    depart_prev: string
    loc?: string
  }[]
  arrive_home: string
}

const DAYS = ['일', '월', '화', '수', '목', '금', '토']
const COLOR_MAP: Record<string, string> = { red: '#dc3545', blue: '#0d6efd', green: '#198754', gray: '#adb5bd', info: '#0dcaf0' }

function mapUrl(from: string, to: string) {
  return {
    kakao: `https://map.kakao.com/?sName=${encodeURIComponent(from)}&eName=${encodeURIComponent(to)}`,
    naver: `https://map.naver.com/index.nhn?stitle=${encodeURIComponent(from)}&etitle=${encodeURIComponent(to)}&pathType=1`,
    google: `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(from)}&destination=${encodeURIComponent(to)}`,
  }
}

export default function SchedulePopupPage() {
  const [tab, setTab] = useState<'calendar' | 'add' | 'common' | 'route'>('calendar')
  const [events, setEvents] = useState<ScheduleEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [year, setYear] = useState(new Date().getFullYear())
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [selectedDate, setSelectedDate] = useState('')

  const [formTitle, setFormTitle] = useState('')
  const [formDate, setFormDate] = useState('')
  const [formTime, setFormTime] = useState('')
  const [formLocation, setFormLocation] = useState('')
  const [formMemo, setFormMemo] = useState('')
  const [saving, setSaving] = useState(false)

  const [friends, setFriends] = useState<Friend[]>([])
  const [selectedFriendIds, setSelectedFriendIds] = useState<number[]>([])
  const [commonDuration, setCommonDuration] = useState(60)
  const [commonResult, setCommonResult] = useState<string[]>([])
  const [searchingCommon, setSearchingCommon] = useState(false)

  const [planDate, setPlanDate] = useState('')
  const [planFrom, setPlanFrom] = useState('')
  const [planTo, setPlanTo] = useState('')
  const [planItems, setPlanItems] = useState<PlanItem[]>([])
  const [planResult, setPlanResult] = useState<PlanResult | null>(null)
  const [calculatingPlan, setCalculatingPlan] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const d = await fetch('/api/bot/schedule').then(r => r.json())
      setEvents(Array.isArray(d.schedules) ? d.schedules : [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    fetch('/api/chat/friends').then(r => r.json()).then(d => setFriends(d.friends || [])).catch(() => {})
  }, [])

  useEffect(() => {
    if (tab === 'calendar' && !selectedDate) {
      setSelectedDate(new Date().toISOString().slice(0, 10))
    }
    if (tab === 'route') {
      if (!planDate) setPlanDate(new Date().toISOString().slice(0, 10))
      fetch('/api/user/location').then(r => r.json()).then(loc => {
        if (loc.town) setPlanFrom(prev => prev || (loc.town + ' ' + (loc.village || '')).trim())
      }).catch(() => {})
    }
  }, [tab])

  const daysInMonth = new Date(year, month, 0).getDate()
  const firstDay = new Date(year, month - 1, 1).getDay()

  const eventsForDay = (day: number) => {
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    return events.filter(s => (s.event_date || '').startsWith(dateStr))
  }

  const changeMonth = (delta: number) => {
    let m = month + delta
    let y = year
    if (m < 1) { m = 12; y-- }
    if (m > 12) { m = 1; y++ }
    setYear(y); setMonth(m)
  }

  const handleAddEvent = async () => {
    if (!formTitle.trim() || !formDate) return alert('제목과 날짜를 입력하세요.')
    setSaving(true)
    try {
      const eventDate = formDate + (formTime ? `T${formTime}:00` : 'T00:00:00')
      await fetch('/api/bot/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: formTitle.trim(), event_date: eventDate, location: formLocation, memo: formMemo }),
      }).then(r => r.json())
      setFormTitle(''); setFormDate(''); setFormTime(''); setFormLocation(''); setFormMemo('')
      load()
      alert('✅ 일정이 등록되었습니다.')
    } catch { alert('등록 실패') }
    finally { setSaving(false) }
  }

  const handleDelete = async (id: number | string) => {
    if (!confirm('삭제하시겠습니까?')) return
    try {
      await fetch('/api/bot/schedule/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: typeof id === 'string' ? parseInt(id.split('_')[0]) : id }),
      }).then(r => r.json())
      load()
    } catch { alert('삭제 실패') }
  }

  const handleFindCommon = async () => {
    if (selectedFriendIds.length === 0) return alert('친구를 선택하세요.')
    setSearchingCommon(true)
    try {
      const res = await fetch('/api/bot/schedule/common', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ friend_ids: selectedFriendIds, duration_min: commonDuration }),
      }).then(r => r.json())
      if (res.slots) setCommonResult(res.slots)
      else setCommonResult(res.common_times || [])
    } catch { alert('검색 실패') }
    finally { setSearchingCommon(false) }
  }

  const addPlanItem = () => {
    setPlanItems(prev => [...prev, { title: '', loc: '', time: '', dur: 60 }])
  }

  const removePlanItem = (idx: number) => {
    setPlanItems(prev => prev.filter((_, i) => i !== idx))
  }

  const updatePlanItem = (idx: number, field: keyof PlanItem, value: string | number) => {
    setPlanItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item))
  }

  const handleCalculatePlan = async () => {
    if (!planDate) return alert('날짜를 선택하세요.')
    const items = planItems.filter(p => p.title.trim())
    if (items.length === 0) return alert('약속을 하나 이상 추가하세요.')
    setCalculatingPlan(true)
    try {
      const res = await fetch('/api/bot/schedule/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date: planDate, from: planFrom, to: planTo, items }),
      }).then(r => r.json())
      if (res.error) { setPlanResult(null); alert(res.error); return }
      setPlanResult(res)
    } catch { alert('계산 실패') }
    finally { setCalculatingPlan(false) }
  }

  const handleSavePlan = async () => {
    if (!planResult || !planResult.plan) return alert('먼저 계산하기를 실행하세요.')
    if (!confirm('계산된 일정을 저장할까요?')) return
    try {
      await Promise.all(planResult.plan.map(p => fetch('/api/bot/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: p.title,
          event_date: planDate + ' ' + p.arrive + ':00',
          description: `🚌 출발: ${planResult.from} → ${planResult.leave_time} 출발 | 🏠 귀가: ${planResult.arrive_home} 도착 | 📍 ${p.title}`,
          memo: `🚌 출발: ${planResult.from} → ${planResult.leave_time} 출발 | 🏠 귀가: ${planResult.arrive_home} 도착 | 📍 ${p.title}<br>🗺️ <a href="${mapUrl(planResult.from, p.title + ' ' + (p.loc || '')).kakao}" target="_blank">카카오맵</a> | <a href="${mapUrl(planResult.from, p.title + ' ' + (p.loc || '')).naver}" target="_blank">네이버지도</a>`,
        }),
      }).then(r => r.json())))
      alert('지도 링크가 포함된 일정이 저장되었습니다!')
      load()
    } catch { alert('저장 실패') }
  }

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <ul className="nav nav-tabs mb-4">
        {(['calendar', 'add', 'common', 'route'] as const).map(t => (
          <li className="nav-item" key={t}>
            <button className={`nav-link ${tab === t ? 'active fw-bold' : ''}`} onClick={() => setTab(t)}>
              {t === 'calendar' ? '📅 달력' : t === 'add' ? '➕ 일정등록' : t === 'common' ? '👥 공통시간' : '🗺️ 동선 계획'}
            </button>
          </li>
        ))}
      </ul>

      {tab === 'calendar' && (
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
              const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
              const dayEvts = eventsForDay(day)
              const isSelected = selectedDate === dateStr
              return (
                <div key={day}
                  onClick={() => setSelectedDate(selectedDate === dateStr ? '' : dateStr)}
                  style={{
                    textAlign: 'center', padding: '6px 2px', borderRadius: 8, cursor: 'pointer',
                    background: isToday ? '#d4f4ec' : isSelected ? '#0d6efd' : undefined,
                    color: isSelected ? '#fff' : undefined,
                    fontWeight: isToday || isSelected ? 700 : undefined,
                  }}>
                  {day}
                  {dayEvts.length > 0 && (
                    <div style={{ display: 'flex', justifyContent: 'center', gap: 2, marginTop: 2 }}>
                      {[...new Set(dayEvts.map(e => e.color || 'gray'))].slice(0, 3).map(c => (
                        <div key={c} style={{ width: 5, height: 5, borderRadius: '50%', background: COLOR_MAP[c] || '#adb5bd' }} />
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
          <div>
            {selectedDate ? (() => {
              const dayScheds = events.filter(s => (s.event_date || '').startsWith(selectedDate))
                .sort((a, b) => (a.event_date || '').localeCompare(b.event_date || ''))
              if (dayScheds.length === 0) return <div className="text-muted small py-2">{selectedDate} 일정 없음</div>
              return (
                <>
                  <div className="small fw-bold mb-2">{selectedDate}</div>
                  {dayScheds.map((s, idx) => (
                    <div key={s.id}>
                      <div className="card border-0 shadow-sm mb-1" style={{
                        borderRadius: 12,
                        borderLeft: `3px solid ${COLOR_MAP[s.color || 'gray'] || '#adb5bd'}`,
                      }}>
                        <div className="card-body p-2">
                          <div className="d-flex justify-content-between align-items-start">
                            <div className="small">
                              <strong>{s.title}</strong>
                              {s.is_recurring && <span className="badge bg-light text-dark ms-1" style={{ fontSize: '0.65rem' }}>🔄</span>}
                            </div>
                            <button className="btn btn-sm btn-outline-danger py-0 px-1" onClick={() => handleDelete(s.id)}>🗑️</button>
                          </div>
                          <div className="small text-muted">
                            {s.event_date && (
                              <span>{new Date(s.event_date).toLocaleString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</span>
                            )}
                            {s.location && <span> · 📍 {s.location}</span>}
                          </div>
                          {(s.description || s.memo) && (
                            <div className="small text-muted mt-1" style={{ whiteSpace: 'pre-wrap' }} dangerouslySetInnerHTML={{ __html: (s.description || s.memo || '').replace(/\n/g, '<br>') }} />
                          )}
                        </div>
                      </div>

                    </div>
                  ))}
                </>
              )
            })() : events.length === 0 ? (
              <EmptyState icon="📅" title="등록된 일정이 없습니다." />
            ) : (
              events.map(s => (
                <div key={s.id} className="card border-0 shadow-sm mb-2" style={{
                  borderRadius: 12,
                  borderLeft: `3px solid ${COLOR_MAP[s.color || 'gray'] || '#adb5bd'}`,
                }}>
                  <div className="card-body p-3">
                    <div className="d-flex justify-content-between align-items-start">
                      <div>
                        <strong>{s.title}</strong>
                        {s.is_recurring && <span className="badge bg-light text-dark ms-1" style={{ fontSize: '0.65rem' }}>🔄</span>}
                      </div>
                      <button className="btn btn-sm btn-outline-danger py-0 px-1" onClick={() => handleDelete(s.id)}>🗑️</button>
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
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}

      {tab === 'add' && (
        <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
          <div className="card-body p-4">
            <h6 className="fw-bold mb-3">새 일정 등록</h6>
            <div className="mb-2">
              <label className="small text-muted d-block">제목</label>
              <input type="text" className="form-control" value={formTitle} onChange={e => setFormTitle(e.target.value)} placeholder="일정 제목" />
            </div>
            <div className="row g-2 mb-2">
              <div className="col-6">
                <label className="small text-muted d-block">날짜</label>
                <input type="date" className="form-control" value={formDate} onChange={e => setFormDate(e.target.value)} />
              </div>
              <div className="col-6">
                <label className="small text-muted d-block">시간</label>
                <input type="time" className="form-control" value={formTime} onChange={e => setFormTime(e.target.value)} />
              </div>
            </div>
            <div className="mb-2">
              <label className="small text-muted d-block">장소</label>
              <input type="text" className="form-control" value={formLocation} onChange={e => setFormLocation(e.target.value)} placeholder="장소" />
            </div>
            <div className="mb-3">
              <label className="small text-muted d-block">메모</label>
              <textarea className="form-control" rows={3} value={formMemo} onChange={e => setFormMemo(e.target.value)} placeholder="메모" />
            </div>
            <button className="btn btn-success" onClick={handleAddEvent} disabled={saving}>
              {saving ? '저장 중...' : '일정 등록'}
            </button>
          </div>
        </div>
      )}

      {tab === 'common' && (
        <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
          <div className="card-body p-4">
            <h6 className="fw-bold mb-3">공통 가능 시간 찾기</h6>
            <div className="mb-3">
              <label className="small text-muted d-block mb-1">친구 선택</label>
              <div className="row g-2">
                {friends.length === 0 ? (
                  <div className="text-muted small">등록된 친구가 없습니다.</div>
                ) : (
                  friends.map(f => (
                    <div key={f.id} className="col-6 col-md-4">
                      <label className="d-flex align-items-center gap-1 small" style={{ cursor: 'pointer' }}>
                        <input type="checkbox" className="form-check-input" checked={selectedFriendIds.includes(f.id)}
                          onChange={() => setSelectedFriendIds(prev =>
                            prev.includes(f.id) ? prev.filter(x => x !== f.id) : [...prev, f.id]
                          )} />
                        {f.name}
                      </label>
                    </div>
                  ))
                )}
              </div>
            </div>
            <div className="mb-3">
              <label className="small text-muted d-block">희망 시간 (분)</label>
              <input type="number" className="form-control" value={commonDuration} onChange={e => setCommonDuration(Number(e.target.value))} min={30} step={30} />
            </div>
            <button className="btn btn-primary mb-3" onClick={handleFindCommon} disabled={searchingCommon}>
              {searchingCommon ? '검색 중...' : '🔍 공통 시간 찾기'}
            </button>
            {commonResult.length > 0 && (
              <div>
                <h6 className="small fw-bold">검색 결과</h6>
                <ul className="list-group list-group-flush small">
                  {commonResult.map((slot, i) => (
                    <li key={i} className="list-group-item px-0">{slot}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'route' && (
        <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
          <div className="card-body p-4">
            <h6 className="fw-bold mb-3">🗺️ 동선 계획</h6>
            <div className="row g-2 mb-2">
              <div className="col-6">
                <small className="text-muted d-block">날짜</small>
                <input type="date" className="form-control" value={planDate} onChange={e => setPlanDate(e.target.value)} />
              </div>
            </div>
            <div className="row g-2 mb-2">
              <div className="col-6">
                <small className="text-muted d-block">출발장소</small>
                <input className="form-control" value={planFrom} onChange={e => setPlanFrom(e.target.value)} placeholder="기본장소" />
              </div>
              <div className="col-6">
                <small className="text-muted d-block">복귀장소</small>
                <input className="form-control" value={planTo} onChange={e => setPlanTo(e.target.value)} placeholder="기본장소" />
              </div>
            </div>
            <small className="text-muted">📋 약속 (도착시간 기준)</small>
            <div id="planItems" className="mb-2">
              {planItems.map((item, idx) => (
                <div key={idx} className="card p-2 mb-2">
                  <div className="row g-1 align-items-center">
                    <div className="col-4">
                      <input className="form-control form-control-sm" placeholder="약속명" value={item.title}
                        onChange={e => updatePlanItem(idx, 'title', e.target.value)} />
                    </div>
                    <div className="col-3">
                      <input className="form-control form-control-sm" placeholder="장소" value={item.loc}
                        onChange={e => updatePlanItem(idx, 'loc', e.target.value)} />
                    </div>
                    <div className="col-3">
                      <input type="time" className="form-control form-control-sm" title="도착 희망시간" value={item.time}
                        onChange={e => updatePlanItem(idx, 'time', e.target.value)} />
                    </div>
                    <div className="col-2 d-flex gap-1">
                      <input type="number" className="form-control form-control-sm" placeholder="분" value={item.dur} min={15} step={15}
                        onChange={e => updatePlanItem(idx, 'dur', parseInt(e.target.value) || 60)} />
                      <button className="btn btn-sm btn-outline-danger py-0 px-1" onClick={() => removePlanItem(idx)}>✕</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <button className="btn btn-sm btn-outline-primary w-100 mb-2" onClick={addPlanItem}>+ 약속 추가</button>
            <button className="btn btn-primary w-100" onClick={handleCalculatePlan} disabled={calculatingPlan}>
              {calculatingPlan ? '계산 중...' : '🗺️ 출발시간 계산하기'}
            </button>
            {planResult && !planResult.error && (
              <div className="alert alert-success py-2 small mt-2">
                <div dangerouslySetInnerHTML={{
                  __html: `<strong>🗺️ ${planResult.date}</strong><br>` +
                    `🏠 ${planResult.from} → <strong class="text-danger">⏰ ${planResult.leave_time} 출발!</strong><br>` +
                    planResult.plan.map(p =>
                      `  🚌 ${p.travel_min}분 → <strong>${p.arrive}</strong> ${p.title} (${p.dur}분) → ` +
                      (p.leave_when ? `<strong class="text-danger">${p.leave_when} 출발</strong>` : '끝') + '<br>'
                    ).join('') +
                    `🏠 ${planResult.to} <strong>${planResult.arrive_home}</strong> 도착`
                }} />
                {(() => {
                  let prevLoc = planResult.from
                  return planResult.plan.map((p, i) => {
                    const currentLoc = p.title + ' ' + (p.loc || '')
                    const urls = prevLoc && currentLoc ? mapUrl(prevLoc, currentLoc) : null
                    prevLoc = currentLoc
                    return urls ? (
                      <div className="d-flex gap-1 justify-content-center mb-1" key={i}>
                        <a className="btn btn-sm btn-outline-success py-0 px-2" target="_blank" rel="noopener noreferrer" href={urls.kakao}>📱 카카오맵</a>
                        <a className="btn btn-sm btn-outline-info py-0 px-2" target="_blank" rel="noopener noreferrer" href={urls.naver}>🗺️ 네이버지도</a>
                        <a className="btn btn-sm btn-outline-danger py-0 px-2" target="_blank" rel="noopener noreferrer" href={urls.google}>🌐 Google Maps</a>
                      </div>
                    ) : null
                  })
                })()}
                <button className="btn btn-sm btn-success mt-2 w-100" onClick={handleSavePlan}>
                  📥 일정에 추가하기
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
