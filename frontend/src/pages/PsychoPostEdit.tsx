import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Loading from '../components/common/Loading'

interface PostData {
  id: number
  title: string
  content: string
  author_name?: string
  status?: string
}

export default function PsychoPostEdit() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [status, setStatus] = useState('')

  useEffect(() => {
    if (!id) return
    const load = async () => {
      try {
        const res = await fetch(`/api/psycho/post/${id}`, { credentials: 'include' })
        if (!res.ok) throw new Error('불러오기 실패')
        const data: PostData = await res.json()
        setTitle(data.title || '')
        setContent(data.content || '')
        setStatus(data.status || '')
      } catch { alert('데이터를 불러오는데 실패했습니다.') }
      finally { setLoading(false) }
    }
    load()
  }, [id])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !content.trim()) { alert('제목과 내용을 입력하세요.'); return }
    setSaving(true)
    try {
      const fd = new FormData()
      fd.append('title', title.trim())
      fd.append('content', content)
      const res = await fetch(`/psycho/post/${id}/edit`, { method: 'POST', body: fd })
      if (res.ok || res.redirected) {
        navigate(`/psycho/${id}`)
      } else {
        alert('수정 실패')
      }
    } catch { alert('오류가 발생했습니다.') }
    finally { setSaving(false) }
  }

  if (loading) return <Loading />

  return (
    <div className="container py-4" style={{ maxWidth: 700 }}>
      <h4 className="fw-bold mb-3">✏️ 심리상담 수정</h4>
      <form onSubmit={handleSubmit} className="card border-0 shadow-sm p-4" style={{ borderRadius: 16 }}>
        <div className="mb-2">
          <label className="small fw-bold">제목</label>
          <input type="text" className="form-control form-control-sm" value={title} onChange={e => setTitle(e.target.value)} required />
        </div>
        <div className="mb-2">
          <label className="small fw-bold">내용</label>
          <textarea className="form-control" rows={8} value={content} onChange={e => setContent(e.target.value)} required />
        </div>
        {status === 'flagged' && (
          <div className="alert alert-warning small mb-2">AI가 부적절한 내용을 감지했습니다. 수정 후 다시 검토됩니다.</div>
        )}
        <button type="submit" className="btn btn-success w-100" disabled={saving}>
          {saving ? '저장 중...' : '수정 완료'}
        </button>
      </form>
      <div className="text-center mt-3">
        <a href={`/psycho/${id}`} className="btn btn-sm btn-outline-secondary">← 돌아가기</a>
      </div>
    </div>
  )
}
