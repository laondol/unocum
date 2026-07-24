import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

interface UserOption {
  id: number; username: string; real_name?: string; town?: string; village?: string
}

export default function MessageSend() {
  const navigate = useNavigate()
  const editorRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [users, setUsers] = useState<UserOption[]>([])
  const [receiverId, setReceiverId] = useState('')
  const [subject, setSubject] = useState('')
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showDrawing, setShowDrawing] = useState(false)
  const [uploading, setUploading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const data = await fetch('/api/message/users').then(r => r.json())
      setUsers(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const execCmd = (cmd: string, val?: string) => {
    document.execCommand(cmd, false, val)
    if (editorRef.current) editorRef.current.focus()
  }

  const insertLink = () => {
    const url = prompt('링크 URL을 입력하세요:', 'https://')
    if (url) execCmd('createLink', url)
  }

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('image', file)
      const res = await fetch('/api/message/upload-image', { method: 'POST', body: fd }).then(r => r.json())
      if (res.url && editorRef.current) {
        execCmd('insertHTML', `<img src="${res.url}" style="max-width:100%;border-radius:8px;margin:8px 0" />`)
      }
    } catch {
      alert('이미지 업로드 실패')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  useEffect(() => {
    if (!showDrawing || !canvasRef.current) return
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.strokeStyle = '#000'
    ctx.lineWidth = 2
    ctx.lineCap = 'round'
    let drawing = false
    const start = (e: MouseEvent | TouchEvent) => {
      drawing = true
      const rect = canvas.getBoundingClientRect()
      const x = (e instanceof MouseEvent ? e.clientX : e.touches[0].clientX) - rect.left
      const y = (e instanceof MouseEvent ? e.clientY : e.touches[0].clientY) - rect.top
      ctx.beginPath()
      ctx.moveTo(x, y)
    }
    const move = (e: MouseEvent | TouchEvent) => {
      if (!drawing) return
      const rect = canvas.getBoundingClientRect()
      const x = (e instanceof MouseEvent ? e.clientX : e.touches[0].clientX) - rect.left
      const y = (e instanceof MouseEvent ? e.clientY : e.touches[0].clientY) - rect.top
      ctx.lineTo(x, y)
      ctx.stroke()
    }
    const end = () => { drawing = false }
    canvas.addEventListener('mousedown', start)
    canvas.addEventListener('mousemove', move)
    canvas.addEventListener('mouseup', end)
    canvas.addEventListener('mouseleave', end)
    canvas.addEventListener('touchstart', start)
    canvas.addEventListener('touchmove', move)
    canvas.addEventListener('touchend', end)
    return () => {
      canvas.removeEventListener('mousedown', start)
      canvas.removeEventListener('mousemove', move)
      canvas.removeEventListener('mouseup', end)
      canvas.removeEventListener('mouseleave', end)
      canvas.removeEventListener('touchstart', start)
      canvas.removeEventListener('touchmove', move)
      canvas.removeEventListener('touchend', end)
    }
  }, [showDrawing])

  const saveDrawing = () => {
    if (!canvasRef.current) return
    const dataUrl = canvasRef.current.toDataURL('image/png')
    fetch(dataUrl).then(r => r.blob()).then(blob => {
      const fd = new FormData()
      fd.append('image', blob, 'drawing.png')
      fetch('/api/message/upload-image', { method: 'POST', body: fd })
        .then(r => r.json())
        .then(res => {
          if (res.url) execCmd('insertHTML', `<img src="${res.url}" style="max-width:100%;border-radius:8px;margin:8px 0" />`)
        })
    })
    setShowDrawing(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const content = editorRef.current?.innerHTML || ''
    if (!receiverId || !content.trim()) return
    setSending(true); setResult('')
    try {
      const fd = new FormData()
      fd.append('receiver_id', receiverId)
      fd.append('subject', subject)
      fd.append('content', content)
      const res = await fetch('/api/message/send', { method: 'POST', body: fd }).then(r => r.json())
      if (res.status === 'success') {
        setResult('편지가 전송되었습니다.')
        setSubject(''); setReceiverId('')
        if (editorRef.current) editorRef.current.innerHTML = ''
      } else {
        setResult(res.msg || '전송 실패')
      }
    } catch { setResult('오류가 발생했습니다.') }
    finally { setSending(false) }
  }

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h3 className="fw-bold text-success">편지 보내기</h3>
        <button className="btn btn-sm btn-outline-success" onClick={() => navigate('/message/inbox')}>받은 편지</button>
      </div>

      <div className="card border-0 shadow-sm p-4" style={{ borderRadius: 18 }}>
        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label className="form-label small fw-bold">받는 사람</label>
            <select className="form-select" value={receiverId} onChange={e => setReceiverId(e.target.value)} required>
              <option value="">선택하세요</option>
              {users.map(u => (
                <option key={u.id} value={u.id}>{u.username}{u.real_name ? ` (${u.real_name})` : ''}</option>
              ))}
            </select>
          </div>
          <div className="mb-3">
            <label className="form-label small fw-bold">제목 (선택)</label>
            <input type="text" className="form-control" value={subject} onChange={e => setSubject(e.target.value)} placeholder="편지 제목" />
          </div>
          <div className="mb-3">
            <label className="form-label small fw-bold">내용</label>
            <div className="border rounded mb-2" style={{ overflow: 'hidden' }}>
              <div className="d-flex flex-wrap gap-1 p-2 bg-light border-bottom">
                <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => execCmd('bold')} title="굵게"><b>B</b></button>
                <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => execCmd('italic')} title="기울임"><i>I</i></button>
                <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => execCmd('underline')} title="밑줄"><u>U</u></button>
                <span className="border-start mx-1"></span>
                <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => execCmd('insertUnorderedList')} title="목록">☰</button>
                <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => execCmd('insertOrderedList')} title="번호 목록">#</button>
                <span className="border-start mx-1"></span>
                <button type="button" className="btn btn-sm btn-outline-secondary" onClick={insertLink} title="링크">🔗</button>
                <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => { if (fileInputRef.current) fileInputRef.current.click() }} title="사진 넣기">
                  {uploading ? '⏳' : '📷'}
                </button>
                <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => setShowDrawing(true)} title="그리기">✏️</button>
              </div>
              <input ref={fileInputRef} type="file" accept="image/*" className="d-none" onChange={handleImageUpload} />
              <div
                ref={editorRef}
                contentEditable
                suppressContentEditableWarning
                className="form-control"
                style={{ minHeight: 200, maxHeight: 400, overflowY: 'auto', border: 'none', borderRadius: 0, boxShadow: 'none' }}
              />
            </div>
          </div>
          <div className="text-muted small mb-3">편지 발송 시 10닢이 차감됩니다.</div>
          <button type="submit" className="btn btn-success w-100 fw-bold py-2" disabled={sending}>
            {sending ? '전송 중...' : '보내기 (10P)'}
          </button>
        </form>
        {result && <div className={`mt-3 small ${result.includes('✅') || result.includes('전송') ? 'text-success' : 'text-danger'}`}>{result}</div>}
      </div>

      {showDrawing && (
        <div className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center" style={{ background: 'rgba(0,0,0,0.5)', zIndex: 9999 }}>
          <div className="bg-white rounded shadow p-3" style={{ maxWidth: 550 }}>
            <h6 className="fw-bold mb-2">그림 그리기</h6>
            <canvas ref={canvasRef} width={500} height={400} className="border rounded w-100" style={{ cursor: 'crosshair', touchAction: 'none' }} />
            <div className="d-flex gap-2 mt-2">
              <button className="btn btn-sm btn-outline-secondary" onClick={() => {
                const canvas = canvasRef.current
                if (!canvas) return
                const ctx = canvas.getContext('2d')
                if (!ctx) return
                ctx.fillStyle = '#fff'
                ctx.fillRect(0, 0, canvas.width, canvas.height)
              }}>초기화</button>
              <button className="btn btn-sm btn-success" onClick={saveDrawing}>편지에 넣기</button>
              <button className="btn btn-sm btn-outline-danger" onClick={() => setShowDrawing(false)}>취소</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
