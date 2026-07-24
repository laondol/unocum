import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { generateDIDKey, saveDIDKey, listDIDs, deleteDIDKey, signPayload, getDIDKey } from '../lib/did'
import Loading from '../components/common/Loading'

interface DIDInfo {
  did: string
  publicKeyJwk: JsonWebKey
  createdAt: string
}

interface VCSubject {
  id: string
  resident: boolean
  town: string
  village: string
}

interface VCItem {
  id: string
  type: string[]
  issuer: string
  issuanceDate: string
  credentialSubject: VCSubject
}

export default function MyDID() {
  const { user, loading: authLoading } = useAuth()
  const [dids, setDIDs] = useState<DIDInfo[]>([])
  const [vcs, setVCs] = useState<VCItem[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [autoIssuing, setAutoIssuing] = useState(false)
  const [tab, setTab] = useState<'keys' | 'vcs'>('keys')

  const load = async () => {
    setLoading(true)
    try {
      const stored = await listDIDs()
      setDIDs(stored as DIDInfo[])
      const res = await fetch('/api/did/vc')
      if (res.ok) setVCs(await res.json())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { if (!authLoading) load() }, [authLoading])

  const handleCreate = async () => {
    if (!user?.id) return alert('로그인 필요')
    setCreating(true)
    try {
      const keyPair = await generateDIDKey()
      const jwk = await crypto.subtle.exportKey('jwk', keyPair.publicKey)
      const did = `did:yp:${user.id}:${Date.now()}`
      await saveDIDKey(did, keyPair)
      const res = await fetch('/api/did/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ did, publicKeyJwk: jwk }),
      })
      if (!res.ok) { const e = await res.json(); alert(e.error || '등록 실패'); return }
      alert('✅ DID 생성 완료: ' + did)
      load()
    } catch (e) { alert('생성 실패: ' + e) }
    finally { setCreating(false) }
  }

  const handleDelete = async (did: string) => {
    if (!confirm('DID 키를 삭제하시겠습니까?')) return
    await deleteDIDKey(did)
    load()
  }

  const handleExport = async (did: string) => {
    const keyPair = await getDIDKey(did)
    if (!keyPair) return alert('키 없음')
    const pub = await crypto.subtle.exportKey('jwk', keyPair.publicKey)
    const blob = new Blob([JSON.stringify({ did, publicKeyJwk: pub }, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `${did.replace(/:/g, '_')}.json`; a.click()
    URL.revokeObjectURL(url)
  }

  if (authLoading || loading) return <Loading />

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <h5 className="fw-bold mb-3">🔐 내 DID / VC</h5>
      <ul className="nav nav-tabs mb-3">
        <li className="nav-item"><button className={`nav-link ${tab === 'keys' ? 'active fw-bold' : ''}`} onClick={() => setTab('keys')}>🔑 DID 키</button></li>
        <li className="nav-item"><button className={`nav-link ${tab === 'vcs' ? 'active fw-bold' : ''}`} onClick={() => setTab('vcs')}>📜 VC 목록 ({vcs.length})</button></li>
      </ul>

      {tab === 'keys' && (
        <div>
          <button className="btn btn-primary mb-3" onClick={handleCreate} disabled={creating}>
            {creating ? '생성 중...' : '➕ 새 DID 키 생성'}
          </button>
          {user?.is_verified_resident && (
            <button className="btn btn-success mb-3 ms-2" onClick={async () => {
              setAutoIssuing(true)
              try {
                const res = await fetch('/api/did/auto-issue', { method: 'POST' })
                const d = await res.json()
                if (res.ok) { alert('✅ VC가 자동 발급되었습니다!'); load() }
                else alert(d.error || '발급 실패')
              } catch (e) { alert('오류: ' + e) }
              finally { setAutoIssuing(false) }
            }} disabled={autoIssuing}>
              {autoIssuing ? '발급 중...' : '🎫 주민인증 VC 발급받기'}
            </button>
          )}
          {dids.length === 0 ? (
            <div className="text-muted small py-3">생성된 DID가 없습니다. 위 버튼으로 DID를 생성하세요.</div>
          ) : (
            dids.map(d => (
              <div key={d.did} className="card border-0 shadow-sm mb-2" style={{ borderRadius: 12 }}>
                <div className="card-body p-3">
                  <div className="d-flex justify-content-between align-items-start">
                    <div>
                      <strong className="small">{d.did}</strong>
                      <div className="small text-muted">생성: {new Date(d.createdAt).toLocaleString('ko-KR')}</div>
                    </div>
                    <div className="d-flex gap-1">
                      <button className="btn btn-sm btn-outline-secondary py-0 px-1" onClick={() => handleExport(d.did)}>📤</button>
                      <button className="btn btn-sm btn-outline-danger py-0 px-1" onClick={() => handleDelete(d.did)}>🗑️</button>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {tab === 'vcs' && (
        <div>
          {vcs.length === 0 ? (
            <div className="text-muted small py-3">발급받은 VC가 없습니다. 관리자에게 문의하세요.</div>
          ) : (
            vcs.map(vc => (
              <div key={vc.id} className="card border-0 shadow-sm mb-2" style={{ borderRadius: 12 }}>
                <div className="card-body p-3">
                  <div className="small">
                    <strong>🏷️ {(vc.type || []).join(', ')}</strong>
                    <div className="text-muted">발급자: {vc.issuer}</div>
                    <div className="text-muted">발급일: {new Date(vc.issuanceDate).toLocaleString('ko-KR')}</div>
                    {vc.credentialSubject && (
                      <div className="mt-1">
                        <span className={`badge me-1 ${vc.credentialSubject.resident ? 'bg-success' : 'bg-secondary'}`}>
                          {vc.credentialSubject.resident ? '주민인증' : '미인증'}
                        </span>
                        {vc.credentialSubject.town && (
                          <span className="badge bg-light text-dark">{vc.credentialSubject.town} {vc.credentialSubject.village}</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
