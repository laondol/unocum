import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function ServicePsychoPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const canManage = user?.role === 'admin' || user?.role === 'leader' || user?.managed_pages?.includes('psycho')

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <div className="d-flex justify-content-between align-items-start mb-3">
            <h4 className="fw-bold mb-0" style={{ color: '#198754' }}>숨상담심리연구소</h4>
            {canManage && (
              <button className="btn btn-sm btn-outline-secondary" onClick={() => navigate('/service/psycho/edit')}>
                ⚙️ 관리
              </button>
            )}
          </div>

          <p className="text-muted small mb-3">
            전문 심리상담사가 개인, 부부, 가족 심리상담을 제공합니다. 우울, 불안, 스트레스, 관계 갈등 등
            다양한 심리적 어려움에 대해 전문적인 상담을 받으세요.
          </p>

          <div className="mb-3 p-3 bg-light rounded">
            <div className="fw-bold small mb-2">📋 상담 분야</div>
            <div className="small">개인상담 · 부부상담 · 가족상담 · 청소년상담 · 스트레스 관리 · 우울/불안 · 트라우마 · 중독</div>
          </div>

          <div className="mb-3 p-3 bg-light rounded">
            <div className="fw-bold small mb-2">🕐 운영 시간</div>
            <div className="small">평일 09:00~18:00 (점심 12:00~13:00) | 토요일 10:00~15:00 | 일요일 휴무</div>
          </div>

          <div className="mb-3 p-3 bg-light rounded">
            <div className="fw-bold small mb-2">💰 비용 안내</div>
            <div className="small">1회 50분 기준 50,000원 (첫 상담 30,000원) | 국가예산지원사업 연계 가능</div>
          </div>
        </div>
      </div>

      <div className="d-flex flex-column gap-2">
        <button className="btn btn-success py-3 fw-bold" onClick={() => navigate('/psycho')}>
          심리상담 게시판
        </button>
        <button className="btn btn-outline-success py-3 fw-bold" onClick={() => navigate('/psycho/schedule')}>
          방문상담 예약
        </button>
      </div>
    </div>
  )
}
