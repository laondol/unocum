import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'
import EmptyState from '../components/common/EmptyState'

interface MessageItem {
  id: number; subject: string; content: string; sender_name?: string; receiver_name?: string
  sender_role?: string; letter_type?: string; is_read?: boolean; is_public?: boolean
  created_at?: string
}

export default function MessageInbox() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get('tab') || 'received'
  const [messages, setMessages] = useState<MessageItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const data = await fetch(`/api/messages?tab=${tab}`).then(r => r.json())
      setMessages(Array.isArray(data) ? data : [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [tab])

  useEffect(() => { load() }, [load])

  const markRead = async (id: number) => {
    try {
      await fetch(`/message/read/${id}`, { method: 'POST' })
      load()
    } catch { /* ignore */ }
  }

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h3 className="fw-bold text-success">편지함</h3>
        <button className="btn btn-success btn-sm" onClick={() => navigate('/message/send')}>편지 보내기</button>
      </div>

      <ul className="nav nav-tabs mb-3">
        <li className="nav-item">
          <button className={`nav-link fw-bold ${tab === 'received' ? 'active' : ''}`}
            onClick={() => setSearchParams({ tab: 'received' })}>벗으로 부터</button>
        </li>
        <li className="nav-item">
          <button className={`nav-link fw-bold ${tab === 'sent' ? 'active' : ''}`}
            onClick={() => setSearchParams({ tab: 'sent' })}>벗에게</button>
        </li>
      </ul>

      {messages.length === 0 ? (
        <EmptyState icon="📭" title={tab === 'received' ? '벗으로부터 온 편지가 없습니다.' : '벗에게 보낸 편지가 없습니다.'} />
      ) : (
        messages.map(m => (
          <div key={m.id} className="card mb-2 border-0 shadow-sm" style={{
            borderRadius: 14,
            borderLeft: !m.is_read && tab === 'received' ? '4px solid #27ae60' : undefined,
          }}>
            <div className="card-body p-3">
              <div className="d-flex justify-content-between align-items-start">
                <div>
                  <strong>{m.subject || '(제목 없음)'}</strong>
                  {!m.is_read && tab === 'received' && <span className="badge bg-success ms-1">NEW</span>}
                  {m.is_public && <span className="badge bg-warning text-dark ms-1">공개</span>}
                </div>
                <small className="text-muted">{m.created_at ? new Date(m.created_at).toLocaleString('ko-KR') : ''}</small>
              </div>
              <div className="small text-muted mb-1">
                {tab === 'received' ? m.sender_name : `→ ${m.receiver_name}`}
              </div>
              <div className="mt-2 p-2 bg-light rounded">{m.content}</div>
              {!m.is_read && tab === 'received' && (
                <div className="text-end mt-1">
                  <button className="btn btn-sm btn-outline-success" onClick={() => markRead(m.id)}>읽음</button>
                </div>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
