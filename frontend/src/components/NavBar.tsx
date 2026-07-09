import { useEffect, useState } from 'react'

interface UserInfo {
  id: number | null; username: string | null; role: string | null; managed_pages: string[]
}

export default function NavBar() {
  const [me, setMe] = useState<UserInfo>({ id: null, username: null, role: null, managed_pages: [] })
  const [siteName, setSiteName] = useState('함께사는양평')

  useEffect(() => {
    const host = window.location.hostname
    if (host === 'localhost' || host === '127.0.0.1') setSiteName('함께사는로컬')
    else if (host === 'test.unocum.kr') setSiteName('함께사는테스트')

    fetch('/api/me').then(r => r.json()).then(d => { if (d.id) setMe(d) }).catch(() => {})
  }, [])

  const hasVillage = me.managed_pages?.some(p => p.startsWith('vi_') || p === 'village') || me.role === 'leader'
  const villageParts = (() => {
    for (const p of (me.managed_pages || [])) {
      if (p.startsWith('vi_')) {
        const parts = p.slice(3).split('_')
        return { myeon: parts[0] || '', ri: parts[1] || '', tooltip: parts[1] + ' 마을' }
      }
    }
    return { myeon: '', ri: '', tooltip: '마을' }
  })()

  return (
    <nav className="navbar navbar-expand-lg sticky-top mb-1">
      <div className="container">
        <div className="d-flex align-items-center flex-shrink-0">
          <a className="navbar-brand d-flex align-items-center me-1" href="/intro">
            <img src="/static/images/logo.png" alt="양평" height="36" title={siteName} />
            <span className="fw-bold text-success d-none d-lg-inline ms-2" style={{ fontSize: '1.2rem' }}>{siteName}</span>
          </a>
          <div className="d-inline-flex align-items-center position-relative" id="navQuick">
            <button className="btn btn-sm btn-outline-warning px-2 py-0" style={{ fontSize: '0.9rem' }}
              onClick={() => document.getElementById('quickMenu')?.classList.toggle('d-none')}>⭐</button>
            <a href="/share-report" className="btn btn-sm btn-outline-success px-2 py-0 ms-1" style={{ fontSize: '0.9rem' }}>📸</a>
            {me.id && hasVillage && (
              <div className="d-inline-flex align-items-center ms-1 position-relative">
                <a href="/village" className="text-decoration-none" title={villageParts.tooltip} style={{ fontSize: '1.2rem' }}
                  onClick={e => { e.preventDefault(); document.getElementById('villageMenu')?.classList.toggle('d-none') }}>🏘️</a>
                <div className="position-absolute bg-white border rounded shadow-sm p-2 d-none" id="villageMenu"
                  style={{ zIndex: 1050, minWidth: 130, top: '100%', left: 0 }}>
                  <a className="d-block small py-1 px-2 text-dark text-decoration-none rounded" href="/village">📝 봉사</a>
                  {villageParts.ri && (
                    <a className="d-block small py-1 px-2 text-dark text-decoration-none rounded"
                      href={`/village/view/${villageParts.myeon}/${villageParts.ri}`}>📖 홍보</a>
                  )}
                </div>
              </div>
            )}
            <div className="position-absolute bg-white border rounded shadow-sm p-2 d-none" id="quickMenu"
              style={{ zIndex: 1050, minWidth: 140, top: '100%', left: 0 }} onClick={e => e.stopPropagation()}>
              <a className="d-block small py-1 px-2 text-dark text-decoration-none rounded" href="/main">💭 꿈꾸기</a>
              <a className="d-block small py-1 px-2 text-dark text-decoration-none rounded" href="/construction">📍 위치기반안내</a>
              <a className="d-block small py-1 px-2 text-dark text-decoration-none rounded" href="#"
                onClick={e => { e.preventDefault(); window.open('/user/my?popup=1', 'tongbotPopup', 'width=700,height=700,left=100,top=50') }}>🤖 통벗채팅</a>
            </div>
          </div>
        </div>

        <div className="d-none d-lg-flex mx-auto flex-shrink-0">
          <form className="d-flex" action="/search" method="GET" role="search">
            <input className="form-control form-control-sm" type="search" name="q" placeholder="검색"
              style={{ width: 130, borderRadius: 20 }} />
          </form>
        </div>

        <div className="collapse navbar-collapse" id="navbarNav" style={{ background: 'white', zIndex: 1020 }}>
          <ul className="navbar-nav mx-auto align-items-center">
            <li className="nav-item dropdown mx-1">
              <a className="nav-link dropdown-toggle px-2" href="#" data-bs-toggle="dropdown">소개</a>
              <ul className="dropdown-menu border-0 shadow">
                <li style={{ fontSize: '0.7rem', fontWeight: 700, color: '#27ae60', textTransform: 'uppercase', letterSpacing: 1, padding: '6px 16px 2px' }}>소개</li>
                <li><a className="dropdown-item" href="/proposal">사업소개</a></li>
                <li><a className="dropdown-item" href="/presentation">운영계획</a></li>
                <li><hr className="dropdown-divider" /></li>
                <li><a className="dropdown-item" href="/terms">회원약관</a></li>
                <li><a className="dropdown-item" href="/charter">정관</a></li>
              </ul>
            </li>
            <li className="nav-item dropdown">
              <a className="nav-link dropdown-toggle px-2" href="#" data-bs-toggle="dropdown">소식</a>
              <ul className="dropdown-menu">
                <li style={{ fontSize: '0.7rem', fontWeight: 700, color: '#27ae60', textTransform: 'uppercase', letterSpacing: 1, padding: '6px 16px 2px' }}>소식</li>
                <li><a className="dropdown-item" href="/kr-yp-news">대한민국과양평</a></li>
                <li><a className="dropdown-item" href="/world-news">세계와양평</a></li>
                <li><a className="dropdown-item" href="/share">공유마당</a></li>
                <li><a className="dropdown-item" href="/construction">📍 위치기반안내</a></li>
              </ul>
            </li>
            <li className="nav-item dropdown mx-1">
              <a className="nav-link dropdown-toggle px-2" href="#" data-bs-toggle="dropdown">하는일</a>
              <ul className="dropdown-menu border-0 shadow">
                <li style={{ fontSize: '0.7rem', fontWeight: 700, color: '#27ae60', textTransform: 'uppercase', letterSpacing: 1, padding: '6px 16px 2px' }}>하는일</li>
                <li><a className="dropdown-item" href="/service/ramp">휠체어경사로보급사업</a></li>
                <li><a className="dropdown-item" href="/service/legal">노무사 이훈의 법률상담</a></li>
                <li><a className="dropdown-item" href="/service/psycho">숨상담심리연구소</a></li>
              </ul>
            </li>
            <li className="nav-item dropdown mx-1">
              <a className="nav-link dropdown-toggle px-2" href="#" data-bs-toggle="dropdown">제안</a>
              <ul className="dropdown-menu border-0 shadow">
                <li style={{ fontSize: '0.7rem', fontWeight: 700, color: '#27ae60', textTransform: 'uppercase', letterSpacing: 1, padding: '6px 16px 2px' }}>제안</li>
                <li><a className="dropdown-item" href="/main">꿈꾸기</a></li>
                <li><a className="dropdown-item" href="/all-proposals">누구의꿈</a></li>
              </ul>
            </li>
            {me.role === 'leader' && (
              <li className="nav-item dropdown mx-1">
                <a className="nav-link dropdown-toggle px-2" href="#" data-bs-toggle="dropdown">관리</a>
                <ul className="dropdown-menu border-0 shadow">
                  <li style={{ fontSize: '0.7rem', fontWeight: 700, color: '#27ae60', textTransform: 'uppercase', letterSpacing: 1, padding: '6px 16px 2px' }}>관리</li>
                  <li><a className="dropdown-item" href="/admin">누구의꿈(관리)</a></li>
                  <li><a className="dropdown-item" href="/admin/users">회원관리</a></li>
                  <li><a className="dropdown-item" href="/admin/news">소식(관리)</a></li>
                  <li><a className="dropdown-item" href="/admin/share-reports">공유(관리)</a></li>
                  <li><a className="dropdown-item" href="/admin/stores">🏪 동네가게(관리)</a></li>
                  <li><a className="dropdown-item" href="/admin/alerts">🚨 알림(관리)</a></li>
                  <li><div className="dropdown-divider"></div></li>
                  <li><a className="dropdown-item" href="/admin/ai-chat">🤖 관리자 AI</a></li>
                  <li><a className="dropdown-item" href="/admin/ai-feedback">📋 AI 피드백</a></li>
                  <li><a className="dropdown-item" href="/admin/ai-train">📚 양평AI 가르치기</a></li>
                  <li><div className="dropdown-divider"></div></li>
                  {window.location.hostname !== 'unocum.kr' && (
                    <li><a className="dropdown-item" href="/admin/page-managers">🔑 페이지관리자</a></li>
                  )}
                  <li><a className="dropdown-item" href="/admin/message/send">쪽지 발송</a></li>
                </ul>
              </li>
            )}
          </ul>
        </div>

        <div className="d-lg-none mx-auto" style={{ position: 'relative' }}>
          <form className="d-flex" action="/search" method="GET"
            onSubmit={e => { const inp = document.getElementById('mobileSearchInput') as HTMLInputElement; if (!inp.value) e.preventDefault() }}>
            <input id="mobileSearchInput" className="form-control form-control-sm" type="search" name="q" placeholder="🔍"
              style={{ width: 36, borderRadius: 20, cursor: 'pointer', transition: 'width 0.3s ease' }}
              onFocus={e => { e.currentTarget.style.width = '180px'; e.currentTarget.placeholder = '검색어 입력' }}
              onBlur={e => { if (!e.currentTarget.value) { e.currentTarget.style.width = '44px'; e.currentTarget.placeholder = '🔍' } }} />
          </form>
        </div>

        <div className="d-flex align-items-center flex-shrink-0 position-relative">
          <a href="/ai/chat" className="btn btn-sm btn-outline-success px-2 py-0"
            style={{ fontSize: '1.1rem', borderRadius: '50%', width: 34, height: 34, lineHeight: '1' }} title="양평AI">🤖</a>
          {me.id ? (
            <>
              <a href="/friends" className="text-decoration-none ms-2 d-none d-lg-inline" title="벗">👥</a>
              <a href="/message/inbox" className="text-decoration-none ms-2 d-none d-lg-inline" title="쪽지">💬</a>
              <a href={`/user/${me.id}`} className="text-decoration-none ms-2" title="회원정보">👤</a>
            </>
          ) : (
            <a href="/login" className="text-decoration-none text-muted ms-2" title="회원정보">👤</a>
          )}
          <button className="navbar-toggler ms-2" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav"
            style={{ border: 'none', padding: 0 }}>
            <span className="navbar-toggler-icon"></span>
          </button>
        </div>
      </div>
    </nav>
  )
}
