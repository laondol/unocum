import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

export default function VillageEventCreatePage() {
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [eventType, setEventType] = useState('meeting')
  const [title, setTitle] = useState('')
  const [eventDate, setEventDate] = useState('')
  const [location, setLocation] = useState('')
  const [videoUrl, setVideoUrl] = useState('')
  const [description, setDescription] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')

  const managed = user?.managed_pages ?? []
  const hasAccess = managed.some(p => p.startsWith('village') || p.startsWith('vi_'))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !eventDate) return
    setSending(true); setError('')
    try {
      const fd = new FormData()
      fd.append('event_type', eventType)
      fd.append('title', title.trim())
      fd.append('event_date', eventDate)
      fd.append('location', location)
      fd.append('video_url', videoUrl)
      fd.append('description', description)
      const res = await api.upload<{ id: number; status: string }>('/village/event/create', fd)
      if (res.id) navigate(`/village/events/${res.id}`)
      else if (res.status === 'success') navigate('/village/events')
      else setError(res.status || '등록 실패')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '등록 중 오류가 발생했습니다.')
    } finally { setSending(false) }
  }

  if (authLoading) return <Loading />
  if (!hasAccess) return <ErrorMessage message="접근 권한이 없습니다." />

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <h4 className="fw-bold mb-3">새 활동 만들기</h4>
      {error && <ErrorMessage message={error} />}
      <form onSubmit={handleSubmit} className="card border-0 shadow-sm p-4" style={{ borderRadius: 16 }}>
        <div className="mb-3">
          <label className="small fw-bold">유형</label>
          <select className="form-select" value={eventType} onChange={e => setEventType(e.target.value)}>
            <option value="meeting">모임</option>
            <option value="activity">활동</option>
          </select>
        </div>
        <div className="mb-3">
          <label className="small fw-bold">제목</label>
          <input type="text" className="form-control" value={title} onChange={e => setTitle(e.target.value)} required />
        </div>
        <div className="mb-3">
          <label className="small fw-bold">일시</label>
          <input type="datetime-local" className="form-control" value={eventDate} onChange={e => setEventDate(e.target.value)} required />
        </div>
        <div className="mb-3">
          <label className="small fw-bold">장소</label>
          <input type="text" className="form-control" value={location} onChange={e => setLocation(e.target.value)} />
        </div>
        <div className="mb-3">
          <label className="small fw-bold">비디오 URL</label>
          <input type="url" className="form-control" value={videoUrl} onChange={e => setVideoUrl(e.target.value)} placeholder="https://..." />
        </div>
        <div className="mb-3">
          <label className="small fw-bold">설명</label>
          <textarea className="form-control" rows={4} value={description} onChange={e => setDescription(e.target.value)} />
        </div>
        <button type="submit" className="btn btn-success w-100" disabled={sending}>
          {sending ? '등록 중...' : '등록'}
        </button>
        <button type="button" className="btn btn-sm btn-outline-secondary w-100 mt-2" onClick={() => navigate('/village/events')}>
          취소
        </button>
      </form>
    </div>
  )
}
