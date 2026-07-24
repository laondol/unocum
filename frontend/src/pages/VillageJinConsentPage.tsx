import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import ErrorMessage from '../components/common/ErrorMessage'

export default function VillageJinConsentPage() {
  const { target } = useParams<{ target: string }>()
  const navigate = useNavigate()
  const [agreed, setAgreed] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!agreed || !target) return
    setSending(true); setError('')
    try {
      const res = await api.post<{ status: string; myeon?: string; ri?: string }>('/village/invite-jin', { target })
      if (res.status === 'success') {
        if (target === 'join') navigate('/village/join')
        else if (res.myeon && res.ri) navigate(`/village/view/${res.myeon}/${res.ri}`)
        else navigate('/village')
      } else {
        setError(res.status || '처리 실패')
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '오류가 발생했습니다.')
    } finally { setSending(false) }
  }

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <div className="card border-0 shadow-sm p-4" style={{ borderRadius: 16 }}>
        <h4 className="fw-bold mb-3">JIN 초대 동의</h4>
        {error && <ErrorMessage message={error} />}
        <form onSubmit={handleSubmit}>
          <div className="mb-4 p-3 bg-light rounded" style={{ maxHeight: 300, overflowY: 'auto' }}>
            <p className="small">
              본인은 마을 공동체 활동에 참여하기 위해 JIN(진) 초대에 동의합니다.
              본 초대는 마을 공동체의 원활한 운영과 소통을 위해 이루어집니다.
              개인정보는 마을 운영 목적으로만 사용되며, 동의하지 않을 경우 초대가 제한될 수 있습니다.
            </p>
            <p className="small">
              - 수집 항목: 이름, 이메일, 마을 정보<br />
              - 이용 목적: 마을 공동체 초대 및 관리<br />
              - 보유 기간: 초대 철회 시까지
            </p>
          </div>
          <div className="form-check mb-3">
            <input type="checkbox" className="form-check-input" id="agree" checked={agreed}
              onChange={e => setAgreed(e.target.checked)} />
            <label className="form-check-label" htmlFor="agree">위 내용에 동의합니다.</label>
          </div>
          <button type="submit" className="btn btn-success w-100" disabled={!agreed || sending}>
            {sending ? '처리 중...' : '동의하고 계속하기'}
          </button>
        </form>
      </div>
    </div>
  )
}
