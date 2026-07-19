import { useEffect, useState } from 'react'

interface GuideSection {
  id: number; title: string; content: string; icon: string; order_index: number
  layout_type: string; children: GuideSection[]
}

export default function GuideList() {
  const [sections, setSections] = useState<GuideSection[]>([])
  const [expanded, setExpanded] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/guide/sections').then(r => r.json()).then(d => { setSections(d); setLoading(false) })
  }, [])

  if (loading) return <div className="text-center py-5"><div className="spinner-border text-success" /></div>

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '16px' }}>
      <div className="text-center mb-4">
        <h3 className="fw-bold" style={{ color: '#2c5f2d' }}>이용 안내</h3>
        <p className="text-muted small">함께사는양평의 모든 기능을 안내해 드립니다.</p>
      </div>

      {sections.map((s, i) => (
        <div key={s.id} className="card border-0 shadow-sm mb-3" style={{ borderRadius: 16, overflow: 'hidden' }}>
          <div
            className="card-body p-0"
            style={{ cursor: 'pointer' }}
            onClick={() => setExpanded(expanded === s.id ? null : s.id)}
          >
            <div className="d-flex align-items-center p-3 gap-3">
              <div style={{
                width: 48, height: 48, borderRadius: 14,
                background: `linear-gradient(135deg, ${i % 2 === 0 ? '#2c5f2d' : '#27ae60'}, ${i % 2 === 0 ? '#97bc62' : '#2ecc71'})`,
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, flexShrink: 0
              }}>
                {s.icon}
              </div>
              <div className="flex-grow-1">
                <h6 className="fw-bold mb-0">{s.title}</h6>
                {expanded !== s.id && (
                  <small className="text-muted" style={{ fontSize: 12 }}>
                    {s.content.replace(/<[^>]*>/g, '').substring(0, 60)}...
                  </small>
                )}
              </div>
              <span style={{
                transition: 'transform 0.2s',
                transform: expanded === s.id ? 'rotate(180deg)' : 'rotate(0)',
                fontSize: 14, color: '#999'
              }}>▼</span>
            </div>
          </div>

          {expanded === s.id && (
            <div className="px-3 pb-3" style={{ animation: 'fadeIn 0.3s ease' }}>
              <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 16 }}>
                <div dangerouslySetInnerHTML={{ __html: s.content }} style={{ lineHeight: 1.8, fontSize: 15 }} />
                {s.children && s.children.length > 0 && (
                  <div className="mt-3">
                    {s.children.map((c: GuideSection) => (
                      <div key={c.id} className="card border-0 mb-2" style={{ borderRadius: 10, background: '#f8f9fa' }}>
                        <div className="card-body p-3">
                          <div className="d-flex align-items-center gap-2 mb-2">
                            <span>{c.icon}</span>
                            <strong style={{ fontSize: 14 }}>{c.title}</strong>
                          </div>
                          <div dangerouslySetInnerHTML={{ __html: c.content }} style={{ fontSize: 14, lineHeight: 1.7 }} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      ))}

      <div className="text-center mt-4 mb-5">
        <div className="card border-0 shadow-sm" style={{ borderRadius: 16, background: 'linear-gradient(135deg, #f0f8f0, #e8f5e9)' }}>
          <div className="card-body p-4">
            <h6 className="fw-bold" style={{ color: '#2c5f2d' }}>더 궁금한 점이 있으신가요?</h6>
            <p className="text-muted small mb-3">이메일이나 문의하기를 통해 언제든 연락해 주세요.</p>
            <a href="mailto:unocumyp@gmail.com" className="btn btn-success btn-sm" style={{ borderRadius: 10 }}>
              문의하기
            </a>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
    </div>
  )
}
