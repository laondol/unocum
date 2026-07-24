import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api, villageApi } from '../lib/api'
import type { VillageEvent, VillageAlert, VillageWish } from '../lib/types'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

interface VillageMember {
  id: number
  real_name?: string
  email?: string
  village?: string
  is_verified_resident?: boolean
  verified_method?: string
}

type Tab = 'feed' | 'members' | 'activities' | 'message' | 'qr'

export default function VillageAdminPage() {
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('feed')
  const [events, setEvents] = useState<VillageEvent[]>([])
  const [alerts, setAlerts] = useState<VillageAlert[]>([])
  const [wishes, setWishes] = useState<VillageWish[]>([])
  const [members, setMembers] = useState<VillageMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [messageContent, setMessageContent] = useState('')
  const [messageFile, setMessageFile] = useState<File | null>(null)
  const [sending, setSending] = useState(false)

  const managed = user?.managed_pages ?? []
  const hasAccess = managed.some(p => p.startsWith('village') || p.startsWith('vi_'))

  const loadFeed = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [ev, al, wi] = await Promise.all([
        villageApi.events().catch(() => []),
        villageApi.alerts().catch(() => []),
        villageApi.wishes().catch(() => []),
      ])
      setEvents(Array.isArray(ev) ? ev : [])
      setAlerts(Array.isArray(al) ? al : [])
      setWishes(Array.isArray(wi) ? wi : [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [])

  const loadMembers = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const data = await api.get<VillageMember[]>('/api/village/members')
      setMembers(Array.isArray(data) ? data : [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => {
    if (authLoading) return
    if (!hasAccess) return
    if (tab === 'feed') loadFeed()
    else if (tab === 'members') loadMembers()
    else setLoading(false)
  }, [tab, authLoading, hasAccess])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!messageContent.trim()) return
    setSending(true)
    try {
      const fd = new FormData()
      fd.append('content', messageContent.trim())
      if (messageFile) fd.append('attachment', messageFile)
      await api.upload('/village/message-all', fd)
      alert('쪽지를 전송했습니다.')
      setMessageContent('')
      setMessageFile(null)
    } catch {
      alert('전송 실패')
    } finally { setSending(false) }
  }

  if (authLoading) return <Loading />
  if (!hasAccess) return <ErrorMessage message="접근 권한이 없습니다." />

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }}>
      <h4 className="fw-bold mb-3">마을 관리</h4>
      <ul className="nav nav-tabs mb-3">
        <li className="nav-item"><button className={`nav-link ${tab === 'feed' ? 'active' : ''}`} onClick={() => setTab('feed')}>마을피드</button></li>
        <li className="nav-item"><button className={`nav-link ${tab === 'members' ? 'active' : ''}`} onClick={() => setTab('members')}>마을회원</button></li>
        <li className="nav-item"><button className={`nav-link ${tab === 'activities' ? 'active' : ''}`} onClick={() => setTab('activities')}>활동</button></li>
        <li className="nav-item"><button className={`nav-link ${tab === 'message' ? 'active' : ''}`} onClick={() => setTab('message')}>전체쪽지</button></li>
        <li className="nav-item"><button className={`nav-link ${tab === 'qr' ? 'active' : ''}`} onClick={() => setTab('qr')}>QR초대</button></li>
      </ul>

      {tab === 'feed' && (
        loading ? <Loading /> : error ? <ErrorMessage message={error} onRetry={loadFeed} /> : (
          <div>
            <h5 className="fw-bold mb-2">알림 ({alerts.length})</h5>
            {alerts.slice(0, 5).map(a => (
              <div key={a.id} className="card border-0 shadow-sm mb-2" style={{ borderRadius: 12 }}>
                <div className="card-body p-3">
                  <strong>{a.title}</strong>
                  {a.content && <p className="small text-muted mt-1 mb-0">{a.content}</p>}
                </div>
              </div>
            ))}
            <h5 className="fw-bold mb-2 mt-3">활동 ({events.length})</h5>
            {events.slice(0, 5).map(e => (
              <div key={e.id} className="card border-0 shadow-sm mb-2" style={{ borderRadius: 12, cursor: 'pointer' }}
                onClick={() => navigate(`/village/events/${e.id}`)}>
                <div className="card-body p-3 d-flex justify-content-between">
                  <span><span className={`badge ${e.event_type === 'meeting' ? 'bg-info' : 'bg-warning'} me-1`}>{e.event_type === 'meeting' ? '모임' : '활동'}</span>{e.title}</span>
                  <small className="text-muted">{e.event_date ? new Date(e.event_date).toLocaleString('ko-KR') : ''}</small>
                </div>
              </div>
            ))}
            <h5 className="fw-bold mb-2 mt-3">바람 ({wishes.length})</h5>
            {wishes.slice(0, 5).map(w => (
              <div key={w.id} className="card border-0 shadow-sm mb-2" style={{ borderRadius: 12 }}>
                <div className="card-body p-3">
                  <p className="mb-1">{w.content}</p>
                  <small className="text-muted">{w.status} | {w.created_at ? new Date(w.created_at).toLocaleDateString('ko-KR') : ''}</small>
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {tab === 'members' && (
        loading ? <Loading /> : error ? <ErrorMessage message={error} onRetry={loadMembers} /> : (
          <div className="table-responsive">
            <table className="table table-hover align-middle">
              <thead className="table-light">
                <tr><th>이름</th><th>이메일</th><th>마을</th><th>진위확인</th></tr>
              </thead>
              <tbody>
                {members.map(m => (
                  <tr key={m.id}>
                    <td>{m.real_name || '-'}</td>
                    <td>{m.email || '-'}</td>
                    <td>{m.village || '-'}</td>
                    <td>{m.is_verified_resident ? <span className="badge bg-success">완료</span> : <span className="badge bg-secondary">미확인</span>}</td>
                  </tr>
                ))}
                {members.length === 0 && (
                  <tr><td colSpan={4} className="text-center text-muted py-4">회원이 없습니다.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )
      )}

      {tab === 'activities' && (
        loading ? <Loading /> : error ? <ErrorMessage message={error} onRetry={loadFeed} /> : (
          <div>
            {events.length === 0 ? <p className="text-muted text-center py-4">등록된 활동이 없습니다.</p> : (
              events.map(e => (
                <div key={e.id} className="card border-0 shadow-sm mb-2" style={{ borderRadius: 12, cursor: 'pointer' }}
                  onClick={() => navigate(`/village/events/${e.id}`)}>
                  <div className="card-body p-3 d-flex justify-content-between">
                    <div>
                      <span className={`badge ${e.event_type === 'meeting' ? 'bg-info' : 'bg-warning'} me-1`}>{e.event_type === 'meeting' ? '모임' : '활동'}</span>
                      <strong>{e.title}</strong>
                    </div>
                    <small className="text-muted">{e.event_date ? new Date(e.event_date).toLocaleString('ko-KR') : ''}</small>
                  </div>
                  <div className="px-3 pb-2 small text-muted">📍 {e.location || '미정'}</div>
                </div>
              ))
            )}
            <button className="btn btn-sm btn-success mt-2" onClick={() => navigate('/village/events/create')}>+ 새 활동</button>
          </div>
        )
      )}

      {tab === 'message' && (
        <form onSubmit={handleSendMessage} className="card border-0 shadow-sm p-4" style={{ borderRadius: 16 }}>
          <div className="mb-3">
            <label className="small fw-bold">내용</label>
            <textarea className="form-control" rows={5} value={messageContent}
              onChange={e => setMessageContent(e.target.value)} required />
          </div>
          <div className="mb-3">
            <label className="small fw-bold">파일 첨부</label>
            <input type="file" className="form-control form-control-sm"
              onChange={e => setMessageFile(e.target.files?.[0] || null)} />
          </div>
          <button type="submit" className="btn btn-success w-100" disabled={sending}>
            {sending ? '전송 중...' : '전체 쪽지 보내기'}
          </button>
        </form>
      )}

      {tab === 'qr' && (
        <div className="text-center py-4">
          <p className="text-muted mb-3">QR 초대 페이지로 이동합니다.</p>
          <button className="btn btn-success" onClick={() => navigate('/village/qr')}>QR 초대 페이지 열기</button>
        </div>
      )}
    </div>
  )
}
