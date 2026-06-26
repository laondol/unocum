import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import api from '../api'

export default function Layout() {
  const [user, setUser] = useState(null)
  const nav = useNavigate()

  // Check login on mount
  api.get('/user/me').then(d => setUser(d.user)).catch(() => {})

  return (
    <div className="min-vh-100 bg-light">
      <nav className="navbar navbar-expand-lg bg-white shadow-sm sticky-top">
        <div className="container">
          <Link className="navbar-brand fw-bold text-success" to="/">🏡 함께사는양평</Link>
          <div className="ms-auto d-flex gap-2">
            {user ? (
              <>
                <Link to={`/user/${user.id}`} className="btn btn-sm btn-outline-secondary">👤 {user.username}</Link>
                <a href="/logout" className="btn btn-sm btn-outline-danger">로그아웃</a>
              </>
            ) : (
              <Link to="/login" className="btn btn-sm btn-success">로그인</Link>
            )}
          </div>
        </div>
      </nav>
      <main className="container pb-5 pt-3">
        <Outlet />
      </main>
    </div>
  )
}
