import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Loading from '../components/common/Loading'

const ALERT_TYPE_OPTIONS = [
  { value: 'general', label: '일반' },
  { value: 'construction', label: '공사' },
  { value: 'event', label: '행사' },
  { value: 'weather', label: '날씨' },
  { value: 'missing', label: '실종' },
  { value: 'disaster', label: '재난' },
  { value: 'safety', label: '안전' },
  { value: 'traffic', label: '교통' },
]

const URGENCY_OPTIONS = [
  { value: 'normal', label: '일반' },
  { value: 'urgent', label: '긴급' },
  { value: 'critical', label: '심각' },
  { value: 'important', label: '중요' },
]

export default function AdminAlertEdit() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)

  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [alertType, setAlertType] = useState('general')
  const [urgency, setUrgency] = useState('normal')
  const [town, setTown] = useState('')
  const [village, setVillage] = useState('')
  const [isActive, setIsActive] = useState(true)

  useEffect(() => {
    if (!id) return
    const load = async () => {
      try {
        const res = await fetch('/api/admin/alerts')
        if (!res.ok) throw new Error()
        const data = await res.json()
        const alert = Array.isArray(data) ? data.find((a: { id: number }) => a.id === Number(id)) : null
        if (alert) {
          setTitle(alert.title || '')
          setContent(alert.content || '')
          setAlertType(alert.alert_type || 'general')
          setUrgency(alert.urgency || 'normal')
          setTown(alert.town || '')
          setVillage(alert.village || '')
          setIsActive(alert.is_active !== false)
        }
      } catch { alert('데이터를 불러오는데 실패했습니다.') }
      finally { setLoading(false) }
    }
    load()
  }, [id])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) { alert('제목을 입력하세요.'); return }
    setSaving(true)
    try {
      const fd = new FormData()
      fd.append('title', title.trim())
      fd.append('content', content)
      fd.append('alert_type', alertType)
      fd.append('urgency', urgency)
      fd.append('town', town)
      fd.append('village', village)
      fd.append('is_active', isActive ? '1' : '0')

      const url = isEdit ? `/admin/alerts/edit/${id}` : '/admin/alerts/new'
      const res = await fetch(url, { method: 'POST', body: fd })
      if (res.ok || res.redirected) {
        navigate('/admin/alerts')
      } else {
        alert('저장 실패')
      }
    } catch { alert('저장 중 오류가 발생했습니다.') }
    finally { setSaving(false) }
  }

  if (loading) return <Loading />

  return (
    <div className="container mt-4" style={{ maxWidth: 600 }}>
      <a href="/admin/alerts" className="btn btn-sm btn-outline-secondary mb-3">← 알림 목록으로</a>
      <h3 className="fw-bold mb-4">{isEdit ? '✏️ 알림 수정' : '🚨 새 알림 등록'}</h3>

      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label className="form-label">제목 <span className="text-danger">*</span></label>
          <input type="text" className="form-control" value={title} onChange={e => setTitle(e.target.value)} required placeholder="예: OO리 실종자 발생" />
        </div>
        <div className="mb-3">
          <label className="form-label">내용</label>
          <textarea className="form-control" rows={5} value={content} onChange={e => setContent(e.target.value)} placeholder="상세 내용을 입력하세요..." />
        </div>
        <div className="row mb-3">
          <div className="col-4">
            <label className="form-label">알림 유형</label>
            <select className="form-select" value={alertType} onChange={e => setAlertType(e.target.value)}>
              {ALERT_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="col-4">
            <label className="form-label">긴급도</label>
            <select className="form-select" value={urgency} onChange={e => setUrgency(e.target.value)}>
              {URGENCY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          {isEdit && (
            <div className="col-4">
              <label className="form-label">상태</label>
              <select className="form-select" value={isActive ? '1' : '0'} onChange={e => setIsActive(e.target.value === '1')}>
                <option value="1">활성</option>
                <option value="0">비활성</option>
              </select>
            </div>
          )}
        </div>
        <div className="row mb-3">
          <div className="col-6">
            <label className="form-label">읍/면</label>
            <input type="text" className="form-control" value={town} onChange={e => setTown(e.target.value)} placeholder="예: 양평읍" />
          </div>
          <div className="col-6">
            <label className="form-label">리</label>
            <input type="text" className="form-control" value={village} onChange={e => setVillage(e.target.value)} placeholder="예: 양근리" />
          </div>
        </div>
        <div className="d-flex gap-2">
          <button type="submit" className="btn btn-danger flex-grow-1" disabled={saving}>
            {saving ? '저장 중...' : isEdit ? '저장' : '🚨 알림 등록'}
          </button>
          <a href="/admin/alerts" className="btn btn-outline-secondary">취소</a>
        </div>
      </form>
    </div>
  )
}
