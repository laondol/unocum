import { useAuth } from '../contexts/AuthContext'
import Loading from '../components/common/Loading'

export default function MyPagePointsPage() {
  const { user, loading } = useAuth()

  if (loading) return <Loading />

  return (
    <div className="container mt-4" style={{ maxWidth: 600 }}>
      <h4 className="fw-bold mb-4">💰 포인트</h4>
      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 16 }}>
        <div className="card-body p-4 text-center">
          <div className="fs-1 mb-2">💰</div>
          <div className="text-muted small mb-1">현재 포인트</div>
          <div className="display-6 fw-bold text-primary">
            {user?.points?.toLocaleString() ?? 0}
          </div>
          <div className="small text-muted mt-1">닢</div>
        </div>
      </div>
      <div className="d-grid gap-2 mb-4">
        <a href="/mypage/points/charge" className="btn btn-primary btn-lg fw-bold" style={{ borderRadius: 12 }}>
          포인트 충전하기
        </a>
      </div>
      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h6 className="fw-bold mb-3">📋 충전 내역</h6>
          <div className="text-center py-4 text-muted">
            <div className="fs-2 mb-2">📭</div>
            <p className="small mb-0">충전 내역을 불러올 수 없습니다.</p>
            <p className="small text-muted">서버 API 연동 시 충전 내역이 표시됩니다.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
