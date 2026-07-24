import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../contexts/AuthContext'
import Loading from '../components/common/Loading'

const PRESETS = [1000, 3000, 5000, 10000]
const PAY_METHODS = [
  { id: 'card', label: '카드' },
  { id: 'bank', label: '무통장' },
  { id: 'kakaopay', label: '카카오페이' },
  { id: 'naverpay', label: '네이버페이' },
]

export default function PointsChargePage() {
  const { user, loading: authLoading } = useAuth()
  const [nip, setNip] = useState(0)
  const [customNip, setCustomNip] = useState('')
  const [payMethod, setPayMethod] = useState('card')
  const [processing, setProcessing] = useState(false)
  const [message, setMessage] = useState('')
  const [history, setHistory] = useState<{ id: number; nip: number; status: string; created_at: string }[]>([])
  const sdkLoaded = useRef(false)

  useEffect(() => {
    if (sdkLoaded.current) return
    sdkLoaded.current = true
    const script = document.createElement('script')
    script.src = 'https://cdn.portone.io/v2/browser-sdk.js'
    script.async = true
    document.head.appendChild(script)
  }, [])

  useEffect(() => {
    fetch('/api/user/points/history')
      .then(r => r.json())
      .then(d => { if (Array.isArray(d)) setHistory(d); else if (d.history) setHistory(d.history) })
      .catch(() => {})
  }, [])

  if (authLoading) return <Loading />

  const handlePreset = (amount: number) => {
    setNip(amount)
    setCustomNip('')
  }

  const handleCustomChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/[^0-9]/g, '')
    setCustomNip(val)
    setNip(val ? parseInt(val) : 0)
  }

  const handleCharge = async () => {
    if (nip <= 0) return alert('충전 금액을 입력하세요.')
    setProcessing(true)
    setMessage('')
    try {
      const prepareRes = await fetch('/api/payment/prepare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nip }),
      })
      const prepareData = await prepareRes.json()
      if (!prepareData.payment_id) throw new Error(prepareData.error || '결제 준비 실패')

      const paymentId = prepareData.payment_id
      const portOne = (window as any).PortOne
      if (!portOne) throw new Error('PortOne SDK가 로드되지 않았습니다.')

      const payRes = await portOne.requestPayment({
        storeId: prepareData.store_id || '',
        paymentId,
        orderName: `포인트 충전 ${nip}닢`,
        totalAmount: nip,
        currency: 'KRW',
        payMethod: payMethod === 'bank' ? 'BANK' : payMethod === 'card' ? 'CARD' : 'EASY_PAY',
        channelKey: prepareData.channel_key || '',
      })

      if (payRes.code === 'SUCCESS') {
        const verifyRes = await fetch('/api/payment/verify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ payment_id: paymentId, nip }),
        })
        const verifyData = await verifyRes.json()
        if (verifyData.status === 'success' || verifyData.success) {
          setMessage('✅ 충전이 완료되었습니다!')
          fetch('/api/user/points/history')
            .then(r => r.json())
            .then(d => { if (Array.isArray(d)) setHistory(d); else if (d.history) setHistory(d.history) })
            .catch(() => {})
        } else {
          setMessage('❌ ' + (verifyData.error || '결제 검증 실패'))
        }
      } else {
        setMessage('❌ ' + (payRes.message || '결제가 취소되었습니다.'))
      }
    } catch (e: unknown) {
      setMessage('❌ ' + (e instanceof Error ? e.message : '결제 처리 중 오류'))
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="container mt-4" style={{ maxWidth: 600 }}>
      <div className="alert alert-warning small mb-4" role="alert">
        🧪 테스트 모드입니다. 실제 결제가 이루어지지 않을 수 있습니다.
      </div>

      <h4 className="fw-bold mb-4">💰 포인트 충전</h4>

      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <span className="text-muted small">현재 포인트</span>
            <span className="fw-bold fs-5">{(user?.points ?? 0).toLocaleString()} 닢</span>
          </div>
          <hr />
          <label className="small text-muted mb-2">충전 금액 선택</label>
          <div className="d-flex gap-2 mb-3 flex-wrap">
            {PRESETS.map(p => (
              <button
                key={p}
                className={`btn ${nip === p && !customNip ? 'btn-primary' : 'btn-outline-primary'}`}
                onClick={() => handlePreset(p)}
              >
                {p.toLocaleString()}닢
              </button>
            ))}
          </div>
          <div className="mb-3">
            <label className="small text-muted mb-1">직접 입력</label>
            <div className="input-group">
              <input
                type="text"
                className="form-control"
                placeholder="금액 입력"
                value={customNip}
                onChange={handleCustomChange}
              />
              <span className="input-group-text">닢</span>
            </div>
          </div>
          <div className="mb-3">
            <label className="small text-muted mb-2">결제 수단</label>
            <div className="d-flex gap-2 flex-wrap">
              {PAY_METHODS.map(m => (
                <button
                  key={m.id}
                  className={`btn btn-sm ${payMethod === m.id ? 'btn-dark' : 'btn-outline-secondary'}`}
                  onClick={() => setPayMethod(m.id)}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>
          <button
            className="btn btn-success btn-lg w-100 fw-bold"
            style={{ borderRadius: 12 }}
            onClick={handleCharge}
            disabled={processing || nip <= 0}
          >
            {processing ? '처리 중...' : `${nip.toLocaleString()}닢 결제하기`}
          </button>
          {message && (
            <div className={`mt-3 alert ${message.startsWith('✅') ? 'alert-success' : 'alert-danger'} small py-2`}>
              {message}
            </div>
          )}
        </div>
      </div>

      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h6 className="fw-bold mb-3">📋 충전 내역</h6>
          {history.length === 0 ? (
            <div className="text-center py-3 text-muted small">충전 내역이 없습니다.</div>
          ) : (
            <div className="table-responsive">
              <table className="table table-sm">
                <thead>
                  <tr>
                    <th>금액</th>
                    <th>상태</th>
                    <th>일시</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map(h => (
                    <tr key={h.id}>
                      <td>{h.nip.toLocaleString()}닢</td>
                      <td><span className={`badge bg-${h.status === 'completed' ? 'success' : 'warning'}`}>{h.status}</span></td>
                      <td className="small">{new Date(h.created_at).toLocaleString('ko-KR')}</td>
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
