
export default function AdminRampApplications() {
  return (
    <div className="px-0 px-md-2">
      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h4 className="fw-bold mb-3">🦽 경사로 신청 관리</h4>
          <p className="text-muted mb-3">경사로 신청 관리 기능은 기존 페이지에서 이용 가능합니다.</p>
          <a
            href="/admin/ramp-applications"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-success"
          >
            경사로 신청 관리 페이지 열기
          </a>
        </div>
      </div>
    </div>
  )
}
