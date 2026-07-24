import { useRef, useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

export default function MainPage() {
  const navigate = useNavigate()
  const editorRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [title, setTitle] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const [showCanvas, setShowCanvas] = useState(false)
  const drawingRef = useRef(false)

  useEffect(() => {
    if (editorRef.current && !editorRef.current.innerHTML) {
      editorRef.current.innerHTML = ''
    }
  }, [])

  const execCmd = useCallback((cmd: string) => {
    document.execCommand(cmd, false)
    editorRef.current?.focus()
  }, [])

  const handleFileClick = () => fileInputRef.current?.click()

  const toggleCanvas = () => setShowCanvas(prev => !prev)

  const clearCanvas = () => {
    const c = canvasRef.current
    if (!c) return
    const ctx = c.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, c.width, c.height)
  }

  const startDraw = () => { drawingRef.current = true }
  const stopDraw = () => {
    drawingRef.current = false
    const c = canvasRef.current
    if (!c) return
    const ctx = c.getContext('2d')
    if (!ctx) return
    ctx.beginPath()
  }

  const draw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!drawingRef.current) return
    const c = canvasRef.current
    if (!c) return
    const ctx = c.getContext('2d')
    if (!ctx) return
    const rect = c.getBoundingClientRect()
    ctx.lineWidth = 3
    ctx.lineCap = 'round'
    ctx.strokeStyle = '#333'
    ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const content = editorRef.current?.innerHTML?.trim() || ''
    if (!title.trim() || !content || content === '<br>' || submitting) return
    setSubmitting(true)

    const fd = new FormData()
    fd.append('title', title.trim())
    fd.append('content', content)
    if (fileInputRef.current?.files?.length) {
      for (const f of fileInputRef.current.files) fd.append('file', f)
    }
    const drawingData = canvasRef.current?.toDataURL('image/png')
    if (drawingData && drawingData.length > 2000) fd.append('drawing_data', drawingData)

    let success = false
    try {
      const res = await fetch('/submit', { method: 'POST', body: fd })
      const data = await res.json()
      if (data.status === 'success' || data.id) {
        success = true
      } else {
        alert(data.msg || '오류 발생')
        setSubmitting(false)
        return
      }
    } catch {
      alert('서버 연결 실패')
      setSubmitting(false)
      return
    }

    if (!success) return
    setCountdown(10)
    const iv = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(iv)
          navigate('/all-proposals')
          return 0
        }
        return prev - 1
      })
    }, 1000)
  }

  if (countdown > 0) {
    return (
      <div style={{
        position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
        background: 'rgba(255,255,255,0.98)', zIndex: 9999,
        display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
      }}>
        <div style={{
          padding: 50, border: '3px solid #27ae60', borderRadius: 30,
          background: 'white', boxShadow: '0 15px 50px rgba(0,0,0,0.15)',
          textAlign: 'center',
        }}>
          <h2 style={{ color: '#27ae60', marginBottom: 15 }}>🌳 정상적으로 등록되었습니다.</h2>
          <p style={{ color: '#666', marginBottom: 20 }}>
            소중한 양평 자치 제안 기록소로 이동합니다.
          </p>
          <div className="spinner-grow text-success" role="status" style={{ width: '3rem', height: '3rem' }} />
        </div>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <h3 className="fw-bold mb-4 text-center">💭 꿈꾸기</h3>
      <p className="text-muted text-center mb-4 small">
        양평을 위한 여러분의 아이디어를 자유롭게 기록해주세요.
      </p>

      <form onSubmit={handleSubmit}>
        <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 18 }}>
          <div className="card-body p-4">
            <div className="mb-3">
              <label className="form-label fw-bold small">제목</label>
              <input
                type="text"
                className="form-control"
                placeholder="제목을 입력해 주세요"
                value={title}
                onChange={e => setTitle(e.target.value)}
                required
                style={{ borderRadius: 12, padding: 12 }}
              />
            </div>

            <div className="mb-2">
              <div className="btn-group btn-group-sm flex-wrap">
                <button type="button" className="btn btn-outline-secondary" onClick={() => execCmd('bold')} title="굵게"><b>B</b></button>
                <button type="button" className="btn btn-outline-secondary" onClick={() => execCmd('italic')} title="기울임"><i>I</i></button>
                <button type="button" className="btn btn-outline-secondary" onClick={() => execCmd('underline')} title="밑줄"><u>U</u></button>
                <button type="button" className="btn btn-outline-secondary" onClick={() => execCmd('insertUnorderedList')} title="목록">&bull;</button>
                <button type="button" className="btn btn-outline-secondary" onClick={() => execCmd('insertOrderedList')} title="번호">1.</button>
                <button type="button" className="btn btn-outline-secondary" onClick={handleFileClick} title="사진/파일">📎</button>
                <button type="button" className="btn btn-outline-secondary" onClick={toggleCanvas} title="그리기">✏️</button>
              </div>
            </div>

            <div className="mb-3">
              <div
                ref={editorRef}
                contentEditable
                className="form-control"
                style={{
                  minHeight: 250, maxHeight: 500, overflowY: 'auto',
                  borderRadius: 12, padding: 12,
                }}
                data-placeholder="우리 공동체를 위한 소중한 제안을 적어주세요."
              />
            </div>

            <input type="file" ref={fileInputRef} className="d-none" accept="image/*,application/pdf" />

            {showCanvas && (
              <div className="mb-3">
                <canvas
                  ref={canvasRef}
                  width={400}
                  height={300}
                  style={{
                    border: '1px solid #ccc', background: 'white',
                    cursor: 'crosshair', width: '100%', borderRadius: 12,
                  }}
                  onMouseDown={startDraw}
                  onMouseUp={stopDraw}
                  onMouseMove={draw}
                  onMouseLeave={stopDraw}
                />
                <div className="mt-1">
                  <button type="button" className="btn btn-sm btn-light" onClick={clearCanvas}>지우기</button>
                </div>
              </div>
            )}

            <button
              type="submit"
              className="btn btn-success w-100 py-3 fw-bold"
              style={{ borderRadius: 12, fontSize: '1.1rem' }}
              disabled={submitting || !title.trim()}
            >
              {submitting ? '등록 중...' : '제안 제출하기'}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
