import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function ServiceRampPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [vName, setVName] = useState('')
  const [vEmail, setVEmail] = useState(user?.email || '')
  const [vPhone, setVPhone] = useState('')
  const [vError, setVError] = useState('')
  const [vLoading, setVLoading] = useState(false)
  const [vSuccess, setVSuccess] = useState(false)

  const handleVolunteer = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!vName || !vEmail) { setVError('이름과 이메일을 입력해주세요.'); return }
    setVError(''); setVLoading(true)
    try {
      const res = await fetch('/service/ramp/volunteer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: vName, email: vEmail, phone: vPhone }),
      })
      const data = await res.json()
      if (!res.ok) { setVError(data.error || data.msg || '신청 실패'); return }
      setVSuccess(true)
    } catch { setVError('서버 연결 실패') }
    finally { setVLoading(false) }
  }

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <div className="card border-0 shadow-sm mb-4 text-center" style={{ borderRadius: 16, background: 'linear-gradient(135deg, #198754, #20c997)' }}>
        <div className="card-body p-5 text-white">
          <div style={{ fontSize: 48 }}>♿</div>
          <h3 className="fw-bold mt-2">함께사는양평 휠체어 경사로</h3>
          <p className="mb-0 small opacity-75">장애인과 노약자, 모든 이웃이 편리하게 다닐 수 있는 양평을 만듭니다.</p>
        </div>
      </div>

      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold mb-2">📊 현재까지 경사로 설치 현황</h5>
          <div className="row text-center g-2 mt-2">
            <div className="col-4">
              <div className="p-2 bg-light rounded">
                <div className="fw-bold" style={{ color: '#198754', fontSize: 24 }}>0</div>
                <div className="small text-muted">신청 대기</div>
              </div>
            </div>
            <div className="col-4">
              <div className="p-2 bg-light rounded">
                <div className="fw-bold" style={{ color: '#198754', fontSize: 24 }}>0</div>
                <div className="small text-muted">설치 완료</div>
              </div>
            </div>
            <div className="col-4">
              <div className="p-2 bg-light rounded">
                <div className="fw-bold" style={{ color: '#198754', fontSize: 24 }}>0</div>
                <div className="small text-muted">자원봉사자</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold mb-2">🔧 경사로 설치 안내</h5>
          <ol className="small mb-0 text-muted" style={{ lineHeight: 2 }}>
            <li>경사로가 필요한 장소를 사진과 함께 신청해주세요.</li>
            <li>현장 확인 후 맞춤형 경사로를 제작합니다.</li>
            <li>자원봉사자와 함께 설치를 진행합니다.</li>
            <li>설치 후 정기적인 점검을 통해 안전을 유지합니다.</li>
          </ol>
        </div>
      </div>

      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold mb-2">🎬 설치 영상</h5>
          <div className="bg-light d-flex align-items-center justify-content-center rounded" style={{ height: 200 }}>
            <span className="text-muted small">▶ 경사로 설치 영상 (준비 중)</span>
          </div>
        </div>
      </div>

      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold mb-2">📝 경사로 설치 신청</h5>
          <div className="alert alert-secondary py-2 small mb-0">한달 후부터 신청 받습니다. 조금만 기다려주세요!</div>
        </div>
      </div>

      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold mb-3">🙋 자원봉사 신청</h5>
          {vSuccess ? (
            <div className="alert alert-success py-2 small">자원봉사 신청이 완료되었습니다. 감사합니다!</div>
          ) : (
            <form onSubmit={handleVolunteer}>
              {vError && <div className="alert alert-danger py-2 small">{vError}</div>}
              <div className="mb-2">
                <input type="text" className="form-control" placeholder="이름" value={vName} onChange={e => setVName(e.target.value)} required />
              </div>
              <div className="mb-2">
                <input type="email" className="form-control" placeholder="이메일" value={vEmail} onChange={e => setVEmail(e.target.value)} required />
              </div>
              <div className="mb-3">
                <input type="tel" className="form-control" placeholder="연락처" value={vPhone} onChange={e => setVPhone(e.target.value)} />
              </div>
              <button type="submit" className="btn btn-success w-100 py-2 fw-bold" disabled={vLoading}>
                {vLoading ? '신청 중...' : '자원봉사 신청하기'}
              </button>
            </form>
          )}
        </div>
      </div>

      <div className="text-center">
        <button className="btn btn-sm btn-outline-secondary" onClick={() => navigate('/intro')}>← 인트로</button>
      </div>
    </div>
  )
}
