import { useState } from 'react'
import QRScanner from '../components/QRScanner'
import { useAuth } from '../contexts/AuthContext'

interface UserLookup {
  id: number
  username: string
  real_name: string
  town: string
  village: string
  is_verified_resident: boolean
  did?: string
}

export default function AdminIssueVC() {
  const { user } = useAuth()
  const [mode, setMode] = useState<'qr' | 'manual'>('manual')
  const [searchTerm, setSearchTerm] = useState('')
  const [users, setUsers] = useState<UserLookup[]>([])
  const [selectedUser, setSelectedUser] = useState<UserLookup | null>(null)
  const [issuing, setIssuing] = useState(false)
  const [resultVc, setResultVc] = useState<any>(null)
  const [qrSession, setQrSession] = useState<string | null>(null)
  const [qrUrl, setQrUrl] = useState('')

  const handleSearch = async () => {
    if (!searchTerm.trim()) return
    try {
      const res = await fetch(`/api/admin/users/search?q=${encodeURIComponent(searchTerm)}`)
      if (res.ok) setUsers(await res.json())
    } catch {}
  }

  const handleIssueVc = async (targetUser: UserLookup) => {
    if (!targetUser.did) return alert('이 사용자는 DID가 없습니다. 먼저 DID를 생성해주세요.')
    setIssuing(true)
    setResultVc(null)
    try {
      const res = await fetch('/api/did/issue-vc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ did: targetUser.did, userId: targetUser.id, town: targetUser.town, village: targetUser.village }),
      })
      const data = await res.json()
      if (!res.ok) { alert(data.error || '발급 실패'); return }
      setResultVc(data)
      alert('✅ VC 발급 완료!')
    } catch (e) { alert('발급 실패: ' + e) }
    finally { setIssuing(false) }
  }

  const handleCreateQrSession = async () => {
    try {
      const res = await fetch('/api/did/qr-session', { method: 'POST' })
      const data = await res.json()
      if (!res.ok) { alert(data.error || '세션 생성 실패'); return }
      const url = `${window.location.origin}/did/claim?session=${data.sessionId}`
      setQrSession(data.sessionId)
      setQrUrl(url)
    } catch (e) { alert('세션 생성 실패: ' + e) }
  }

  const handleQrScan = async (data: string) => {
    try {
      const url = new URL(data)
      const sessionId = url.searchParams.get('session')
      if (!sessionId) { alert('유효한 QR 코드가 아닙니다'); return }
      const res = await fetch('/api/did/qr-session/claim', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId }),
      })
      const d = await res.json()
      if (d.success) alert('✅ QR 세션 연결 완료! 관리자 승인 대기 중...')
      else alert(d.error || '실패')
    } catch { alert('유효한 QR 코드가 아닙니다') }
  }

  if (!user || (user.role !== 'admin' && user.role !== 'leader')) {
    return <div className="text-muted py-4 text-center">접근 권한이 없습니다.</div>
  }

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <h5 className="fw-bold mb-3">🏷️ VC 발급 (관리자)</h5>

      <ul className="nav nav-tabs mb-3">
        <li className="nav-item"><button className={`nav-link ${mode === 'manual' ? 'active fw-bold' : ''}`} onClick={() => setMode('manual')}>🔍 사용자 검색</button></li>
        <li className="nav-item"><button className={`nav-link ${mode === 'qr' ? 'active fw-bold' : ''}`} onClick={() => setMode('qr')}>📷 QR 발급</button></li>
      </ul>

      {mode === 'manual' && (
        <div>
          <div className="input-group mb-3">
            <input type="text" className="form-control" placeholder="이름/이메일 검색" value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSearch()} />
            <button className="btn btn-primary" onClick={handleSearch}>검색</button>
          </div>

          {users.map(u => (
            <div key={u.id} className="card border-0 shadow-sm mb-2" style={{ borderRadius: 12 }}>
              <div className="card-body p-3">
                <div className="d-flex justify-content-between align-items-start">
                  <div className="small">
                    <strong>{u.real_name || u.username}</strong>
                    {u.is_verified_resident && <span className="badge bg-success ms-1">주민인증</span>}
                    <div className="text-muted">{u.town} {u.village}</div>
                    <div className="text-muted">DID: {u.did || '❌ 없음'}</div>
                  </div>
                  <div className="d-flex gap-1">
                    {u.did && (
                      <button className="btn btn-sm btn-success py-0 px-2" onClick={() => handleIssueVc(u)} disabled={issuing}>
                        {issuing ? '발급 중...' : '🎫 VC 발급'}
                      </button>
                    )}
                    <button className="btn btn-sm btn-outline-info py-0 px-2" onClick={() => setSelectedUser(selectedUser?.id === u.id ? null : u)}>
                      {selectedUser?.id === u.id ? '접기' : '상세'}
                    </button>
                  </div>
                </div>
                {resultVc && selectedUser?.id === u.id && (
                  <div className="mt-2 p-2 bg-light rounded small" style={{ maxHeight: 200, overflow: 'auto' }}>
                    <pre style={{ fontSize: '0.7rem' }}>{JSON.stringify(resultVc, null, 2)}</pre>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {mode === 'qr' && (
        <div>
          <div className="mb-3">
            <button className="btn btn-primary" onClick={handleCreateQrSession} disabled={!!qrSession}>
              {qrSession ? '✅ QR 세션 활성화됨' : '🔄 새 QR 세션 생성 (3분 유효)'}
            </button>
            {qrUrl && (
              <div className="mt-2">
                <div className="small text-muted mb-1">QR URL (복사하여 QR 생성기 사용):</div>
                <code className="small">{qrUrl}</code>
              </div>
            )}
          </div>
          <div className="mb-3">
            <h6 className="small fw-bold mb-2">📷 QR 스캔 (사용자 기기에서)</h6>
            <QRScanner onScan={handleQrScan} onError={err => alert('스캔 오류: ' + err)} />
          </div>
        </div>
      )}
    </div>
  )
}
