import { useState, useEffect } from 'react'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

interface PageGroup {
  title: string
  pages?: Record<string, string>
  groups?: { label: string; pages: Record<string, string> }[]
}

interface AdminUser {
  id: number; username: string; email: string; real_name: string
  role: string; town: string; village: string
  is_verified_resident: boolean; managed_pages: string
}

interface PageManagersData {
  admins: AdminUser[]
  all_pages: PageGroup[]
}

export default function AdminPageManagers() {
  const [data, setData] = useState<PageManagersData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true); setError('')
    try {
      const res = await fetch('/api/admin/page-managers')
      if (!res.ok) throw new Error('불러오기 실패')
      setData(await res.json())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const togglePage = async (userId: number, page: string) => {
    const fd = new FormData()
    fd.append('user_id', String(userId))
    fd.append('page', page)
    fd.append('action', 'toggle')
    const res = await fetch('/admin/page-managers', { method: 'POST', body: fd })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: '요청 실패' }))
      alert(err.error || '요청 실패')
    }
    load()
  }

  if (loading) return <div className="px-0 px-md-2"><Loading /></div>
  if (error) return <div className="px-0 px-md-2"><ErrorMessage message={error} onRetry={load} /></div>
  if (!data) return null

  return (
    <div className="px-0 px-md-2" style={{ maxWidth: 900 }}>
      {data.admins.map(u => {
        const up = (u.managed_pages || '').split(',').filter(Boolean)
        const isVillage = up.some(p => p.startsWith('vi_'))
        return (
          <div key={u.id}>
            <div className="card border-0 shadow-sm mb-3 sticky-top" style={{ borderRadius: 16, backgroundColor: '#e8f5e9', zIndex: 1020, top: 56 }}>
              <div className="card-body py-2 px-3">
                <div className="d-flex align-items-center gap-2 flex-wrap">
                  <div className="rounded-circle bg-success d-flex align-items-center justify-content-center text-white fw-bold flex-shrink-0"
                    style={{ width: 36, height: 36, fontSize: 14 }}>
                    {(u.real_name || u.username || u.email).slice(0, 2)}
                  </div>
                  <strong>{u.real_name || u.username || '이름없음'}</strong>
                  {u.role === 'leader' && <span className="badge bg-primary">책</span>}
                  {(u.role === 'admin' || up.length > 0) && <span className="badge bg-danger">관</span>}
                  {isVillage && <span className="badge bg-success">마</span>}
                  <span className="text-muted small">ID:{u.id}</span>
                  <span className="text-muted small">{u.email}</span>
                  <span className="text-muted small">📍{u.town || '-'} {u.village || ''}</span>
                  {u.is_verified_resident
                    ? <span className="badge bg-success small">이웃인증</span>
                    : <span className="badge bg-secondary small">미인증</span>}
                </div>
              </div>
            </div>

            {data.all_pages.map(group => (
              <div key={group.title} className="card border-0 shadow-sm mb-3" style={{ borderRadius: 16 }}>
                <div className="card-header bg-white border-bottom-0 pt-3 pb-1">
                  <h6 className="fw-bold mb-0 text-success">{group.title}</h6>
                </div>
                <div className="card-body pt-2 pb-2">
                  {group.groups ? group.groups.map(sg => (
                    <div key={sg.label} className="mb-2">
                      <div className="small fw-bold text-success mb-1">{sg.label}</div>
                      <div className="row g-2 ps-3">
                        {Object.entries(sg.pages).map(([pageKey, pageName]) => {
                          const checked = up.includes(pageKey)
                          return (
                            <div key={pageKey} className="col-md-4 col-6">
                              <div className="d-flex align-items-center">
                                <div className="form-check">
                                  <input type="checkbox" className="form-check-input" id={`chk_${u.id}_${pageKey}`}
                                    checked={checked} onChange={() => togglePage(u.id, pageKey)} />
                                  <label className="form-check-label small" htmlFor={`chk_${u.id}_${pageKey}`}
                                    style={checked ? { fontWeight: 600, color: '#27ae60' } : {}}>
                                    {checked && '✅ '}{pageName}
                                  </label>
                                </div>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )) : (
                    <div className="row g-2">
                      {Object.entries(group.pages || {}).map(([pageKey, pageName]) => {
                        const checked = up.includes(pageKey)
                        return (
                          <div key={pageKey} className="col-md-4 col-6">
                            <div className="d-flex align-items-center">
                              <div className="form-check">
                                <input type="checkbox" className="form-check-input" id={`chk_${u.id}_${pageKey}`}
                                  checked={checked} onChange={() => togglePage(u.id, pageKey)} />
                                <label className="form-check-label small" htmlFor={`chk_${u.id}_${pageKey}`}
                                  style={checked ? { fontWeight: 600, color: '#27ae60' } : {}}>
                                  {checked && '✅ '}{pageName}
                                </label>
                              </div>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )
      })}

      {data.admins.length === 0 && (
        <div className="text-center py-4 text-muted">등록된 페이지 관리자가 없습니다.</div>
      )}

      <div className="text-center mt-3">
        <a href="/admin/users" className="btn btn-sm btn-outline-secondary">&larr; 회원관리로 돌아가기</a>
      </div>
    </div>
  )
}
