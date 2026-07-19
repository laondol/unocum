import { useEffect, useState } from 'react'

export default function EpubList() {
  const [books, setBooks] = useState<any[]>([])
  const [templates, setTemplates] = useState<any[]>([])
  const [guideTemplates, setGuideTemplates] = useState<any[]>([])
  const [showNew, setShowNew] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newType, setNewType] = useState('newsletter')
  const [newTpl, setNewTpl] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/epub/books').then(r => r.json()).then(d => { setBooks(d); setLoading(false) })
    fetch('/api/epub/templates').then(r => r.json()).then(setTemplates)
    fetch('/api/guide/templates').then(r => r.json()).then(setGuideTemplates).catch(() => {})
  }, [])

  function createBook() {
    if (!newTitle.trim()) { alert('제목을 입력하세요'); return }
    const isGuideTpl = newTpl.startsWith('guide_')
    const guideId = isGuideTpl ? parseInt(newTpl.replace('guide_', '')) : null
    const epubId = !isGuideTpl && newTpl ? parseInt(newTpl) : null

    if (guideId) {
      fetch(`/api/guide/template/${guideId}/use`, { method: 'POST' })
        .then(r => r.json())
        .then(tplData => {
          return fetch('/api/epub/book/create', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              title: newTitle, layout_type: newType,
              initial_content: tplData.html_content,
              initial_style: tplData.style_guide,
            })
          }).then(r => r.json())
        })
        .then(d => {
          if (d.status === 'success') window.location.href = `/epub/edit/${d.id}`
          else alert(d.msg || '오류')
        })
    } else {
      fetch('/api/epub/book/create', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle, layout_type: newType, template_id: epubId || undefined })
      }).then(r => r.json()).then(d => {
        if (d.status === 'success') window.location.href = `/epub/edit/${d.id}`
        else alert(d.msg || '오류')
      })
    }
  }

  const typeLabel: Record<string, string> = { newsletter: '소식지', guidebook: '가이드북', journal: '수기' }
  const typeColor: Record<string, string> = { newsletter: 'success', guidebook: 'primary', journal: 'purple' }

  const filteredEpub = templates.filter(t => t.layout_type === newType || !newType)
  const filteredGuide = guideTemplates.filter(t => t.layout_type === newType || !newType)

  if (loading) return <div className="text-center py-5"><div className="spinner-border" /></div>

  return (
    <div className="container-fluid px-3 py-3" style={{ maxWidth: 900, margin: '0 auto' }}>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h4 className="fw-bold mb-0">EPUB 콘텐츠</h4>
        <button className="btn btn-success btn-sm" onClick={() => setShowNew(!showNew)}>
          {showNew ? '취소' : '+ 새 콘텐츠'}
        </button>
      </div>

      {showNew && (
        <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 12 }}>
          <div className="card-body p-3">
            <div className="mb-2">
              <label className="form-label small fw-bold">제목</label>
              <input type="text" className="form-control" value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="예: 7월 양평 소식지" />
            </div>
            <div className="mb-2">
              <label className="form-label small fw-bold">유형</label>
              <select className="form-select" value={newType} onChange={e => setNewType(e.target.value)}>
                <option value="newsletter">마을 소식지</option>
                <option value="guidebook">지역 가이드북</option>
                <option value="journal">체험 수기</option>
              </select>
            </div>
            <div className="mb-3">
              <label className="form-label small fw-bold">템플릿 선택</label>
              <select className="form-select" value={newTpl} onChange={e => setNewTpl(e.target.value)}>
                <option value="">템플릿 없이 시작</option>
                {filteredGuide.length > 0 && (
                  <optgroup label="가이드 템플릿">
                    {filteredGuide.map(t => (
                      <option key={`guide_${t.id}`} value={`guide_${t.id}`}>{t.name} - {t.description}</option>
                    ))}
                  </optgroup>
                )}
                {filteredEpub.length > 0 && (
                  <optgroup label="에디터 템플릿">
                    {filteredEpub.map(t => (
                      <option key={t.id} value={t.id}>{t.name} - {t.description}</option>
                    ))}
                  </optgroup>
                )}
              </select>
              {newTpl && (
                <div className="mt-1">
                  <small className="text-muted" style={{ fontSize: 11 }}>
                    {newTpl.startsWith('guide_') ? '가이드 템플릿에서 가져오기' : '에디터 템플릿 적용'}
                  </small>
                </div>
              )}
            </div>
            <button className="btn btn-success w-100" onClick={createBook}>만들기</button>
          </div>
        </div>
      )}

      {books.length === 0 ? (
        <div className="text-center py-5 text-muted">
          <div style={{ fontSize: 48 }}>EPUB</div>
          <p>아직 콘텐츠가 없습니다.</p>
          <button className="btn btn-success" onClick={() => setShowNew(true)}>첫 콘텐츠 만들기</button>
        </div>
      ) : (
        <div className="row g-3">
          {books.map(b => (
            <div key={b.id} className="col-12">
              <div className="card border-0 shadow-sm" style={{ borderRadius: 12, cursor: 'pointer' }}
                   onClick={() => window.location.href = `/epub/edit/${b.id}`}>
                <div className="card-body p-3 d-flex gap-3">
                  {b.cover_image && <img src={b.cover_image} style={{ width: 80, height: 80, objectFit: 'cover', borderRadius: 8 }} />}
                  <div className="flex-grow-1 min-w-0">
                    <div className="d-flex align-items-center gap-2 mb-1">
                      <span className={`badge bg-${typeColor[b.layout_type] || 'secondary'}`} style={{ fontSize: '0.65rem' }}>
                        {typeLabel[b.layout_type] || b.layout_type}
                      </span>
                      {b.status === 'draft' && <span className="badge bg-warning text-dark" style={{ fontSize: '0.6rem' }}>임시</span>}
                    </div>
                    <h6 className="fw-bold mb-1 text-truncate">{b.title}</h6>
                    <small className="text-muted">
                      {b.page_count}페이지 | {b.town} {b.village} | {b.updated_at || b.created_at}
                    </small>
                  </div>
                  <div className="d-flex align-items-center">
                    <span className="text-muted small">{b.author_name}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
