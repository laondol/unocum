
export default function AdminAiChat() {
  return (
    <div className="px-0 px-md-2">
      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-4 text-center">
          <h5 className="fw-bold mb-3">AI 채팅 관리</h5>
          <a href="/admin/ai-chat" className="btn btn-success mb-3">Flutter 서버에서 열기</a>
          <p className="text-muted mb-0">관리 기능은 서버 페이지에서 이용 가능합니다</p>
        </div>
      </div>
    </div>
  )
}
