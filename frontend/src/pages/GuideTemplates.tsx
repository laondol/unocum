import { useEffect, useState } from 'react'

interface Template {
  id: number; name: string; description: string; html_content: string
  layout_type: string; preview_image: string; is_featured: boolean
  use_count: number; style_guide: any
}

export default function GuideTemplates() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [preview, setPreview] = useState<Template | null>(null)

  useEffect(() => {
    fetch('/api/guide/templates').then(r => r.json()).then(d => { setTemplates(d); setLoading(false) })
  }, [])

  const layoutLabel: Record<string, string> = { card: '카드형', guidebook: '가이드북', journal: '수기형', hero: '히어로형', steps: '단계형' }

  if (loading) return <div className="text-center py-5"><div className="spinner-border text-success" /></div>

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '16px' }}>
      <div className="text-center mb-4">
        <h3 className="fw-bold" style={{ color: '#2c5f2d' }}>템플릿 라이브러리</h3>
        <p className="text-muted small">좋은 레이아웃을 템플릿으로 저장하고 재사용하세요.</p>
      </div>

      {templates.length === 0 ? (
        <div className="text-center py-5 text-muted">
          <p>아직 템플릿이 없습니다.</p>
        </div>
      ) : (
        <div className="row g-3">
          {templates.map(t => (
            <div key={t.id} className="col-12 col-md-6">
              <div
                className="card border-0 shadow-sm h-100"
                style={{ borderRadius: 14, cursor: 'pointer', transition: 'transform 0.2s' }}
                onMouseEnter={e => (e.currentTarget.style.transform = 'translateY(-3px)')}
                onMouseLeave={e => (e.currentTarget.style.transform = 'translateY(0)')}
                onClick={() => setPreview(t)}
              >
                {t.preview_image && (
                  <img src={t.preview_image} style={{ width: '100%', height: 160, objectFit: 'cover', borderRadius: '14px 14px 0 0' }} />
                )}
                <div className="card-body p-3">
                  <div className="d-flex align-items-center gap-2 mb-1">
                    <span className="badge bg-success" style={{ fontSize: '0.6rem' }}>{layoutLabel[t.layout_type] || t.layout_type}</span>
                    {t.is_featured && <span className="badge bg-warning text-dark" style={{ fontSize: '0.6rem' }}>추천</span>}
                    <small className="text-muted ms-auto" style={{ fontSize: 10 }}>사용 {t.use_count}회</small>
                  </div>
                  <h6 className="fw-bold mb-1">{t.name}</h6>
                  <small className="text-muted">{t.description}</small>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {preview && (
        <div
          className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center"
          style={{ background: 'rgba(0,0,0,0.5)', zIndex: 9999 }}
          onClick={() => setPreview(null)}
        >
          <div
            className="bg-white shadow-lg"
            style={{ borderRadius: 16, maxWidth: 700, width: '90%', maxHeight: '85vh', overflow: 'auto' }}
            onClick={e => e.stopPropagation()}
          >
            <div className="d-flex justify-content-between align-items-center p-3 border-bottom">
              <h5 className="fw-bold mb-0">{preview.name}</h5>
              <button className="btn btn-sm btn-outline-secondary" onClick={() => setPreview(null)}>✕</button>
            </div>
            <div className="p-3">
              <div dangerouslySetInnerHTML={{ __html: preview.html_content }} />
            </div>
            <div className="p-3 border-top d-flex justify-content-end gap-2">
              <button className="btn btn-outline-success btn-sm" onClick={() => {
                navigator.clipboard.writeText(preview.html_content)
                alert('HTML이 복사되었습니다.')
              }}>HTML 복사</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
