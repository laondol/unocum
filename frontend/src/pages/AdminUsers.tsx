import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

interface AdminUser {
  id: number
  email: string
  username: string
  real_name: string
  role: string
  town: string
  village: string
  points: number
  is_verified_resident: boolean
  has_did: boolean
  has_vc: boolean
  managed_pages: number
}

type SortKey = 'email' | 'village' | 'points' | 'verified' | 'role'

export default function AdminUsers() {
  const navigate = useNavigate()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('email')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [selected, setSelected] = useState<Set<number>>(new Set())

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/admin/users')
      if (!res.ok) throw new Error('불러오기 실패')
      const data = await res.json()
      setUsers(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const filtered = useMemo(() => {
    if (!search.trim()) return users
    const q = search.toLowerCase()
    return users.filter(u =>
      u.email.toLowerCase().includes(q) ||
      u.real_name.toLowerCase().includes(q) ||
      u.username.toLowerCase().includes(q)
    )
  }, [users, search])

  const sorted = useMemo(() => {
    const arr = [...filtered]
    arr.sort((a, b) => {
      let cmp = 0
      switch (sortKey) {
        case 'email':
          cmp = a.email.localeCompare(b.email)
          break
        case 'village':
          cmp = (a.village || a.town || '').localeCompare(b.village || b.town || '')
          break
        case 'points':
          cmp = a.points - b.points
          break
        case 'verified':
          cmp = Number(a.is_verified_resident) - Number(b.is_verified_resident)
          break
        case 'role':
          cmp = a.role.localeCompare(b.role)
          break
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
    return arr
  }, [filtered, sortKey, sortDir])

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sortIcon = (key: SortKey) => {
    if (sortKey !== key) return ' ⇅'
    return sortDir === 'asc' ? ' ↑' : ' ↓'
  }

  const toggleAll = () => {
    if (selected.size === sorted.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(sorted.map(u => u.id)))
    }
  }

  const toggleOne = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleDelete = async (id: number) => {
    if (!confirm('정말 삭제하시겠습니까?')) return
    try {
      const res = await fetch(`/admin/users/delete/${id}`, { method: 'POST' })
      const data = await res.json()
      if (data.status === 'success') {
        setUsers(prev => prev.filter(u => u.id !== id))
        setSelected(prev => { const n = new Set(prev); n.delete(id); return n })
      } else {
        alert(data.msg || '삭제 실패')
      }
    } catch {
      alert('오류가 발생했습니다.')
    }
  }

  const roleBadge = (role: string) => {
    if (role === 'admin') return <span className="badge bg-danger me-1">관</span>
    if (role === 'manager') return <span className="badge bg-primary me-1">책</span>
    if (role === 'master') return <span className="badge bg-dark me-1">마</span>
    return <span className="badge bg-secondary me-1">+역할</span>
  }

  if (loading) return (
    <div className="px-0 px-md-2">
      <Loading />
    </div>
  )

  if (error) return (
    <div className="px-0 px-md-2">
      <ErrorMessage message={error} onRetry={load} />
    </div>
  )

  return (
    <div className="px-0 px-md-2">
      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h5 className="fw-bold mb-0">👥 회원 관리</h5>
            <input
              type="text"
              className="form-control form-control-sm"
              style={{ maxWidth: 260 }}
              placeholder="이메일 또는 이름 검색..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>

          {sorted.length === 0 ? (
            <div className="text-center py-5 text-muted">검색 결과가 없습니다.</div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0" style={{ fontSize: '0.85rem' }}>
                <thead className="table-light">
                  <tr>
                    <th style={{ width: 40 }}>
                      <input
                        type="checkbox"
                        className="form-check-input"
                        checked={sorted.length > 0 && selected.size === sorted.length}
                        onChange={toggleAll}
                      />
                    </th>
                    <th style={{ cursor: 'pointer' }} onClick={() => toggleSort('email')}>
                      이메일{sortIcon('email')}
                    </th>
                    <th style={{ cursor: 'pointer' }} onClick={() => toggleSort('village')}>
                      동/리{sortIcon('village')}
                    </th>
                    <th style={{ cursor: 'pointer' }} onClick={() => toggleSort('points')}>
                      닢{sortIcon('points')}
                    </th>
                    <th style={{ cursor: 'pointer' }} onClick={() => toggleSort('verified')}>
                      인증{sortIcon('verified')}
                    </th>
                    <th>DID/VC</th>
                    <th style={{ cursor: 'pointer' }} onClick={() => toggleSort('role')}>
                      역할{sortIcon('role')}
                    </th>
                    <th>관리</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map(u => (
                    <tr key={u.id}>
                      <td>
                        <input
                          type="checkbox"
                          className="form-check-input"
                          checked={selected.has(u.id)}
                          onChange={() => toggleOne(u.id)}
                        />
                      </td>
                      <td>
                        <a
                          href={`/user/${u.id}`}
                          className="text-decoration-none fw-medium"
                          onClick={e => { e.preventDefault(); navigate(`/user/${u.id}`) }}
                        >
                          {u.email}
                        </a>
                      </td>
                      <td>{u.village || u.town || '-'}</td>
                      <td>{u.points.toLocaleString()}</td>
                      <td>
                        {u.is_verified_resident ? (
                          <span className="badge bg-success">✅</span>
                        ) : (
                          <span className="text-muted">-</span>
                        )}
                      </td>
                      <td>{roleBadge(u.role)}</td>
                      <td>
                        {u.has_did ? <span className="badge bg-info me-1" title="DID 있음">DID</span> : null}
                        {u.has_vc ? <span className="badge bg-success" title="VC 있음">VC</span> : null}
                        {!u.has_did && !u.has_vc ? <span className="text-muted">-</span> : null}
                      </td>
                      <td>
                        <div className="d-flex gap-1">
                          <button
                            className="btn btn-sm btn-outline-info"
                            title="쪽지 보내기"
                            onClick={() => navigate(`/message/send?to=${u.id}`)}
                          >
                            ✉️
                          </button>
                          <button
                            className="btn btn-sm btn-outline-danger"
                            title="삭제"
                            onClick={() => handleDelete(u.id)}
                          >
                            🗑️
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
      </div>
    </div>
  )
}
