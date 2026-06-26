export default function Intro() {
  return (
    <div className="text-center py-5">
      <div className="fs-1 mb-3">🏡</div>
      <h1 className="fw-bold mb-3">함께사는양평</h1>
      <p className="text-muted mb-4">양평군 주민 커뮤니티 플랫폼</p>
      <div className="d-flex gap-2 justify-content-center">
        <a href="/login" className="btn btn-success">로그인</a>
        <a href="/register" className="btn btn-outline-success">회원가입</a>
      </div>
    </div>
  )
}
