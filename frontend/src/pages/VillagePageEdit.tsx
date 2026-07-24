import { useState, useEffect } from 'react'
import Loading from '../components/common/Loading'

const TEMPLATES = [
  { id: 'basic', label: '📄 기본', content: '<h2>안녕하세요!</h2><p>우리 마을에 오신 것을 환영합니다.</p><p>[gallery]</p><p>[stores]</p><p>[posts]</p>' },
  { id: 'gallery', label: '🖼️ 갤러리', content: '<h2>우리 마을 갤러리</h2><p>마을의 아름다운 모습을 공유해 주세요.</p><p>[gallery]</p>' },
  { id: 'news', label: '📰 소식', content: '<h2>마을 소식</h2><p>[posts]</p><p>[gallery]</p><p>[stores]</p>' },
  { id: 'store', label: '🏪 동네가게', content: '<h2>우리 동네 가게</h2><p>마을의 맛집과 가게들을 소개합니다.</p><p>[stores]</p><p>[gallery]</p>' },
]

export default function VillagePageEdit() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [visibility, setVisibility] = useState('members')

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch('/village/page')
        if (!res.ok) throw new Error()
        const text = await res.text()
        const parser = new DOMParser()
        const doc = parser.parseFromString(text, 'text/html')
        const getVal = (name: string) => {
          const el = doc.querySelector<HTMLInputElement | HTMLTextAreaElement>(`[name="${name}"]`)
          return el?.value ?? ''
        }
        const titleVal = getVal('title')
        const contentVal = getVal('content')
        if (titleVal) setTitle(titleVal)
        if (contentVal) setContent(contentVal)
        const visEl = doc.querySelector<HTMLSelectElement>('[name="visibility"]')
        if (visEl) setVisibility(visEl.value)
      } catch { /* use defaults */ }
      finally { setLoading(false) }
    }
    load()
  }, [])

  const applyTemplate = (tmpl: typeof TEMPLATES[0]) => {
    if (!confirm('템플릿을 적용하면 현재 내용이 지워집니다. 계속할까요?')) return
    setContent(tmpl.content)
  }

  const insertShortcode = (code: string) => {
    setContent(prev => prev + `[${code}]`)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const fd = new FormData()
      fd.append('title', title)
      fd.append('content', content)
      fd.append('visibility', visibility)
      const res = await fetch('/village/page', { method: 'POST', body: fd })
      if (res.ok) {
        alert('저장되었습니다.')
      } else {
        alert('저장에 실패했습니다.')
      }
    } catch { alert('오류가 발생했습니다.') }
    finally { setSaving(false) }
  }

  if (loading) return <Loading />

  return (
    <div className="container py-4" style={{ maxWidth: 900 }}>
      <h4 className="fw-bold mb-3">
        <a className="text-dark text-decoration-none" href="/village">❤️ 봉사</a> | <a className="text-dark text-decoration-none" href="/village/page">📖 마을 홍보</a>
      </h4>

      <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: 16 }}>
        <div className="card-body p-3">
          <h6 className="fw-bold mb-2">🎨 템플릿 선택</h6>
          <div className="d-flex gap-2 flex-wrap">
            {TEMPLATES.map(t => (
              <button key={t.id} type="button" className="btn btn-sm btn-outline-success" onClick={() => applyTemplate(t)}>
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label small fw-bold">페이지 제목</label>
              <input type="text" className="form-control" value={title} onChange={e => setTitle(e.target.value)} />
            </div>

            <div className="d-flex gap-1 mb-2 flex-wrap">
              <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => insertShortcode('gallery')}>📸 [갤러리]</button>
              <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => insertShortcode('stores')}>🏪 [동네가게]</button>
              <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => insertShortcode('posts')}>📝 [마을글]</button>
            </div>

            <div className="mb-3">
              <textarea className="form-control" rows={12} value={content} onChange={e => setContent(e.target.value)} placeholder="마을 소식, 공지, 행사 등을 작성하세요..." />
            </div>

            <div className="mb-3">
              <label className="form-label small fw-bold">공개 설정</label>
              <select className="form-select" style={{ width: 'auto' }} value={visibility} onChange={e => setVisibility(e.target.value)}>
                <option value="off">🔒 비공개</option>
                <option value="members">👥 마을주민만</option>
                <option value="public">🌐 전체공개</option>
              </select>
            </div>

            <button type="submit" className="btn btn-success" disabled={saving}>
              {saving ? '저장 중...' : '저장'}
            </button>
            <a href="/village" className="btn btn-outline-secondary ms-2">← 마을지기</a>
          </form>
        </div>
      </div>
    </div>
  )
}
