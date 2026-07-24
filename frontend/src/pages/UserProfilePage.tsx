import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

interface ProfileUser {
  id: number; username: string; real_name?: string; town?: string; village?: string;
  social_provider?: string; points: number; role?: string; managed_pages?: string;
  is_neighbor?: boolean; location_share?: boolean; village_notify?: boolean;
  curr_address?: string;
}

interface PointHistory {
  id: number; change_type: string; amount: number; balance_after: number;
  description?: string; created_at?: string;
}

interface Message {
  id: number; subject?: string; content?: string; sender_role?: string;
  is_read: boolean; created_at?: string;
}

interface PostItem {
  title: string; date?: string; type: string; url: string;
}

interface Appointment {
  id: number; title?: string; date?: string; time_slot?: string;
  location?: string; status?: string; edit_url?: string;
}

interface Draft {
  id: number; title?: string; category?: string; status?: string;
  updated_at?: string;
}

interface ShareImage {
  path: string; title?: string; url: string;
}

interface Friend {
  id: number; username: string; name: string; town: string; village: string;
}

const CATS: Record<string, string> = {
  share: '공유마당', dream: '꿈꾸기', news: '소식', legal: '법률상담',
  psycho: '심리상담', village_wish: '마을바람',
}
const TYPE_LABELS: Record<string, string> = {
  꿈꾸기: '💭 꿈꾸기', 공유: '📸 공유', 바람: '💨 마을바람', 법률: '⚖️ 법률',
}
const CHANGE_LABELS: Record<string, string> = {
  signup: '가입', monthly: '월급', post: '제안', comment: '댓글', like: '추천',
  village_report: '제보', share_report: '공유', admin_adjust: '관리자 조정',
  village_appointment: '마을지기 임명', village_monthly: '마을지기 활동비', letter: '편지발송',
}

export default function UserProfilePage() {
  const { userId } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState<{
    profile_user: ProfileUser; is_own: boolean; is_admin: boolean; is_friend: boolean;
    p_is_village: boolean; point_history: PointHistory[]; messages: Message[];
    posts: PostItem[]; appointments: Appointment[]; drafts: Draft[];
    bot_memory?: string; curr_location?: string; share_images: ShareImage[];
    recent_friends: Friend[]; profile_initial: string;
  } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showNip, setShowNip] = useState(false)
  const [showAddressEdit, setShowAddressEdit] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const r = await fetch(`/api/user/${userId}/profile`)
      if (r.status === 401) { navigate('/login'); return }
      if (!r.ok) throw new Error('불러오기 실패')
      const d = await r.json()
      setData(d)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [userId, navigate])

  useEffect(() => { load() }, [load])

  const formatDate = (s?: string) => {
    if (!s) return ''
    const d = new Date(s)
    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  }

  const formatDateShort = (s?: string) => {
    if (!s) return ''
    const d = new Date(s)
    return `${d.getMonth() + 1}/${d.getDate()}`
  }

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />
  if (!data) return null

  const u = data.profile_user
  const hasAppointments = data.is_own && data.appointments.length > 0
  const hasBotActivity = data.is_own && (data.bot_memory || data.drafts.length > 0)

  return (
    <div className="container mt-4" style={{ maxWidth: 800 }}>
      {/* Profile Header */}
      <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: 18 }}>
        <div className="card-body p-3">
          <div className="row">
            {/* Left: User info */}
            <div className="col-6 pe-3" style={{ borderRight: '2px solid #dee2e6' }}>
              <div className="d-flex align-items-center gap-2 mb-2">
                <div className="bg-success text-white rounded-circle d-flex align-items-center justify-content-center flex-shrink-0"
                  style={{ width: 48, height: 48, fontSize: '1.2rem' }}>
                  {data.profile_initial}
                </div>
                <div>
                  <div className="fw-bold small">{u.real_name || u.username}</div>
                  <small className="text-muted">@{u.username} <span className="text-muted">({{
                    google: '구글', naver: '네이버', kakao: '카카오톡',
                  }[u.social_provider || ''] || '함사양'})</span></small>
                </div>
              </div>
              <div className="d-flex gap-1 flex-wrap mb-2">
                <span className="badge bg-light text-dark small">{u.town} {u.village}</span>
                {u.is_neighbor && <span className="badge bg-success small">이웃</span>}
                {u.role === 'leader' && <span className="badge bg-primary small">책</span>}
                {(u.role === 'admin' || u.managed_pages) && <span className="badge bg-danger small">관</span>}
                {data.p_is_village && <span className="badge bg-success small">마</span>}
              </div>
              <button className="text-decoration-none border-0 bg-transparent p-0"
                onClick={() => setShowNip(!showNip)}>
                <span className="fw-bold text-success fs-5">
                  {u.points?.toLocaleString()}
                </span>
                <small className="text-muted"> 닢</small>
              </button>
              {data.is_own && (
                <div className="mt-1"><small className="text-muted">📍 {data.curr_location || '위치 없음'}</small></div>
              )}
              {data.is_own ? (
                <div className="mt-2 d-flex gap-1 flex-wrap">
                  <button className="btn btn-sm btn-outline-secondary" onClick={() => navigate('/user/edit-profile')}>✏️ 수정</button>
                  <a href="/logout" className="btn btn-sm btn-outline-danger"
                    onClick={e => { if (!confirm('로그아웃 하시겠습니까?')) e.preventDefault() }}>🚪 로그아웃</a>
                </div>
              ) : (
                <div className="mt-2">
                  {data.is_friend ? (
                    <span className="badge bg-success">👥 벗</span>
                  ) : null}
                </div>
              )}
            </div>
            {/* Right: TongBot */}
            <div className="col-6 text-center ps-3">
              {data.is_own ? (
                <>
                  <div className="mb-2">
                    <button className="btn btn-warning btn-sm"
                      onClick={() => window.open('/user/my?popup=1', 'tongbotPopup', 'width=700,height=700,left=100,top=50')}>
                      🤖 통벗
                    </button>
                  </div>
                  <div className="d-flex flex-wrap gap-1 justify-content-center">
                    <a href="/epub" className="btn btn-sm btn-outline-success">✍️ 콘텐츠</a>
                    <button className="btn btn-sm btn-outline-success"
                      onClick={() => window.open('/user/my?popup=1&tab=write', 'writePopup', 'width=700,height=700,left=100,top=50')}>
                      ✍️ 글쓰기
                    </button>
                    <button className="btn btn-sm btn-outline-info"
                      onClick={() => window.open('/user/my?popup=1', 'chatPopup', 'width=700,height=700,left=100,top=50')}>
                      👥 채팅
                    </button>
                    <button className="btn btn-sm btn-outline-secondary"
                      onClick={() => window.open('/schedule?v=2', 'schedPopup', 'width=700,height=700,left=100,top=50')}>
                      📅 일정
                    </button>
                  </div>
                </>
              ) : (
                <div className="text-muted py-4"><small>통벗 정보 없음</small></div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Appointments */}
      {hasAppointments && (
        <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: 18 }}>
          <div className="card-header bg-white fw-bold" style={{ borderRadius: '18px 18px 0 0' }}>📅 법률상담 예약</div>
          <div className="card-body p-0">
            {data.appointments.map(a => (
              <div key={a.id} className="p-2 border-bottom small">
                <div className="d-flex justify-content-between">
                  <a href="/legal/schedule" className="text-decoration-none"><strong>{a.title || '상담'}</strong></a>
                  <span className={`badge bg-${a.status === 'approved' ? 'success' : a.status === 'pending' ? 'warning' : 'secondary'}`}>
                    {a.status}
                  </span>
                </div>
                <div className="text-muted">{a.date} {a.time_slot} | {a.location}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TongBot Activity */}
      {hasBotActivity && (
        <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: 18 }}>
          <div className="card-header bg-white fw-bold" style={{ borderRadius: '18px 18px 0 0' }}>🤖 통벗 활동 (30일 보관)</div>
          <div className="card-body p-0">
            {data.drafts.length > 0 && (
              <>
                <div className="px-3 pt-2 small fw-bold text-success">✍️ 글쓰기 초안</div>
                {Object.entries(CATS).map(([key, label]) => {
                  const catDrafts = data.drafts.filter(d => d.category === key)
                  if (catDrafts.length === 0) return null
                  return (
                    <div key={key}>
                      <div className="px-3 small text-muted mt-1">{label} ({catDrafts.length})</div>
                      {catDrafts.map(d => (
                        <button key={d.id}
                          className="list-group-item list-group-item-action small ps-4 border-0 text-start"
                          onClick={() => window.open(`/user/my?popup=1&tab=write&draft=${d.id}`, 'writePopup', 'width=700,height=700,left=100,top=50')}>
                          {d.title || '제목없음'}
                          <span className={`badge bg-${d.status === 'reviewed' ? 'success' : 'secondary'} ms-1`}>
                            {d.status === 'reviewed' ? '교정완료' : '작성중'}
                          </span>
                          <small className="text-muted float-end">
                            {d.updated_at ? formatDateShort(d.updated_at) : ''}
                          </small>
                        </button>
                      ))}
                    </div>
                  )
                })}
              </>
            )}
            {data.bot_memory && (
              <>
                <div className="px-3 pt-2 small fw-bold text-success">💬 최근 대화</div>
                <div className="p-2 px-3 small text-muted" style={{ whiteSpace: 'pre-wrap', maxHeight: 120, overflowY: 'auto' }}>
                  {data.bot_memory}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Location */}
      <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: 18 }}>
        <div className="card-body p-2">
          <div className="d-flex align-items-center gap-2 flex-wrap">
            <small className="text-muted">📍</small>
            <span className="fw-bold small">{data.curr_location || `${u.town || ''} ${u.village || ''}`}</span>
            {data.is_own && (
              <>
                <button className="btn btn-sm btn-outline-secondary py-0 px-1"
                  onClick={() => setShowAddressEdit(!showAddressEdit)}>✏️</button>
                <a href="/construction?tab=home" className="btn btn-sm btn-outline-secondary py-0 px-1">🏠</a>
                <div className="ms-auto d-flex gap-1">
                  <div className="form-check form-switch mb-0 small">
                    <input className="form-check-input" type="checkbox" checked={u.location_share}
                      onChange={e => fetch('/user/location/share/toggle', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ value: e.target.checked ? 'friends' : 'off' })
                      })} />
                    <label className="form-check-label">위치</label>
                  </div>
                  <div className="form-check form-switch mb-0 small">
                    <input className="form-check-input" type="checkbox" checked={u.village_notify}
                      onChange={e => fetch('/user/village/notify/toggle', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ value: e.target.checked })
                      })} />
                    <label className="form-check-label">소식</label>
                  </div>
                </div>
              </>
            )}
          </div>
          {data.is_own && (
            <div className="mt-2 p-2 bg-light rounded">
              <form method="POST" action="/user/location/correct?back=profile" className="row g-1 align-items-center">
                <div className="col-12 mb-1"><small className="text-muted">📍 위치 보정 참여시 <strong>1닢</strong> 지급</small></div>
                <div className="col-8">
                  <input type="text" name="manual_loc" className="form-control form-control-sm" placeholder="정확한 주소 입력 (예: 양수리 935)" required />
                </div>
                <div className="col-4">
                  <button className="btn btn-sm btn-outline-secondary w-100" type="submit">📍 보정</button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>

      {/* Point History */}
      <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: 18 }}>
        <div className="card-header bg-white fw-bold d-flex justify-content-between"
          style={{ borderRadius: '18px 18px 0 0', cursor: 'pointer' }}
          onClick={() => setShowNip(!showNip)}>
          <span>💎 닢 내역</span>
          <span>{showNip ? '▲' : '▼'}</span>
        </div>
        {showNip && (
          <div className="card-body p-0">
            <div className="table-responsive">
              <table className="table table-hover mb-0 small">
                <thead className="table-light">
                  <tr><th>일시</th><th>유형</th><th>변동</th><th>잔액</th><th>설명</th></tr>
                </thead>
                <tbody>
                  {data.point_history.length === 0 ? (
                    <tr><td colSpan={5} className="text-center text-muted py-4">내역 없음</td></tr>
                  ) : (
                    data.point_history.map(h => (
                      <tr key={h.id}>
                        <td className="text-muted">{formatDate(h.created_at)}</td>
                        <td>{CHANGE_LABELS[h.change_type] || h.change_type}</td>
                        <td className={`fw-bold ${h.amount > 0 ? 'text-success' : 'text-danger'}`}>
                          {h.amount > 0 ? '+' : ''}{h.amount.toLocaleString()}
                        </td>
                        <td>{h.balance_after.toLocaleString()}</td>
                        <td className="small">{h.description}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Friends + Messages */}
      <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: 18 }}>
        <div className="card-header bg-white fw-bold" style={{ borderRadius: '18px 18px 0 0' }}>
          {data.is_own ? '👥 벗 · 편지' : '💬 편지'}
        </div>
        <div className="card-body p-0">
          {data.is_own && data.recent_friends.length > 0 && (
            <div className="p-2 border-bottom">
              <small className="text-muted">최근 교류한 벗</small>
              <div className="d-flex flex-wrap gap-1 mt-1">
                {data.recent_friends.slice(0, 8).map(f => (
                  <a key={f.id} href={`/user/${f.id}`} className="badge bg-light text-dark text-decoration-none">
                    {f.name}
                  </a>
                ))}
              </div>
            </div>
          )}
          <div className="list-group list-group-flush" style={{ maxHeight: 250, overflowY: 'auto' }}>
            {data.messages.length === 0 ? (
              <div className="list-group-item text-center text-muted py-4">편지가 없습니다.</div>
            ) : (
              data.messages.map(m => (
                data.is_own ? (
                  <a key={m.id} href={`/message/read/${m.id}`}
                    className={`list-group-item list-group-item-action small ${!m.is_read && data.is_own ? 'fw-bold bg-light' : ''}`}>
                    <div className="d-flex justify-content-between">
                      <span className="text-muted">{formatDate(m.created_at)}</span>
                      {data.is_own && (
                        <span className={`badge ${m.sender_role === 'admin' ? 'bg-danger' : m.sender_role === 'leader' ? 'bg-primary' : 'bg-secondary'}`}>
                          {m.sender_role}
                        </span>
                      )}
                    </div>
                    <strong>{m.subject || '(제목 없음)'}</strong>
                    <small className="text-muted d-block">
                      {(m.content || '').startsWith('<div') ?
                        <span dangerouslySetInnerHTML={{ __html: m.content || '' }} /> :
                        (m.content || '').slice(0, 80) + ((m.content || '').length > 80 ? '...' : '')}
                    </small>
                  </a>
                ) : (
                  <div key={m.id} className="list-group-item small">
                    <div className="d-flex justify-content-between">
                      <span className="text-muted">{formatDate(m.created_at)}</span>
                      <span className={`badge ${m.is_read ? 'bg-secondary' : 'bg-warning text-dark'}`}>
                        {m.is_read ? '읽음' : '읽지않음'}
                      </span>
                    </div>
                    <strong>{m.subject || '(제목 없음)'}</strong>
                    <small className="text-muted d-block">
                      {(m.content || '').startsWith('<div') ?
                        <span dangerouslySetInnerHTML={{ __html: m.content || '' }} /> :
                        (m.content || '').slice(0, 80) + ((m.content || '').length > 80 ? '...' : '')}
                    </small>
                  </div>
                )
              ))
            )}
          </div>
        </div>
      </div>

      {/* Posts */}
      {data.posts.length > 0 && (
        <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: 18 }}>
          <div className="card-header bg-white fw-bold" style={{ borderRadius: '18px 18px 0 0' }}>📝 작성한 글</div>
          <div className="card-body p-0">
            {Object.entries(TYPE_LABELS).map(([tkey, tlabel]) => {
              const tposts = data.posts.filter(p => p.type === tkey)
              if (tposts.length === 0) return null
              return (
                <div key={tkey}>
                  <div className="px-3 pt-2 small fw-bold text-success">{tlabel} ({tposts.length})</div>
                  <div className="list-group list-group-flush">
                    {tposts.map((p, i) => (
                      <a key={i} href={p.url}
                        className="list-group-item list-group-item-action small ps-4">
                        {(p.title || '').slice(0, 50)}{(p.title || '').length > 50 ? '...' : ''}
                        <small className="text-muted float-end">{formatDate(p.date)}</small>
                      </a>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Photos */}
      {data.share_images.length > 0 && (
        <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: 18 }}>
          <div className="card-header bg-white fw-bold" style={{ borderRadius: '18px 18px 0 0' }}>🖼️ 공유한 사진</div>
          <div className="card-body p-2">
            <div className="row g-2">
              {data.share_images.map((img, i) => (
                <div key={i} className="col-4 col-md-3">
                  <a href={img.url} className="d-block position-relative">
                    <img src={img.path} className="img-fluid rounded"
                      style={{ height: 120, objectFit: 'cover', width: '100%' }}
                      onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
                      alt={img.title || '사진'} />
                    <small className="d-block text-truncate text-muted">{img.title || '사진'}</small>
                  </a>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
