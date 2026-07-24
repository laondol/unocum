import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function ServiceLegalPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin' || user?.role === 'leader'

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <div className="d-flex justify-content-between align-items-start mb-3">
            <h4 className="fw-bold mb-0" style={{ color: '#198754' }}>이훈노무사 노동법률상담소</h4>
            {isAdmin && (
              <button className="btn btn-sm btn-outline-secondary" onClick={() => navigate('/service/legal/edit')}>
                ⚙️ 관리
              </button>
            )}
          </div>

          <p className="text-muted small mb-3">
            전문 노무사가 무료로 노동법률 상담을 제공합니다. 근로계약, 임금체불, 부당해고, 산업재해 등
            모든 노동문제에 대해 상담 받으세요.
          </p>

          <div className="mb-3 p-3 bg-light rounded">
            <div className="fw-bold small mb-2">👤 대표 노무사</div>
            <div className="small">이 훈 노무사 (고용노동부 인증)</div>
          </div>

          <div className="mb-3 p-3 bg-light rounded">
            <div className="fw-bold small mb-2">📋 상담 분야</div>
            <div className="small">근로계약 · 임금체불 · 부당해고 · 산업재해 · 퇴직금 · 직장내 괴롭힘 · 노동위원회 · 체불임금</div>
          </div>

          <div className="mb-3 p-3 bg-light rounded">
            <div className="fw-bold small mb-2">🕐 운영 시간</div>
            <div className="small">평일 10:00~16:00 (점심 12:00~13:00) | 주말 및 공휴일 휴무</div>
          </div>

          <div className="mb-3 p-3 bg-light rounded">
            <div className="fw-bold small mb-2">📍 위치</div>
            <div className="small">경기도 양평군 양평읍 (자세한 위치는 예약 후 안내)</div>
          </div>
        </div>
      </div>

      <div className="d-flex flex-column gap-2">
        <button className="btn btn-success py-3 fw-bold" onClick={() => navigate('/legal')}>
          법률상담 게시판
        </button>
        <button className="btn btn-outline-success py-3 fw-bold" onClick={() => navigate('/legal/issues')}>
          노동이슈
        </button>
        <button className="btn btn-outline-success py-3 fw-bold" onClick={() => navigate('/legal/schedule')}>
          방문상담 예약
        </button>
      </div>
    </div>
  )
}
