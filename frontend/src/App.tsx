import { BrowserRouter, Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar'
import ShareList from './pages/ShareList'
import ShareDetail from './pages/ShareDetail'
import ShareReport from './pages/ShareReport'
import ShareEdit from './pages/ShareEdit'
import UserMyPage from './pages/UserMyPage'

export default function App() {
  const siteName = (() => {
    const host = window.location.hostname
    if (host === 'localhost' || host === '127.0.0.1') return '함께사는로컬'
    if (host === 'test.unocum.kr') return '함께사는테스트'
    return '함께사는양평'
  })()
  return (
    <BrowserRouter>
      <NavBar />
      <div className="container pb-5">
        <Routes>
          <Route path="/share" element={<ShareList />} />
          <Route path="/share/detail/:id" element={<ShareDetail />} />
          <Route path="/share/report" element={<ShareReport />} />
          <Route path="/share/edit/:id" element={<ShareEdit />} />
          <Route path="/user/my" element={<UserMyPage />} />
          <Route path="*" element={<ShareList />} />
        </Routes>
      </div>
      <footer className="text-center py-4 border-top" style={{ background: '#f8f9fa' }}>
        <span className="fw-bold text-success">{siteName}</span>
        <span className="text-muted mx-2">|</span>
        <a href="mailto:unocumyp@gmail.com" className="text-muted text-decoration-none small">unocumyp@gmail.com</a>
      </footer>
    </BrowserRouter>
  )
}