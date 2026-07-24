import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Loading from '../components/common/Loading'

const CATEGORIES = ['세계뉴스', '대한민국뉴스', '양평소식', '지역소식', '정책정보', '농업정보', '관광소식', '환경뉴스', '복지정보', '건강정보']

export default function AdminNewsEdit() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)

  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')
  const [content, setContent] = useState('')
  const [sourceUrl, setSourceUrl] = useState('')
  const [sourceName, setSourceName] = useState('')
  const [category, setCategory] = useState('세계뉴스')
  const [aiReason, setAiReason] = useState('')
  const [isSelected, setIsSelected] = useState(false)
  const [image, setImage] = useState<File | null>(null)
  const [existingImage, setExistingImage] = useState('')
  const [translating, setTranslating] = useState(false)

  useEffect(() => {
    if (!id) return
    const fetchData = async () => {
      try {
        const res = await fetch(`/admin/news/edit/${id}`)
        if (!res.ok) throw new Error('불러오기 실패')
        const text = await res.text()
        const parser = new DOMParser()
        const doc = parser.parseFromString(text, 'text/html')
        const getVal = (name: string) => {
          const el = doc.querySelector<HTMLInputElement | HTMLTextAreaElement>(`[name="${name}"]`)
          return el?.value ?? ''
        }
        const getChecked = (name: string) => {
          const el = doc.querySelector<HTMLInputElement>(`[name="${name}"]`)
          return el?.checked ?? false
        }
        setTitle(getVal('title'))
        setSummary(getVal('summary'))
        setContent(getVal('content'))
        setSourceUrl(getVal('source_url'))
        setSourceName(getVal('source_name'))
        setCategory(getVal('category') || '세계뉴스')
        setAiReason(getVal('ai_reason'))
        setIsSelected(getChecked('is_selected'))
        const imgEl = doc.querySelector<HTMLImageElement>('img[src*="uploads/news"]')
        if (imgEl) setExistingImage(imgEl.src)
      } catch {
        alert('데이터를 불러오는데 실패했습니다.')
      } finally { setLoading(false) }
    }
    fetchData()
  }, [id])

  const handleTranslate = async () => {
    if (!sourceUrl) { alert('번역할 원본 URL이 없습니다.'); return }
    setTranslating(true)
    try {
      const res = await fetch(`/admin/news/edit/${id}?translate=1`)
      const text = await res.text()
      const parser = new DOMParser()
      const doc = parser.parseFromString(text, 'text/html')
      const translatedEl = doc.querySelector<HTMLTextAreaElement>('[name="content"]')
      if (translatedEl && translatedEl.value) {
        setContent(translatedEl.value)
      } else {
        alert('번역 결과를 가져올 수 없습니다.')
      }
    } catch { alert('번역 중 오류가 발생했습니다.') }
    finally { setTranslating(false) }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) { alert('제목을 입력하세요.'); return }
    setSaving(true)
    try {
      const fd = new FormData()
      fd.append('title', title.trim())
      fd.append('summary', summary)
      fd.append('content', content)
      fd.append('source_url', sourceUrl)
      fd.append('source_name', sourceName)
      fd.append('category', category)
      fd.append('ai_reason', aiReason)
      if (isSelected) fd.append('is_selected', 'on')
      if (image) fd.append('image', image)

      const url = isEdit ? `/admin/news/edit/${id}` : '/admin/news/create'
      const res = await fetch(url, { method: 'POST', body: fd })
      if (!res.ok) throw new Error('저장 실패')
      navigate('/admin/news')
    } catch { alert('저장 중 오류가 발생했습니다.') }
    finally { setSaving(false) }
  }

  if (loading) return <Loading />

  return (
    <div className="container mt-4" style={{ maxWidth: 900 }}>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h4 className="fw-bold mb-0">{isEdit ? '✏️ 뉴스 수정' : '📝 새 뉴스 작성'}</h4>
        <a href="/admin/news" className="btn btn-outline-secondary btn-sm">← 목록</a>
      </div>

      <form onSubmit={handleSubmit} className="card border-0 shadow-sm p-4">
        <div className="mb-3">
          <label className="form-label fw-bold">제목 *</label>
          <input type="text" className="form-control form-control-lg" value={title} onChange={e => setTitle(e.target.value)} required placeholder="뉴스 제목" />
        </div>

        <div className="row mb-3">
          <div className="col-md-6">
            <label className="form-label fw-bold">분류</label>
            <select className="form-select" value={category} onChange={e => setCategory(e.target.value)}>
              {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="col-md-6">
            <label className="form-label fw-bold">출처</label>
            <input type="text" className="form-control" value={sourceName} onChange={e => setSourceName(e.target.value)} placeholder="뉴스 출처명" />
          </div>
        </div>

        <div className="mb-3">
          <label className="form-label fw-bold">AI 선정 이유</label>
          <textarea className="form-control" rows={2} value={aiReason} onChange={e => setAiReason(e.target.value)} placeholder="AI가 이 뉴스를 선정한 이유" />
        </div>

        <div className="mb-3">
          <label className="form-label fw-bold">요약</label>
          <textarea className="form-control" rows={3} value={summary} onChange={e => setSummary(e.target.value)} placeholder="3줄 요약" />
        </div>

        <div className="mb-3">
          <div className="d-flex justify-content-between align-items-center">
            <label className="form-label fw-bold mb-0">본문 (HTML 지원)</label>
            {isEdit && sourceUrl && (
              <button type="button" className="btn btn-sm btn-outline-info" onClick={handleTranslate} disabled={translating}>
                {translating ? '⏳ 번역 중...' : '🌐 원문 번역하기'}
              </button>
            )}
          </div>
          <textarea className="form-control" rows={12} value={content} onChange={e => setContent(e.target.value)} placeholder="본문 내용을 입력하세요." />
        </div>

        <div className="row mb-3">
          <div className="col-md-6">
            <label className="form-label fw-bold">대표 이미지</label>
            <input type="file" className="form-control" accept="image/*" onChange={e => setImage(e.target.files?.[0] || null)} />
            {existingImage && (
              <div className="mt-2">
                <img src={existingImage} style={{ maxHeight: 100 }} className="rounded" alt="" />
                <span className="text-muted small ms-2">기존 이미지</span>
              </div>
            )}
          </div>
          <div className="col-md-6">
            <label className="form-label fw-bold">원본 URL</label>
            <input type="url" className="form-control" value={sourceUrl} onChange={e => setSourceUrl(e.target.value)} placeholder="https://..." />
          </div>
        </div>

        <div className="form-check mb-4">
          <input type="checkbox" className="form-check-input" id="chkSelect" checked={isSelected} onChange={e => setIsSelected(e.target.checked)} />
          <label className="form-check-label fw-bold" htmlFor="chkSelect">✅ intro 페이지에 표시</label>
        </div>

        <div className="d-flex gap-2">
          <button type="submit" className="btn btn-success px-5 py-2 fw-bold" disabled={saving}>
            {saving ? '저장 중...' : isEdit ? '수정 완료' : '등록하기'}
          </button>
          <a href="/admin/news" className="btn btn-outline-secondary px-4 py-2">취소</a>
        </div>
      </form>
    </div>
  )
}
