import { useEffect, useState, useRef } from 'react'

interface Media { id: number; file_path: string; latitude: number | null; longitude: number | null; caption: string; order_index: number }
interface Page { id: number; title: string; content: string; order_index: number; latitude: number | null; longitude: number | null; media: Media[] }

export default function EpubEditor() {
  const id = window.location.pathname.split('/').filter(Boolean).pop()
  const [book, setBook] = useState<any>(null)
  const [pages, setPages] = useState<Page[]>([])
  const [selectedPage, setSelectedPage] = useState<number>(0)
  const [template, setTemplate] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [leafletReady, setLeafletReady] = useState(false)
  const [guideTemplates, setGuideTemplates] = useState<any[]>([])
  const [showTemplateModal, setShowTemplateModal] = useState(false)
  const [imgFloat, setImgFloat] = useState<'left' | 'right'>('left')
  const [showKeywordInput, setShowKeywordInput] = useState(false)
  const [pendingImageUrl, setPendingImageUrl] = useState('')
  const [pendingKeyword, setPendingKeyword] = useState('')
  const [showLinkModal, setShowLinkModal] = useState(false)
  const [linkText, setLinkText] = useState('')
  const [linkUrl, setLinkUrl] = useState('')
  const [showPhotoEdit, setShowPhotoEdit] = useState(false)
  const [editImageSrc, setEditImageSrc] = useState('')
  const [editImageAction, setEditImageAction] = useState<'crop' | 'rotate' | 'watermark'>('crop')
  const [rotateDeg, setRotateDeg] = useState(0)
  const [watermarkText, setWatermarkText] = useState('함께사는양평')
  const [watermarkPos, setWatermarkPos] = useState('bottom-right')
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<any>(null)
  const markersRef = useRef<any[]>([])
  const editorRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const photoEditInputRef = useRef<HTMLInputElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const currentPage = pages[selectedPage]

  useEffect(() => {
    fetch(`/api/epub/book/${id}`).then(r => r.json()).then(d => {
      setBook(d)
      setPages(d.pages || [])
      setTemplate(d.template || null)
      setLoading(false)
    })
    fetch('/api/guide/templates').then(r => r.json()).then(setGuideTemplates).catch(() => {})
  }, [id])

  useEffect(() => {
    if (!leafletReady || !mapRef.current || !currentPage) return
    const L = (window as any).L
    if (!L) return

    if (mapInstanceRef.current) { mapInstanceRef.current.remove(); mapInstanceRef.current = null }
    const lat = currentPage.latitude || 37.5665
    const lon = currentPage.longitude || 126.978
    mapInstanceRef.current = L.map(mapRef.current).setView([lat, lon], 14)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(mapInstanceRef.current)

    markersRef.current.forEach(m => m.remove())
    markersRef.current = []

    if (currentPage.latitude && currentPage.longitude) {
      const m = L.marker([currentPage.latitude, currentPage.longitude]).addTo(mapInstanceRef.current)
      markersRef.current.push(m)
    }
    currentPage.media.forEach(med => {
      if (med.latitude && med.longitude) {
        const mk = L.marker([med.latitude, med.longitude], { icon: L.divIcon({ className: '', html: `<img src="${med.file_path}" style="width:32px;height:32px;border-radius:6px;border:2px solid white;object-fit:cover;" />` }) }).addTo(mapInstanceRef.current)
        markersRef.current.push(mk)
      }
    })
    setTimeout(() => mapInstanceRef.current?.invalidateSize(), 200)
  }, [leafletReady, selectedPage, pages])

  useEffect(() => {
    if (document.getElementById('leaflet-css')) { setLeafletReady(true); return }
    const link = document.createElement('link'); link.id = 'leaflet-css'; link.rel = 'stylesheet'; link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'; document.head.appendChild(link)
    const script = document.createElement('script'); script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'; script.onload = () => setLeafletReady(true); document.head.appendChild(script)
  }, [])

  function updatePage(idx: number, field: string, value: any) {
    setPages(prev => {
      const next = [...prev]
      next[idx] = { ...next[idx], [field]: value }
      return next
    })
  }

  function savePage(idx: number) {
    const p = pages[idx]
    setSaving(true)
    fetch(`/api/epub/page/${p.id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: p.title, content: p.content, latitude: p.latitude, longitude: p.longitude })
    }).then(r => r.json()).then(d => { setSaving(false); if (d.status !== 'success') alert(d.msg || '저장 실패') })
  }

  function addPage() {
    fetch('/api/epub/page/add', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ book_id: parseInt(id || '0'), title: '새 섹션', content: '' })
    }).then(r => r.json()).then(d => {
      if (d.status === 'success') {
        setPages(prev => [...prev, { id: d.id, title: '새 섹션', content: '', order_index: prev.length, latitude: null, longitude: null, media: [] }])
        setSelectedPage(pages.length)
      }
    })
  }

  function addPageFromTemplate(tpl: any) {
    fetch('/api/epub/page/add', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ book_id: parseInt(id || '0'), title: tpl.name, content: tpl.html_content })
    }).then(r => r.json()).then(d => {
      if (d.status === 'success') {
        setPages(prev => [...prev, { id: d.id, title: tpl.name, content: tpl.html_content, order_index: prev.length, latitude: null, longitude: null, media: [] }])
        setSelectedPage(pages.length)
        setShowTemplateModal(false)
      }
    })
  }

  function deletePage(idx: number) {
    if (!confirm('이 섹션을 삭제하시겠습니까?')) return
    const p = pages[idx]
    fetch(`/api/epub/page/${p.id}`, { method: 'DELETE' }).then(r => r.json()).then(d => {
      if (d.status === 'success') {
        setPages(prev => prev.filter((_, i) => i !== idx))
        setSelectedPage(Math.max(0, idx - 1))
      }
    })
  }

  function insertImageAtKeyword(imageUrl: string, keyword: string, floatSide: 'left' | 'right') {
    if (!editorRef.current || !keyword.trim()) return
    const editor = editorRef.current
    let html = currentPage.content

    const floatStyle = floatSide === 'left'
      ? 'float:left; margin:0 16px 12px 0; max-width:45%; border-radius:12px;'
      : 'float:right; margin:0 0 12px 16px; max-width:45%; border-radius:12px;'

    const anchorId = 'img-' + Date.now()
    const imgTag = `<img src="${imageUrl}" style="${floatStyle} max-height:300px; object-fit:cover;" data-keyword="${keyword}" data-anchor="${anchorId}" />`

    const tempDiv = document.createElement('div')
    tempDiv.innerHTML = html

    const walker = document.createTreeWalker(tempDiv, NodeFilter.SHOW_TEXT)
    let found = false
    while (walker.nextNode()) {
      const textNode = walker.currentNode
      const text = textNode.textContent || ''
      const idx = text.toLowerCase().indexOf(keyword.toLowerCase())
      if (idx >= 0) {
        const before = text.substring(0, idx + keyword.length)
        const after = text.substring(idx + keyword.length)

        const paragraph = textNode.parentElement?.closest('p, div, h1, h2, h3, h4, h5, h6, li, blockquote')
        if (paragraph && paragraph.parentElement) {
          const wrapper = document.createElement('div')
          wrapper.setAttribute('data-anchor-container', anchorId)
          wrapper.innerHTML = `<span style="border-bottom:2px solid #27ae60;" data-kw="${keyword}">${before}</span>${after}`
          paragraph.parentNode?.insertBefore(wrapper, paragraph)
          paragraph.remove()
          wrapper.insertAdjacentHTML('afterend', `<div data-anchor-img="${anchorId}">${imgTag}</div>`)
          found = true
          break
        } else {
          const span = document.createElement('span')
          span.innerHTML = `<span style="border-bottom:2px solid #27ae60;" data-kw="${keyword}">${before}</span>${after}<div data-anchor-img="${anchorId}">${imgTag}</div>`
          textNode.parentNode?.replaceChild(span, textNode)
          found = true
          break
        }
      }
    }

    if (!found) {
      tempDiv.innerHTML += `<div style="margin:8px 0;"><div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:8px 12px;font-size:12px;color:#856404;">"${keyword}" 단어를 찾지 못했습니다. 텍스트를 먼저 작성한 후 다시 시도하세요.</div>${imgTag}</div>`
    }

    const newContent = tempDiv.innerHTML
    editor.innerHTML = newContent
    updatePage(selectedPage, 'content', newContent)
  }

  function handleInlineImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files
    if (!files?.length || !currentPage) return
    const file = files[0]

    const fd = new FormData()
    fd.append('page_id', String(currentPage.id))
    fd.append('media', file)

    fetch('/api/epub/media/upload', { method: 'POST', body: fd }).then(r => r.json()).then(d => {
      if (d.status === 'success' && d.media?.length) {
        setPendingImageUrl(d.media[0].file_path)
        setShowKeywordInput(true)
      }
    })

    e.target.value = ''
  }

  function confirmKeywordInsert() {
    if (!pendingKeyword.trim()) {
      alert('키워드를 입력하세요.')
      return
    }
    insertImageAtKeyword(pendingImageUrl, pendingKeyword.trim(), imgFloat)
    setShowKeywordInput(false)
    setPendingImageUrl('')
    setPendingKeyword('')
  }

  function insertLink() {
    if (!editorRef.current) return
    if (!linkUrl.trim()) { alert('URL을 입력하세요.'); return }
    const editor = editorRef.current
    editor.focus()

    const url = linkUrl.trim()
    const text = linkText.trim() || url
    const linkHtml = `<a href="${url}" target="_blank" style="color:#27ae60;text-decoration:underline;">${text}</a>`

    const sel = window.getSelection()
    if (sel && sel.rangeCount > 0) {
      const range = sel.getRangeAt(0)
      const temp = document.createElement('div')
      temp.innerHTML = linkHtml
      const linkNode = temp.firstChild
      range.deleteContents()
      if (linkNode) range.insertNode(linkNode)
      range.collapse(false)
      sel.removeAllRanges()
      sel.addRange(range)
    } else {
      editor.innerHTML += linkHtml
    }

    updatePage(selectedPage, 'content', editor.innerHTML)
    setShowLinkModal(false)
    setLinkText('')
    setLinkUrl('')
  }

  function openPhotoEdit(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files
    if (!files?.length) return
    const file = files[0]
    const reader = new FileReader()
    reader.onload = (ev) => {
      setEditImageSrc(ev.target?.result as string)
      setShowPhotoEdit(true)
      setRotateDeg(0)
      setEditImageAction('crop')
    }
    reader.readAsDataURL(file)
    e.target.value = ''
  }

  function applyPhotoEdit() {
    const canvas = canvasRef.current
    const img = document.getElementById('editPreviewImg') as HTMLImageElement
    if (!canvas || !img) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const rad = (rotateDeg * Math.PI) / 180
    const cos = Math.abs(Math.cos(rad))
    const sin = Math.abs(Math.sin(rad))
    const newW = img.naturalWidth * cos + img.naturalHeight * sin
    const newH = img.naturalWidth * sin + img.naturalHeight * cos

    canvas.width = newW
    canvas.height = newH
    ctx.clearRect(0, 0, newW, newH)
    ctx.translate(newW / 2, newH / 2)
    ctx.rotate(rad)
    ctx.drawImage(img, -img.naturalWidth / 2, -img.naturalHeight / 2)

    if (editImageAction === 'watermark' && watermarkText) {
      ctx.save()
      ctx.font = 'bold 20px sans-serif'
      ctx.fillStyle = 'rgba(255,255,255,0.7)'
      ctx.strokeStyle = 'rgba(0,0,0,0.5)'
      ctx.lineWidth = 1
      const metrics = ctx.measureText(watermarkText)
      const tw = metrics.width
      let wx = 20, wy = canvas.height - 20
      if (watermarkPos === 'top-left') { wx = 20; wy = 30 }
      else if (watermarkPos === 'top-right') { wx = canvas.width - tw - 20; wy = 30 }
      else if (watermarkPos === 'bottom-left') { wx = 20; wy = canvas.height - 20 }
      else if (watermarkPos === 'center') { wx = (canvas.width - tw) / 2; wy = canvas.height / 2 }
      ctx.strokeText(watermarkText, wx, wy)
      ctx.fillText(watermarkText, wx, wy)
      ctx.restore()
    }

    canvas.toBlob((blob) => {
      if (!blob || !currentPage) return
      const fd = new FormData()
      fd.append('page_id', String(currentPage.id))
      fd.append('media', new File([blob], 'edited.jpg', { type: 'image/jpeg' }))
      fetch('/api/epub/media/upload', { method: 'POST', body: fd }).then(r => r.json()).then(d => {
        if (d.status === 'success' && d.media?.length) {
          setPendingImageUrl(d.media[0].file_path)
          setShowPhotoEdit(false)
          setShowKeywordInput(true)
        }
      })
    }, 'image/jpeg', 0.9)
  }

  function deleteMedia(mediaId: number) {
    fetch(`/api/epub/media/${mediaId}`, { method: 'DELETE' }).then(r => r.json()).then(d => {
      if (d.status === 'success') {
        setPages(prev => {
          const next = [...prev]
          next[selectedPage] = { ...next[selectedPage], media: next[selectedPage].media.filter(m => m.id !== mediaId) }
          return next
        })
      }
    })
  }

  function aiAssist() {
    if (!currentPage) return
    const ctx = editorRef.current?.innerText || ''
    fetch('/api/epub/ai/assist', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ section_title: currentPage.title, context: ctx, layout_type: book?.layout_type, book_title: book?.title })
    }).then(r => r.json()).then(d => {
      if (d.status === 'success' && d.suggestion) {
        if (confirm('AI가 작성한 초안을 삽입하시겠습니까?\n\n' + d.suggestion.substring(0, 200))) {
          updatePage(selectedPage, 'content', ctx + '\n\n' + d.suggestion)
        }
      } else {
        alert(d.suggestion || 'AI 도우미를 사용할 수 없습니다.')
      }
    })
  }

  function publishBook(status: string) {
    fetch(`/api/epub/book/${id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    }).then(r => r.json()).then(d => {
      if (d.status === 'success') { setBook((prev: any) => ({ ...prev, status })); alert(status === 'published' ? '발행되었습니다.' : '임시저장되었습니다.') }
    })
  }

  if (loading) return <div className="text-center py-5"><div className="spinner-border" /></div>
  if (!book) return <div className="text-center py-5 text-muted">콘텐츠를 찾을 수 없습니다.</div>

  const styleGuide = template?.style_guide || {}

  return (
    <div className="container-fluid px-2 py-2" style={{ maxWidth: '100%' }}>
      <div className="d-flex justify-content-between align-items-center mb-2">
        <div>
          <a href="/epub" className="text-decoration-none small">목록</a>
          <h5 className="fw-bold mb-0 ms-2 d-inline">{book.title}</h5>
          {book.status === 'draft' && <span className="badge bg-warning text-dark ms-2" style={{ fontSize: '0.6rem' }}>임시</span>}
        </div>
        <div className="d-flex gap-2">
          {book.status === 'draft' ? (
            <button className="btn btn-success btn-sm" onClick={() => publishBook('published')}>발행</button>
          ) : (
            <button className="btn btn-outline-warning btn-sm" onClick={() => publishBook('draft')}>비공개</button>
          )}
          <a href={`/epub/view/${id}`} target="_blank" className="btn btn-outline-primary btn-sm">미리보기</a>
        </div>
      </div>

      {template && (
        <div className="mb-2 p-2 rounded small" style={{ background: styleGuide.color_primary ? styleGuide.color_primary + '15' : '#f0f0f0', borderLeft: `4px solid ${styleGuide.color_primary || '#ccc'}` }}>
          <strong>{template.name}</strong> 템플릿 사용 중
          {template.sections?.length > 0 && (
            <span className="ms-2 text-muted">| 섹션: {template.sections.map((s: any) => s.title).join(' > ')}</span>
          )}
        </div>
      )}

      <div className="row g-2" style={{ minHeight: '75vh' }}>
        <div className="col-3" style={{ borderRight: '1px solid #eee' }}>
          <div className="d-flex justify-content-between align-items-center mb-2 px-1">
            <small className="fw-bold text-muted">섹션 ({pages.length})</small>
            <div className="d-flex gap-1">
              <button className="btn btn-sm btn-outline-success" style={{ padding: '2px 8px', fontSize: 11 }} onClick={() => setShowTemplateModal(true)}>+ 템플릿</button>
              <button className="btn btn-sm btn-outline-secondary" style={{ padding: '2px 8px', fontSize: 11 }} onClick={addPage}>+ 빈 섹션</button>
            </div>
          </div>
          <div className="list-group list-group-flush">
            {pages.map((p, i) => (
              <button key={p.id}
                className={`list-group-item list-group-item-action py-2 px-2 ${i === selectedPage ? 'active' : ''}`}
                style={{ fontSize: 13, cursor: 'pointer' }}
                onClick={() => setSelectedPage(i)}>
                <div className="d-flex justify-content-between">
                  <span className="text-truncate" style={{ maxWidth: 120 }}>{p.title || '(제목 없음)'}</span>
                  <button className="btn btn-link text-danger p-0" style={{ fontSize: 10 }}
                    onClick={e => { e.stopPropagation(); deletePage(i) }}>X</button>
                </div>
                {p.media.length > 0 && <small className="text-muted" style={{ fontSize: 10 }}>{p.media.length}장</small>}
              </button>
            ))}
          </div>
        </div>

        <div className="col-5 px-2">
          {currentPage && (
            <>
              <div className="mb-2">
                <input type="text" className="form-control form-control-sm fw-bold" value={currentPage.title}
                  onChange={e => updatePage(selectedPage, 'title', e.target.value)}
                  placeholder="섹션 제목" />
              </div>
              <div className="mb-2">
                <div ref={editorRef} contentEditable suppressContentEditableWarning
                  className="form-control" style={{ minHeight: 250, fontSize: styleGuide.body_size || 15, lineHeight: styleGuide.line_height || 1.8, fontFamily: styleGuide.font_family || 'inherit' }}
                  dangerouslySetInnerHTML={{ __html: currentPage.content }}
                  onBlur={e => updatePage(selectedPage, 'content', e.target.innerHTML)}
                />
              </div>
              <div className="d-flex gap-1 mb-2 align-items-center flex-wrap">
                <button className="btn btn-sm btn-outline-primary" onClick={() => savePage(selectedPage)} disabled={saving} style={{ fontSize: 11 }}>
                  {saving ? '저장 중...' : '저장'}
                </button>
                <button className="btn btn-sm btn-outline-info" onClick={aiAssist} style={{ fontSize: 11 }}>AI 도우미</button>
                <button className="btn btn-sm btn-outline-primary" onClick={() => setShowLinkModal(true)} style={{ fontSize: 11 }}>링크</button>
                <div className="btn-group btn-group-sm" role="group">
                  <button type="button" className={`btn ${imgFloat === 'left' ? 'btn-success' : 'btn-outline-success'}`}
                    onClick={() => setImgFloat('left')} style={{ fontSize: 11 }}>왼쪽</button>
                  <button type="button" className={`btn ${imgFloat === 'right' ? 'btn-success' : 'btn-outline-success'}`}
                    onClick={() => setImgFloat('right')} style={{ fontSize: 11 }}>오른쪽</button>
                </div>
                <label className="btn btn-sm btn-outline-success mb-0" style={{ fontSize: 11 }}>
                  사진 삽입
                  <input type="file" accept="image/*" ref={fileInputRef} onChange={handleInlineImageUpload} style={{ display: 'none' }} />
                </label>
                <label className="btn btn-sm btn-outline-warning mb-0" style={{ fontSize: 11 }}>
                  사진편집
                  <input type="file" accept="image/*" ref={photoEditInputRef} onChange={openPhotoEdit} style={{ display: 'none' }} />
                </label>
              </div>
              <div style={{ fontSize: 11, color: '#999', marginBottom: 8 }}>
                사진 삽입: 키워드 위치에 사진 배치 | 사진편집: 자르기/회전/워터마크 후 삽입 | 링크: URL 하이퍼링크
              </div>
              {currentPage.media.length > 0 && (
                <div className="mt-2">
                  <small className="fw-bold text-muted" style={{ fontSize: 11 }}>첨부 사진</small>
                  <div className="d-flex gap-2 flex-wrap mt-1">
                    {currentPage.media.map(m => (
                      <div key={m.id} className="position-relative">
                        <img src={m.file_path} style={{ width: 80, height: 80, objectFit: 'cover', borderRadius: 8 }} />
                        <button className="btn btn-sm btn-danger position-absolute" style={{ top: -6, right: -6, width: 18, height: 18, padding: 0, fontSize: 10, borderRadius: '50%' }}
                          onClick={() => deleteMedia(m.id)}>X</button>
                        {m.latitude && m.longitude && (
                          <div className="position-absolute bottom-0 start-0 badge bg-success" style={{ fontSize: 8, padding: '1px 4px' }}>GPS</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <div className="col-4">
          <div ref={mapRef} style={{ height: '100%', minHeight: 300, borderRadius: 12 }} />
        </div>
      </div>

      {showLinkModal && (
        <div className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center"
          style={{ background: 'rgba(0,0,0,0.5)', zIndex: 9999 }}
          onClick={() => { setShowLinkModal(false); setLinkText(''); setLinkUrl('') }}>
          <div className="bg-white shadow-lg" style={{ borderRadius: 16, maxWidth: 400, width: '90%' }}
            onClick={e => e.stopPropagation()}>
            <div className="p-3 border-bottom">
              <h6 className="fw-bold mb-0">링크 삽입</h6>
            </div>
            <div className="p-3">
              <div className="mb-2">
                <label className="form-label small fw-bold">표시할 텍스트 (선택)</label>
                <input type="text" className="form-control" value={linkText}
                  onChange={e => setLinkText(e.target.value)} placeholder="클릭할 텍스트" />
              </div>
              <div className="mb-2">
                <label className="form-label small fw-bold">URL</label>
                <input type="url" className="form-control" value={linkUrl}
                  onChange={e => setLinkUrl(e.target.value)} placeholder="https://example.com" autoFocus />
              </div>
              <div className="d-flex gap-2">
                <button className="btn btn-outline-secondary btn-sm flex-fill"
                  onClick={() => { setShowLinkModal(false); setLinkText(''); setLinkUrl('') }}>취소</button>
                <button className="btn btn-primary btn-sm flex-fill" onClick={insertLink}>삽입</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showKeywordInput && (
        <div className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center"
          style={{ background: 'rgba(0,0,0,0.5)', zIndex: 9999 }}
          onClick={() => { setShowKeywordInput(false); setPendingImageUrl(''); setPendingKeyword('') }}>
          <div className="bg-white shadow-lg" style={{ borderRadius: 16, maxWidth: 420, width: '90%' }}
            onClick={e => e.stopPropagation()}>
            <div className="p-3 border-bottom">
              <h6 className="fw-bold mb-0">키워드에 사진 매칭</h6>
            </div>
            <div className="p-3">
              <div className="mb-2">
                <img src={pendingImageUrl} style={{ width: '100%', maxHeight: 200, objectFit: 'cover', borderRadius: 10 }} />
              </div>
              <div className="mb-2">
                <label className="form-label small fw-bold">매칭할 키워드 입력</label>
                <input type="text" className="form-control" value={pendingKeyword}
                  onChange={e => setPendingKeyword(e.target.value)}
                  placeholder="예: 양평소방서, 둔포교, 꽃구경..."
                  onKeyDown={e => { if (e.key === 'Enter') confirmKeywordInsert() }}
                  autoFocus />
                <small className="text-muted" style={{ fontSize: 11 }}>텍스트에 있는 단어를 정확히 입력하세요.</small>
              </div>
              <div className="mb-2">
                <label className="form-label small fw-bold">배치 위치</label>
                <div className="d-flex gap-2">
                  <button className={`btn btn-sm flex-fill ${imgFloat === 'left' ? 'btn-success' : 'btn-outline-success'}`}
                    onClick={() => setImgFloat('left')}>텍스트 왼쪽</button>
                  <button className={`btn btn-sm flex-fill ${imgFloat === 'right' ? 'btn-success' : 'btn-outline-success'}`}
                    onClick={() => setImgFloat('right')}>텍스트 오른쪽</button>
                </div>
              </div>
              <div className="d-flex gap-2">
                <button className="btn btn-outline-secondary btn-sm flex-fill"
                  onClick={() => { setShowKeywordInput(false); setPendingImageUrl(''); setPendingKeyword('') }}>취소</button>
                <button className="btn btn-success btn-sm flex-fill" onClick={confirmKeywordInsert}>삽입</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showPhotoEdit && (
        <div className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center"
          style={{ background: 'rgba(0,0,0,0.5)', zIndex: 9999 }}
          onClick={() => setShowPhotoEdit(false)}>
          <div className="bg-white shadow-lg" style={{ borderRadius: 16, maxWidth: 600, width: '95%', maxHeight: '90vh', overflow: 'auto' }}
            onClick={e => e.stopPropagation()}>
            <div className="p-3 border-bottom d-flex justify-content-between align-items-center">
              <h6 className="fw-bold mb-0">사진편집</h6>
              <button className="btn btn-sm btn-outline-secondary" onClick={() => setShowPhotoEdit(false)}>✕</button>
            </div>
            <div className="p-3">
              <div className="mb-3">
                <div className="btn-group btn-group-sm w-100" role="group">
                  <button className={`btn ${editImageAction === 'crop' ? 'btn-primary' : 'btn-outline-primary'}`}
                    onClick={() => setEditImageAction('crop')}>자르기</button>
                  <button className={`btn ${editImageAction === 'rotate' ? 'btn-primary' : 'btn-outline-primary'}`}
                    onClick={() => setEditImageAction('rotate')}>회전</button>
                  <button className={`btn ${editImageAction === 'watermark' ? 'btn-primary' : 'btn-outline-primary'}`}
                    onClick={() => setEditImageAction('watermark')}>워터마크</button>
                </div>
              </div>

              <div className="text-center mb-3">
                <img id="editPreviewImg" src={editImageSrc}
                  style={{ maxWidth: '100%', maxHeight: 350, borderRadius: 10, transform: `rotate(${rotateDeg}deg)`, transition: 'transform 0.3s' }} />
                <canvas ref={canvasRef} style={{ display: 'none' }} />
              </div>

              {editImageAction === 'rotate' && (
                <div className="mb-3">
                  <label className="form-label small fw-bold">회전 각도: {rotateDeg}°</label>
                  <input type="range" className="form-range" min={-180} max={180} step={5}
                    value={rotateDeg} onChange={e => setRotateDeg(Number(e.target.value))} />
                  <div className="d-flex justify-content-between" style={{ fontSize: 10, color: '#999' }}>
                    <span>-180°</span>
                    <button className="btn btn-link btn-sm p-0" style={{ fontSize: 11 }} onClick={() => setRotateDeg(0)}>초기화</button>
                    <span>180°</span>
                  </div>
                </div>
              )}

              {editImageAction === 'watermark' && (
                <div className="mb-3">
                  <div className="mb-2">
                    <label className="form-label small fw-bold">워터마크 텍스트</label>
                    <input type="text" className="form-control form-control-sm" value={watermarkText}
                      onChange={e => setWatermarkText(e.target.value)} placeholder="워터마크 텍스트" />
                  </div>
                  <div>
                    <label className="form-label small fw-bold">위치</label>
                    <div className="d-flex gap-1 flex-wrap">
                      {[['top-left','좌상단'],['top-right','우상단'],['center','가운데'],['bottom-left','좌하단'],['bottom-right','우하단']].map(([v,l]) => (
                        <button key={v} className={`btn btn-sm ${watermarkPos === v ? 'btn-success' : 'btn-outline-success'}`}
                          onClick={() => setWatermarkPos(v)} style={{ fontSize: 10 }}>{l}</button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {editImageAction === 'crop' && (
                <div className="mb-3">
                  <small className="text-muted" style={{ fontSize: 11 }}>사진을 클릭한 상태에서 드래그하여 영역을 선택하세요. (추후 구현)</small>
                </div>
              )}

              <div className="d-flex gap-2">
                <button className="btn btn-outline-secondary btn-sm flex-fill" onClick={() => setShowPhotoEdit(false)}>취소</button>
                <button className="btn btn-success btn-sm flex-fill" onClick={applyPhotoEdit}>편집 후 삽입</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showTemplateModal && (
        <div className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center"
          style={{ background: 'rgba(0,0,0,0.5)', zIndex: 9999 }}
          onClick={() => setShowTemplateModal(false)}>
          <div className="bg-white shadow-lg" style={{ borderRadius: 16, maxWidth: 600, width: '90%', maxHeight: '80vh', overflow: 'auto' }}
            onClick={e => e.stopPropagation()}>
            <div className="d-flex justify-content-between align-items-center p-3 border-bottom">
              <h5 className="fw-bold mb-0">템플릿에서 섹션 추가</h5>
              <button className="btn btn-sm btn-outline-secondary" onClick={() => setShowTemplateModal(false)}>✕</button>
            </div>
            <div className="p-3">
              {guideTemplates.length === 0 ? (
                <p className="text-muted text-center">사용 가능한 템플릿이 없습니다.</p>
              ) : (
                <div className="row g-2">
                  {guideTemplates.map(t => (
                    <div key={t.id} className="col-12">
                      <div className="card border-0 shadow-sm" style={{ borderRadius: 10, cursor: 'pointer' }}
                        onClick={() => addPageFromTemplate(t)}>
                        <div className="card-body p-3">
                          <div className="d-flex align-items-center gap-2 mb-1">
                            <span className="badge bg-success" style={{ fontSize: '0.6rem' }}>{t.layout_type}</span>
                            {t.is_featured && <span className="badge bg-warning text-dark" style={{ fontSize: '0.6rem' }}>추천</span>}
                            <small className="text-muted ms-auto" style={{ fontSize: 10 }}>사용 {t.use_count}회</small>
                          </div>
                          <h6 className="fw-bold mb-1" style={{ fontSize: 14 }}>{t.name}</h6>
                          <small className="text-muted" style={{ fontSize: 12 }}>{t.description}</small>
                          <div className="mt-2 p-2 rounded" style={{ background: '#f8f9fa', fontSize: 12, maxHeight: 80, overflow: 'hidden' }}
                            dangerouslySetInnerHTML={{ __html: t.html_content }} />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
