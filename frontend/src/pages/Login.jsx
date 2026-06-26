import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const nav = useNavigate()

  const handleLogin = (e) => {
    e.preventDefault()
    const fd = new FormData()
    fd.append('username', username)
    fd.append('password', password)
    fetch('/login', { method: 'POST', body: fd })
      .then(r => { if (r.redirected) nav('/') })
      .catch(() => alert('로그인 실패'))
  }

  return (
    <div className="mx-auto" style={{maxWidth:360}}>
      <h3 className="fw-bold mb-4 text-center">로그인</h3>
      <form onSubmit={handleLogin}>
        <input className="form-control mb-2" placeholder="아이디" value={username} onChange={e=>setUsername(e.target.value)} />
        <input className="form-control mb-3" type="password" placeholder="비밀번호" value={password} onChange={e=>setPassword(e.target.value)} />
        <button className="btn btn-success w-100">로그인</button>
      </form>
    </div>
  )
}
