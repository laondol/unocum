import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

export default function VillageJoinPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const code = searchParams.get('code') || ''
  const [photo, setPhoto] = useState<File | null>(null)
  const [caretaker, setCaretaker] = useState<{ name?: string; phone?: string } | null>(null)
  const [riBadges, setRiBadges] = useState<string[]>([])
  const [sending, setSending] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!code) { setLoading(false); return }
    api.get<{ caretaker?: { name?: string; phone?: string }; ri_badges?: string[] }>(`/api/village/join-info`, { code })
      .then(data => {
        if (data.caretaker) setCaretaker(data.caretaker)
        if (data.ri_badges) setRiBadges(data.ri_badges)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [code])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSending(true); setError('')
    try {
      const fd = new FormData()
      fd.append('code', code)
      if (photo) fd.append('photo', photo)
      const res = await api.upload<{ status: string }>('/village/join', fd)
      if (res.status === 'success') navigate('/village')
      else setError(res.status || '가입 실패')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '가입 중 오류가 발생했습니다.')
    } finally { setSending(false) }
  }

  if (loading) return <Loading />

  return (
    <div style={{ maxWidth: 500, margin: '0 auto' }}>
      <div className="card border-0 shadow-sm p-4" style={{ borderRadius: 16 }}>
        <h4 className="fw-bold mb-3">마을 가입</h4>
        {error && <ErrorMessage message={error} />}

        {code && caretaker && (
          <div className="alert alert-info py-2 small mb-3">
            <strong>담당자:</strong> {caretaker.name} ({caretaker.phone})
          </div>
        )}

        {code && riBadges.length > 0 && (
          <div className="mb-3">
            <small className="fw-bold text-muted">선택한 리</small>
            <div className="d-flex gap-1 flex-wrap mt-1">
              {riBadges.map((ri, i) => <span key={i} className="badge bg-success">{ri}</span>)}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label className="small fw-bold">초대 코드</label>
            <input type="text" className="form-control" value={code} readOnly />
          </div>
          <div className="mb-3">
            <label className="small fw-bold">사진 (선택)</label>
            <input type="file" className="form-control form-control-sm" accept="image/*"
              onChange={e => setPhoto(e.target.files?.[0] || null)} />
          </div>
          <button type="submit" className="btn btn-success w-100" disabled={sending}>
            {sending ? '처리 중...' : '가입하기'}
          </button>
        </form>
      </div>
    </div>
  )
}
