import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { psychoApi } from '../lib/api'

export default function PsychoWrite() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [authorName, setAuthorName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [sending, setSending] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !content.trim()) return
    setSending(true)
    try {
      const fd = new FormData()
      fd.append('title', title.trim())
      fd.append('content', content)
      fd.append('author_name', authorName)
      fd.append('email', email)
      if (password) fd.append('password', password)
      const res = await psychoApi.create(fd)
      if (res.status === 'success') {
        navigate('/psycho')
      } else {
        alert(res.status || '등록 실패')
      }
    } catch { alert('등록 중 오류가 발생했습니다.') }
    finally { setSending(false) }
  }

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <h4 className="fw-bold mb-3">심리상담 글쓰기</h4>
      <form onSubmit={handleSubmit}>
        <div className="card border-0 shadow-sm p-4" style={{ borderRadius: 16 }}>
          <div className="mb-3">
            <label className="form-label small fw-bold">제목</label>
            <input type="text" className="form-control" value={title} onChange={e => setTitle(e.target.value)} required />
          </div>
          <div className="mb-3">
            <label className="form-label small fw-bold">상담 내용</label>
            <textarea className="form-control" rows={8} value={content} onChange={e => setContent(e.target.value)} required />
          </div>
          <div className="row g-2 mb-3">
            <div className="col-4">
              <label className="form-label small fw-bold">작성자</label>
              <input type="text" className="form-control" value={authorName} onChange={e => setAuthorName(e.target.value)} required />
            </div>
            <div className="col-4">
              <label className="form-label small fw-bold">이메일</label>
              <input type="email" className="form-control" value={email} onChange={e => setEmail(e.target.value)} required />
            </div>
            <div className="col-4">
              <label className="form-label small fw-bold">비밀번호</label>
              <input type="password" className="form-control" value={password} onChange={e => setPassword(e.target.value)}
                placeholder={password ? '' : '회원은 불필요'} />
            </div>
          </div>
          <div className="alert alert-warning py-2 mb-3 small">상담 내용 및 방식에 따라 상담비가 발생할 수 있습니다. 답변 시 안내해 드립니다.</div>
          <button type="submit" className="btn btn-success w-100 py-2 fw-bold" disabled={sending}>
            {sending ? '등록 중...' : '등록하기'}
          </button>
        </div>
      </form>
      <div className="text-center mt-3">
        <button className="btn btn-sm btn-outline-secondary" onClick={() => navigate('/psycho')}>← 목록</button>
      </div>
    </div>
  )
}
