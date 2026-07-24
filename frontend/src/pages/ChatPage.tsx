import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { ChatRoom, ChatMessage } from '../lib/types'
import Loading from '../components/common/Loading'

interface Friend { id: number; username: string; real_name?: string }

function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.appendChild(document.createTextNode(text))
  return div.innerHTML
}

export default function ChatPage() {
  const [searchParams] = useSearchParams()
  const roomParam = searchParams.get('room')
  const actionParam = searchParams.get('action')

  const [friends, setFriends] = useState<Friend[]>([])
  const [selectedFriends, setSelectedFriends] = useState<number[]>([])
  const [rooms, setRooms] = useState<ChatRoom[]>([])
  const [activeRoom, setActiveRoom] = useState<ChatRoom | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [msgInput, setMsgInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(''); void error;
  const [createType, setCreateType] = useState<'now' | 'reserve' | null>(null)
  const [schedDate, setSchedDate] = useState('')
  const [schedTime, setSchedTime] = useState('')
  const [showFriendModal, setShowFriendModal] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const loadFriends = useCallback(async () => {
    try {
      const data = await fetch('/api/chat/friends').then(r => r.json())
      setFriends(Array.isArray(data) ? data : [])
    } catch { setError('친구 목록을 불러올 수 없습니다.') }
  }, [])

  const loadRooms = useCallback(async () => {
    try {
      const data = await fetch('/api/chat/rooms').then(r => r.json())
      setRooms(Array.isArray(data) ? data : [])
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    setLoading(true)
    Promise.all([loadFriends(), loadRooms()]).finally(() => setLoading(false))
  }, [loadFriends, loadRooms])

  useEffect(() => {
    if (roomParam && rooms.length > 0) {
      const found = rooms.find(r => String(r.id) === roomParam)
      if (found) setActiveRoom(found)
    }
  }, [roomParam, rooms])

  useEffect(() => {
    if (actionParam === 'join' && roomParam) {
      fetch(`/api/chat/rooms/${roomParam}/join`, { method: 'POST' })
        .then(r => r.json()).then(() => loadRooms()).catch(() => {})
    }
    if (actionParam === 'decline' && roomParam) {
      fetch(`/api/chat/rooms/${roomParam}/decline`, { method: 'POST' })
        .then(r => r.json()).then(() => loadRooms()).catch(() => {})
    }
    if (actionParam === 'monitor' && roomParam) {
      fetch(`/api/chat/rooms/${roomParam}/monitor`, { method: 'POST' })
        .then(r => r.json()).then(() => loadRooms()).catch(() => {})
    }
  }, [actionParam, roomParam, loadRooms])

  useEffect(() => {
    if (!activeRoom) return
    const loadMsgs = async () => {
      try {
        const data = await fetch(`/api/chat/messages/${activeRoom.id}`).then(r => r.json())
        setMessages(Array.isArray(data) ? data : [])
      } catch { /* ignore */ }
    }
    loadMsgs()
    const interval = setInterval(loadMsgs, 3000)
    return () => clearInterval(interval)
  }, [activeRoom])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleCreateRoom = async () => {
    if (selectedFriends.length === 0) return
    try {
      const body: { participant_ids: number[]; scheduled_at?: string } = { participant_ids: selectedFriends }
      if (createType === 'reserve' && schedDate && schedTime) {
        body.scheduled_at = `${schedDate}T${schedTime}`
      }
      const res = await fetch('/api/chat/rooms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (data.status === 'success' || data.id) {
        setCreateType(null)
        setSelectedFriends([])
        setSchedDate('')
        setSchedTime('')
        setShowFriendModal(false)
        loadRooms()
      } else {
        alert(data.msg || '방 생성 실패')
      }
    } catch { alert('방 생성 중 오류') }
  }

  const handleSendMessage = async () => {
    if (!msgInput.trim() || !activeRoom) return
    const text = msgInput.trim()
    setMsgInput('')
    try {
      const res = await fetch(`/api/chat/messages/${activeRoom.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })
      const data = await res.json()
      if (data.status === 'success' || data.id) {
        const msgs = await fetch(`/api/chat/messages/${activeRoom.id}`).then(r => r.json())
        setMessages(Array.isArray(msgs) ? msgs : [])
      }
    } catch { alert('메시지 전송 실패') }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const toggleFriend = (id: number) => {
    setSelectedFriends(prev => prev.includes(id) ? prev.filter(f => f !== id) : [...prev, id])
  }

  if (loading) return <Loading />

  return (
    <div className="d-flex" style={{ height: 'calc(100vh - 56px)', overflow: 'hidden' }}>
      <div className="d-flex flex-column border-end" style={{ width: 300, minWidth: 300 }}>
        <div className="p-3 border-bottom">
          <h5 className="fw-bold mb-2">채팅</h5>
          <button className="btn btn-success btn-sm w-100" onClick={() => {
            setCreateType('now')
            setShowFriendModal(true)
          }}>지금 채팅</button>
          <button className="btn btn-outline-success btn-sm w-100 mt-1" onClick={() => {
            setCreateType('reserve')
            setShowFriendModal(true)
          }}>예약 채팅</button>
        </div>
        <div className="flex-grow-1 overflow-auto">
          {rooms.length === 0 ? (
            <div className="text-center text-muted py-5 small">채팅방이 없습니다.</div>
          ) : (
            rooms.map(room => (
              <div
                key={room.id}
                className={`p-3 border-bottom ${activeRoom?.id === room.id ? 'bg-success bg-opacity-10' : ''}`}
                style={{ cursor: 'pointer' }}
                onClick={() => setActiveRoom(room)}
              >
                <div className="fw-medium small">{room.name || `채팅방 ${room.id}`}</div>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>{room.created_at || ''}</div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="flex-grow-1 d-flex flex-column">
        {activeRoom ? (
          <>
            <div className="p-3 border-bottom bg-light">
              <strong>{activeRoom.name || `채팅방 ${activeRoom.id}`}</strong>
            </div>
            <div className="flex-grow-1 p-3 overflow-auto" style={{ background: '#f8f9fa' }}>
              {messages.map((msg, i) => (
                <div key={msg.id || i} className={`d-flex mb-2 ${msg.is_bot ? 'justify-content-start' : 'justify-content-end'}`}>
                  <div
                    className="px-3 py-2"
                    style={{
                      maxWidth: '75%',
                      borderRadius: 16,
                      background: msg.is_bot ? '#fff' : '#198754',
                      color: msg.is_bot ? '#212529' : '#fff',
                      wordBreak: 'break-word',
                    }}
                  >
                    {msg.username && <div className="small fw-bold">{msg.username}</div>}
                    <div>{escapeHtml(msg.message || '')}</div>
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
            <div className="p-3 border-top d-flex gap-2" style={{ background: '#fff' }}>
              <input
                className="form-control"
                placeholder="메시지를 입력하세요..."
                value={msgInput}
                onChange={e => setMsgInput(e.target.value)}
                onKeyDown={handleKeyDown}
              />
              <button className="btn btn-success px-4" onClick={handleSendMessage} disabled={!msgInput.trim()}>전송</button>
            </div>
          </>
        ) : (
          <div className="flex-grow-1 d-flex align-items-center justify-content-center text-muted">
            채팅방을 선택하세요
          </div>
        )}
      </div>

      {showFriendModal && (
        <div className="modal fade show d-block" tabIndex={-1} style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content" style={{ borderRadius: 16 }}>
              <div className="modal-header">
                <h5 className="fw-bold">{createType === 'reserve' ? '예약 채팅' : '지금 채팅'}</h5>
                <button type="button" className="btn-close" onClick={() => { setShowFriendModal(false); setCreateType(null) }} />
              </div>
              <div className="modal-body">
                {friends.length === 0 ? (
                  <p className="text-muted small text-center">친구가 없습니다.</p>
                ) : (
                  <div className="mb-3">
                    {friends.map(f => (
                      <div key={f.id} className="form-check mb-1">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id={`friend-${f.id}`}
                          checked={selectedFriends.includes(f.id)}
                          onChange={() => toggleFriend(f.id)}
                        />
                        <label className="form-check-label" htmlFor={`friend-${f.id}`}>
                          {f.real_name || f.username}
                        </label>
                      </div>
                    ))}
                  </div>
                )}
                {createType === 'reserve' && (
                  <div className="d-flex gap-2 mb-2">
                    <input type="date" className="form-control form-control-sm" value={schedDate} onChange={e => setSchedDate(e.target.value)} />
                    <input type="time" className="form-control form-control-sm" value={schedTime} onChange={e => setSchedTime(e.target.value)} />
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button className="btn btn-sm btn-secondary" onClick={() => { setShowFriendModal(false); setCreateType(null) }}>취소</button>
                <button className="btn btn-sm btn-success" onClick={handleCreateRoom} disabled={selectedFriends.length === 0}>
                  {createType === 'reserve' ? '예약 생성' : '채팅 시작'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
