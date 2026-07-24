import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { legalApi } from '../lib/api'

export default function LegalWrite() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [authorName, setAuthorName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [sending, setSending] = useState(false)
  const editorRef = useRef<HTMLDivElement>(null)

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
      if (file) fd.append('attachment', file)
      const res = await legalApi.create(fd)
      if (res.status === 'success') {
        navigate('/legal')
      } else {
        alert(res.status || '등록 실패')
      }
    } catch { alert('등록 중 오류가 발생했습니다.') }
    finally { setSending(false) }
  }

  const execCmd = (cmd: string) => {
    document.execCommand(cmd, false)
    editorRef.current?.focus()
  }

  const insertLink = () => {
    const url = prompt('URL:')
    if (url) document.execCommand('createLink', false, url)
  }

  const updateContent = () => {
    if (editorRef.current) setContent(editorRef.current.innerHTML)
  }

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <h4 className="fw-bold mb-3">법률상담 작성</h4>
      <form onSubmit={handleSubmit} className="card border-0 shadow-sm p-4" style={{ borderRadius: 16 }}>
        <div className="mb-2">
          <label className="small fw-bold">이름</label>
          <input type="text" className="form-control form-control-sm" value={authorName}
            onChange={e => setAuthorName(e.target.value)} required />
        </div>
        <div className="mb-2">
          <label className="small fw-bold">이메일</label>
          <input type="email" className="form-control form-control-sm" value={email}
            onChange={e => setEmail(e.target.value)} required />
        </div>
        <div className="mb-2">
          <label className="small fw-bold">제목</label>
          <input type="text" className="form-control form-control-sm" value={title}
            onChange={e => setTitle(e.target.value)} required />
        </div>
        <div className="mb-2">
          <label className="small fw-bold mb-1">내용</label>
          <div className="d-flex gap-1 mb-1 flex-wrap">
            <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => execCmd('bold')}><b>B</b></button>
            <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => execCmd('italic')}><i>I</i></button>
            <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => execCmd('underline')}><u>U</u></button>
            <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => execCmd('insertUnorderedList')}>목록</button>
            <button type="button" className="btn btn-sm btn-outline-secondary" onClick={insertLink}>링크</button>
          </div>
          <div ref={editorRef} contentEditable
            className="form-control mb-2"
            style={{ minHeight: 200, maxHeight: 400, overflowY: 'auto' }}
            onInput={updateContent}
            onBlur={updateContent}
            data-placeholder="내용을 작성하세요..." />
        </div>
        <div className="mb-3">
          <label className="small fw-bold">파일 첨부</label>
          <input type="file" className="form-control form-control-sm" accept="image/*,.pdf,.doc,.docx,.hwp"
            onChange={e => setFile(e.target.files?.[0] || null)} />
        </div>
        <div className="mb-2">
          <label className="small fw-bold">비밀번호 (비회원시 필수)</label>
          <input type="password" className="form-control form-control-sm" value={password}
            onChange={e => setPassword(e.target.value)} placeholder="글 확인시 필요" />
        </div>
        <button type="submit" className="btn btn-success w-100" disabled={sending}>
          {sending ? '등록 중...' : '등록'}
        </button>
        <button type="button" className="btn btn-sm btn-outline-secondary w-100 mt-2"
          onClick={() => navigate('/legal')}>취소</button>
      </form>
    </div>
  )
}
