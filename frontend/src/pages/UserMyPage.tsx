import { useEffect, useState } from 'react'

interface UserInfo {
  id: number; username: string; role: string; managed_pages: string[]
}

interface MyReport {
  id: number; title: string; status: string; created_at: string
  town: string; village: string; ai_category: string; user_id: number
}

interface Schedule {
  id: number; title: string; event_date: string; event_time: string
  location: string; description: string; is_allday: boolean
}

export default function UserMyPage() {
  const [me, setMe] = useState<UserInfo | null>(null)
  const [tab, setTab] = useState('reports')
  const [reports, setReports] = useState<MyReport[]>([])
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ title: '', description: '', event_date: '', event_time: '', location: '', is_allday: false })

  useEffect(() => {
    fetch('/api/me').then(r => r.json()).then(d => { if (d.id) setMe(d) })
    fetch('/api/share/reports').then(r => r.json()).then(d => setReports(Array.isArray(d) ? d : [])).catch(() => {})
    loadSchedules()
  }, [])

  function loadSchedules() {
    fetch('/api/bot/schedule').then(r => r.json()).then(d => setSchedules(d.schedules || d || [])).catch(() => {})
  }

  function saveSchedule() {
    fetch('/api/bot/schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        title: form.title, description: form.description,
        event_date: form.event_date, event_time: form.event_time,
        location: form.location, is_allday: form.is_allday ? '1' : '0'
      })
    }).then(r => r.json()).then(d => {
      if (d.status === 'success' || d.id) {
        setShowForm(false); setForm({ title: '', description: '', event_date: '', event_time: '', location: '', is_allday: false })
        loadSchedules()
      }
    }).catch(() => {})
  }

  function deleteSchedule(id: number) {
    if (!confirm('삭제하시겠습니까?')) return
    fetch('/api/bot/schedule/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ id: String(id) })
    }).then(r => r.json()).then(() => loadSchedules()).catch(() => {})
  }

  if (!me) return <div className="text-center py-5"><p>로그인이 필요합니다.</p><a href="/login" className="btn btn-success">로그인</a></div>

  const myReports = reports.filter(r => r.user_id === me.id)

  return (
    <div>
      <div className="d-flex align-items-center gap-3 mb-4">
        <div className="bg-success text-white rounded-circle d-flex align-items-center justify-content-center" style={{ width: 56, height: 56, fontSize: 24 }}>
          {me.username.charAt(0).toUpperCase()}
        </div>
        <div>
          <h4 className="mb-1 fw-bold">{me.username}</h4>
          <span className="badge bg-light text-dark me-2">👤 {me.role === 'admin' ? '관리자' : me.role === 'leader' ? '면장' : '회원'}</span>
          <a href={`/user/${me.id}`} className="btn btn-sm btn-outline-secondary">프로필 보기 →</a>
        </div>
      </div>

      <ul className="nav nav-tabs mb-3">
        <li className="nav-item"><button className={`nav-link ${tab === 'reports' ? 'active fw-bold' : ''}`} onClick={() => setTab('reports')}>📋 내 공유</button></li>
        <li className="nav-item"><button className={`nav-link ${tab === 'schedule' ? 'active fw-bold' : ''}`} onClick={() => setTab('schedule')}>📅 일정</button></li>
        <li className="nav-item"><button className={`nav-link ${tab === 'links' ? 'active fw-bold' : ''}`} onClick={() => setTab('links')}>🔗 바로가기</button></li>
      </ul>

      {tab === 'reports' && (
        <div>
          <a href="/share/report" className="btn btn-success btn-sm mb-3">📸 새 공유</a>
          {myReports.length === 0 ? <p className="text-muted small">작성한 공유가 없습니다.</p> : (
            <div className="list-group">
              {myReports.map(r => (
                <a key={r.id} href={`/share/detail/${r.id}`} className="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                  <div><span className="fw-medium">{r.title || '제목 없음'}</span><br /><small className="text-muted">{r.town} {r.village} · {r.ai_category}</small></div>
                  <span className={`badge ${r.status === 'approved' ? 'bg-success' : 'bg-danger'} rounded-pill`}>{r.status}</span>
                </a>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'schedule' && (
        <div>
          <button className="btn btn-success btn-sm mb-3" onClick={() => setShowForm(!showForm)}>{showForm ? '✕ 닫기' : '+ 새 일정'}</button>
          {showForm && (
            <div className="card p-3 mb-3 border">
              <div className="mb-2"><input className="form-control form-control-sm" placeholder="일정 제목" value={form.title} onChange={e => setForm({...form, title: e.target.value})} /></div>
              <div className="mb-2"><input className="form-control form-control-sm" type="date" value={form.event_date} onChange={e => setForm({...form, event_date: e.target.value})} /></div>
              <div className="mb-2 d-flex gap-2">
                <input className="form-control form-control-sm" type="time" value={form.event_time} onChange={e => setForm({...form, event_time: e.target.value})} disabled={form.is_allday} />
                <div className="form-check"><input className="form-check-input" type="checkbox" id="allday" checked={form.is_allday} onChange={e => setForm({...form, is_allday: e.target.checked})} /><label className="form-check-label small" htmlFor="allday">종일</label></div>
              </div>
              <div className="mb-2"><input className="form-control form-control-sm" placeholder="장소 (선택)" value={form.location} onChange={e => setForm({...form, location: e.target.value})} /></div>
              <div className="mb-2"><textarea className="form-control form-control-sm" rows={2} placeholder="설명 (선택)" value={form.description} onChange={e => setForm({...form, description: e.target.value})} /></div>
              <button className="btn btn-primary btn-sm" onClick={saveSchedule}>저장</button>
            </div>
          )}
          {schedules.length === 0 ? <p className="text-muted small">등록된 일정이 없습니다.</p> : (
            <div className="list-group">
              {schedules.map(s => (
                <div key={s.id} className="list-group-item">
                  <div className="d-flex justify-content-between">
                    <span className="fw-medium">{s.title}</span>
                    <button className="btn btn-sm btn-outline-danger py-0" onClick={() => deleteSchedule(s.id)}>🗑️</button>
                  </div>
                  <small className="text-muted">{s.event_date}{s.event_time && ` ${s.event_time}`}{s.is_allday && ' (종일)'}</small>
                  {s.location && <div><small>📍 {s.location}</small></div>}
                </div>
              ))}
            </div>
          )}
          <a href="/schedule" className="btn btn-outline-secondary btn-sm mt-2" target="_blank">📅 전체 일정 팝업 열기</a>
        </div>
      )}

      {tab === 'links' && (
        <div className="list-group">
          <a href={`/user/${me.id}`} className="list-group-item list-group-item-action">👤 내 프로필</a>
          <a href="/share/report" className="list-group-item list-group-item-action">📸 새 공유 작성</a>
          <a href="/mypage/points" className="list-group-item list-group-item-action">💰 닢 내역</a>
          <a href="/mypage/points/charge" className="list-group-item list-group-item-action">💳 닢 충전</a>
          <a href="/user/edit-profile" className="list-group-item list-group-item-action">⚙️ 회원정보 수정</a>
          <a href="/message/inbox" className="list-group-item list-group-item-action">💬 쪽지함</a>
          <a href="/schedule" className="list-group-item list-group-item-action" target="_blank">📅 일정관리</a>
        </div>
      )}
    </div>
  )
}
