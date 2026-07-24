import { useState, useRef, useEffect } from 'react'

interface ChatMessage {
  role: 'user' | 'ai'
  text: string
}

function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.appendChild(document.createTextNode(text))
  return div.innerHTML
}

export default function AiChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'ai', text: '안녕하세요! 무엇을 도와드릴까요?' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    setError('')
    setMessages(prev => [...prev, { role: 'user', text }])
    setLoading(true)
    try {
      const res = await fetch('/ai/chat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })
      if (!res.ok) throw new Error('전송 실패')
      const data = await res.json()
      setMessages(prev => [...prev, { role: 'ai', text: data.reply || '응답을 받지 못했습니다.' }])
    } catch {
      setError('메시지 전송 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="d-flex flex-column" style={{ height: 'calc(100vh - 100px)', maxWidth: 700, margin: '0 auto' }}>
      <h4 className="fw-bold mb-3">AI 채팅</h4>
      <div className="card border-0 shadow-sm flex-grow-1 d-flex flex-column" style={{ borderRadius: 16, overflow: 'hidden' }}>
        <div className="flex-grow-1 p-3 overflow-auto" style={{ background: '#f8f9fa' }}>
          {messages.map((msg, i) => (
            <div key={i} className={`d-flex mb-3 ${msg.role === 'user' ? 'justify-content-end' : 'justify-content-start'}`}>
              <div
                className="px-3 py-2"
                style={{
                  maxWidth: '80%',
                  borderRadius: 16,
                  background: msg.role === 'user' ? '#198754' : '#fff',
                  color: msg.role === 'user' ? '#fff' : '#212529',
                  wordBreak: 'break-word',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {escapeHtml(msg.text)}
              </div>
            </div>
          ))}
          {loading && (
            <div className="d-flex justify-content-start mb-3">
              <div className="px-3 py-2" style={{ maxWidth: '80%', borderRadius: 16, background: '#fff', color: '#6c757d' }}>
                입력 중...
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        {error && <div className="alert alert-danger text-center small m-2 py-1 mb-0">{error}</div>}
        <div className="p-3 border-top d-flex gap-2" style={{ background: '#fff' }}>
          <input
            className="form-control"
            placeholder="메시지를 입력하세요..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button className="btn btn-success px-4" onClick={handleSend} disabled={loading || !input.trim()}>
            전송
          </button>
        </div>
      </div>
    </div>
  )
}
