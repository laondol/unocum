import { useEffect, useState, useRef } from 'react'

interface Photo { path: string }

export default function ShareEdit() {
  const id = window.location.pathname.split('/').filter(Boolean).pop()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [aiCategory, setAiCategory] = useState('')
  const [photos, setPhotos] = useState<Photo[]>([])
  const [rotations, setRotations] = useState<Record<string, number>>({})
  const [lat, setLat] = useState('')
  const [lon, setLon] = useState('')
  const [newPreviews, setNewPreviews] = useState<string[]>([])
  const [newFiles, setNewFiles] = useState<File[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [loading, setLoading] = useState(true)
  const [leafletReady, setLeafletReady] = useState(false)

  const [storeQuery, setStoreQuery] = useState('')
  const [storeResults, setStoreResults] = useState<any[]>([])
  const [storeSuggestionId, setStoreSuggestionId] = useState('')
  const [selectedStore, setSelectedStore] = useState('')
  const [menuText, setMenuText] = useState('')
  const [menuResult, setMenuResult] = useState('')

  // 워터마크
  const [watermarkText, setWatermarkText] = useState('')
  const [watermarkPos, setWatermarkPos] = useState('bottom-right')
  const [watermarkOpacity, setWatermarkOpacity] = useState(0.5)
  const [watermarkTarget, setWatermarkTarget] = useState('')
  const [wmApplying, setWmApplying] = useState(false)

  // 메뉴 검색
  const [menuSearchName, setMenuSearchName] = useState('')
  const [menuSearching, setMenuSearching] = useState(false)
  const [menuSearchResult, setMenuSearchResult] = useState<any[]>([])

  // 메뉴 목록
  const [storeMenus, setStoreMenus] = useState<any[]>([])
  const [newMenuName, setNewMenuName] = useState('')
  const [newMenuPrice, setNewMenuPrice] = useState('')
  const [newMenuCat, setNewMenuCat] = useState('기타')

  // Cropper 모달
  const [cropOpen, setCropOpen] = useState(false)
  const [cropTarget, setCropTarget] = useState<{ type: 'new'; index: number } | { type: 'existing'; path: string } | null>(null)
  const cropImgRef = useRef<HTMLImageElement>(null)
  const cropperRef = useRef<any>(null)

  // 회전 모달
  const [rotOpen, setRotOpen] = useState(false)
  const [rotSrc, setRotSrc] = useState('')
  const [rotKey, setRotKey] = useState('')
  const [rotAngle, setRotAngle] = useState(0)

  const [editedBlobs, setEditedBlobs] = useState<Record<string, Blob>>({})

  const fileInputRef = useRef<HTMLInputElement>(null)
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<any>(null)
  const originalLatRef = useRef('')
  const originalLonRef = useRef('')

  useEffect(() => {
    fetch(`/api/share/report/${id}`).then(r => r.json()).then(d => {
      setTitle(d.title || '')
      setDescription(d.description || '')
      setAiCategory(d.ai_category || '')
      setLat(d.latitude || '')
      setLon(d.longitude || '')
      const existing: Photo[] = []
      if (d.image_path) existing.push({ path: d.image_path })
      if (d.extra_images) {
        d.extra_images.split(',').filter(Boolean).forEach((p: string) => existing.push({ path: p.trim() }))
      }
      setPhotos(existing)
      originalLatRef.current = d.latitude || ''
      originalLonRef.current = d.longitude || ''
      setLoading(false)
    })
    loadLeaflet()
  }, [id])

  useEffect(() => {
    if (!lat || !lon || !leafletReady) return
    const L = (window as any).L
    if (!L || !mapRef.current) return
    const lt = parseFloat(lat); const ln = parseFloat(lon)
    if (isNaN(lt) || isNaN(ln)) return
    if (mapInstanceRef.current) { mapInstanceRef.current.setView([lt, ln], 15); return }
    mapInstanceRef.current = L.map(mapRef.current).setView([lt, ln], 15)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(mapInstanceRef.current)
    const marker = L.marker([lt, ln], { draggable: true }).addTo(mapInstanceRef.current)
    marker.on('dragend', (e: any) => { const pos = e.target.getLatLng(); setLat(pos.lat.toFixed(7)); setLon(pos.lng.toFixed(7)) })
    setTimeout(() => mapInstanceRef.current?.invalidateSize(), 300)
  }, [lat, lon, leafletReady])

  function loadLeaflet() {
    if (document.getElementById('leaflet-css')) return
    const link = document.createElement('link'); link.id = 'leaflet-css'; link.rel = 'stylesheet'; link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'; document.head.appendChild(link)
    const script = document.createElement('script'); script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'; script.onload = () => setLeafletReady(true); document.head.appendChild(script)
  }

  function loadCropperLib(cb: () => void) {
    if ((window as any).Cropper) { cb(); return }
    const link = document.createElement('link'); link.rel = 'stylesheet'; link.href = 'https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.2/cropper.min.css'; document.head.appendChild(link)
    const s = document.createElement('script'); s.src = 'https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.2/cropper.min.js'; s.onload = () => cb(); document.head.appendChild(s)
  }

  function openCrop(target: { type: 'new'; index: number } | { type: 'existing'; path: string }, src: string) {
    setCropTarget(target)
    setCropOpen(true)
    loadCropperLib(() => {
      setTimeout(() => {
        const img = cropImgRef.current
        if (!img) return
        img.onload = () => {
          if (cropperRef.current) cropperRef.current.destroy()
          cropperRef.current = new (window as any).Cropper(img, { viewMode: 1, autoCropArea: 1 })
        }
        img.src = src
      }, 100)
    })
  }

  function applyCrop() {
    if (!cropperRef.current || !cropTarget) return
    const canvas = cropperRef.current.getCroppedCanvas({ maxWidth: 1600, maxHeight: 1600, imageSmoothingQuality: 'high' })
    const finish = (blob: Blob | null) => {
      if (!blob) return
      const key = cropTarget.type === 'new' ? `new_${cropTarget.index}` : cropTarget.path
      setEditedBlobs(prev => ({ ...prev, [key]: blob }))
      setCropOpen(false)
      if (cropperRef.current) { cropperRef.current.destroy(); cropperRef.current = null }
    }
    try {
      canvas.toBlob((b: Blob | null) => { if (b) finish(b) }, 'image/jpeg', 0.9)
    } catch { }
  }

  function openRotate(key: string, src: string) {
    setRotKey(key)
    setRotSrc(src)
    setRotAngle(rotations[key] || 0)
    setRotOpen(true)
  }

  function applyRotate() {
    if (rotKey) setRotations(prev => ({ ...prev, [rotKey]: rotAngle }))
    setRotOpen(false)
  }

  function deletePhoto(path: string) {
    if (!confirm('이 사진을 삭제하시겠습니까?')) return
    fetch(`/share-report/delete-image/${id}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image_path: path }) })
      .then(r => r.json()).then(d => { if (d.status === 'success') setPhotos(prev => prev.filter(p => p.path !== path)); else alert(d.msg || '오류') })
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files
    if (!files?.length) return
    const arr: File[] = []; const urls: string[] = []
    for (const f of files) { arr.push(f); if (f.type.startsWith('image/')) urls.push(URL.createObjectURL(f)) }
    setNewFiles(prev => [...prev, ...arr])
    setNewPreviews(prev => [...prev, ...urls])
  }

  function removeNewFile(idx: number) {
    setNewFiles(prev => prev.filter((_, i) => i !== idx))
    setNewPreviews(prev => { URL.revokeObjectURL(prev[idx]); return prev.filter((_, i) => i !== idx) })
  }

  function onStoreSearch(q: string) {
    setStoreQuery(q)
    if (!q.trim()) { setStoreResults([]); return }
    let url = `/api/share/store-search?q=${encodeURIComponent(q)}`
    if (lat && lon) url += `&lat=${lat}&lon=${lon}`
    fetch(url).then(r => r.json()).then(d => setStoreResults(d.results || []))
  }
  function pickStore(p: any) {
    setSelectedStore(`${p.name} (${p.address || ''})`)
    setStoreResults([])
    setStoreSuggestionId(String(p.suggestion_id || ''))
    fetch('/api/share/store-suggest', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ place_id: p.place_id, name: p.name, lat: p.lat, lon: p.lon, address: p.address, place_url: p.place_url, phone: p.phone }) })
      .then(r => r.json()).then(d => {
        if (d.suggestion_id) setStoreSuggestionId(String(d.suggestion_id))
        loadStoreMenus(d.suggestion_id)
      })
  }

  function loadStoreMenus(ssid: number) {
    if (!ssid) return
    fetch(`/api/share/store-menus/${ssid}`).then(r => r.json()).then(d => setStoreMenus(d))
  }

  function addMenu() {
    if (!newMenuName.trim() || !storeSuggestionId) return
    fetch('/api/share/store-menu/add', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ store_suggestion_id: parseInt(storeSuggestionId), name: newMenuName, price: newMenuPrice, sub_category: newMenuCat })
    }).then(r => r.json()).then(d => {
      if (d.status === 'success') {
        setStoreMenus(prev => [...prev, { id: d.id, name: newMenuName, price: newMenuPrice, sub_category: newMenuCat, ai_generated: false }])
        setNewMenuName(''); setNewMenuPrice('')
      }
    })
  }

  function deleteMenu(menuId: number) {
    fetch(`/api/share/store-menu/delete/${menuId}`, { method: 'POST' })
      .then(r => r.json()).then(d => { if (d.status === 'success') setStoreMenus(prev => prev.filter(m => m.id !== menuId)) })
  }

  function searchMenus() {
    if (!menuSearchName.trim()) { alert('가게명을 입력하세요'); return }
    setMenuSearching(true)
    fetch('/api/share/menu-search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ store_name: menuSearchName }) })
      .then(r => r.json()).then(d => {
        setMenuSearchResult(d.menus || [])
        if (d.store) setSelectedStore(`${d.store.name} (${d.store.address || ''})`)
        setMenuSearching(false)
        if (d.menus?.length > 0) {
          const text = d.menus.map((m: any) => `${m.name} ${m.price || ''}`).join('\n')
          setMenuText(text)
        }
      }).catch(() => setMenuSearching(false))
  }

  function classifyMenu() {
    if (!menuText.trim()) { alert('메뉴를 입력하세요'); return }
    fetch('/api/share/menu-classify', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: menuText }) })
      .then(r => r.json()).then(d => {
        const labels = d.labels || ['기타']
        const lines = menuText.split('\n')
        let html = '<b>분류 결과:</b><br>'
        lines.forEach((line: string, i: number) => { if (line.trim()) html += `<span class="badge bg-info text-dark me-1">${labels[i] || '기타'}</span>${line.trim()}<br>` })
        setMenuResult(html)
      })
  }

  function applyWatermark(imagePath: string) {
    if (!watermarkText.trim()) { alert('워터마크 텍스트를 입력하세요'); return }
    setWmApplying(true)
    fetch('/api/share/watermark', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_path: imagePath, text: watermarkText, position: watermarkPos, opacity: watermarkOpacity })
    }).then(r => r.json()).then(d => {
      setWmApplying(false)
      if (d.status === 'success') { alert('워터마크가 적용되었습니다.'); location.reload() }
      else alert(d.msg || '워터마크 실패')
    }).catch(() => { setWmApplying(false); alert('워터마크 적용 중 오류') })
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (submitting) return
    setSubmitting(true)
    const fd = new FormData()
    fd.append('title', title)
    fd.append('description', description)
    fd.append('ai_category', aiCategory)
    fd.append('latitude', lat)
    fd.append('longitude', lon)
    fd.append('original_lat', originalLatRef.current)
    fd.append('original_lon', originalLonRef.current)
    if (storeSuggestionId) fd.append('store_suggestion_id', storeSuggestionId)
    if (menuText.trim()) fd.append('menu_text', menuText)

    newFiles.forEach((f, i) => {
      const blob = editedBlobs[`new_${i}`]
      fd.append('image', blob || f, `new_${i}.jpg`)
      const a = rotations[`new_${i}`]
      if (a) fd.append(`rotate_angle_${i}`, String(a))
    })

    photos.forEach((p) => {
      const croppedBlob = editedBlobs[p.path]
      if (croppedBlob) {
        fd.append('replace_image', `${p.path}||re.jpg`)
        fd.append('replace_blob', croppedBlob, 're.jpg')
      }
      const a = rotations[p.path]
      if (a) fd.append('replace_rotate', `${p.path}||${a}`)
    })

    try {
      const res = await fetch(`/share-report/edit/${id}`, { method: 'POST', body: fd })
      const data = await res.json()
      if (data.status === 'success') { alert(data.msg); window.location.href = `/share/detail/${id}` }
      else { alert(data.msg || '오류'); setSubmitting(false) }
    } catch (err: any) { alert('오류: ' + err.message); setSubmitting(false) }
  }

  if (loading) return <div className="text-center py-5"><div className="spinner-border" /></div>

  return (
    <div className="container-fluid px-3 py-3" style={{ maxWidth: '100%' }}>
      <h4 className="fw-bold mb-3 text-center">공유 수정</h4>
      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-3">
          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label fw-bold small">사진</label>
              <div className="d-flex gap-2 flex-wrap mb-2">
                {photos.map((p, i) => (
                  <div key={i} className="position-relative" style={{ width: 100 }}>
                    <div style={{ width: 100, height: 100, overflow: 'hidden', borderRadius: 8, backgroundColor: '#f1f3f5', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <img
                        src={editedBlobs[p.path] ? URL.createObjectURL(editedBlobs[p.path]) : `${p.path}?v=${Date.now()}`}
                        style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', transform: `rotate(${rotations[p.path] || 0}deg)` }}
                      />
                    </div>
                    {photos.length > 1 && <button type="button" onClick={() => deletePhoto(p.path)} className="btn btn-sm btn-danger position-absolute" style={{ top: -6, right: -6, width: 22, height: 22, padding: 0, fontSize: 12, lineHeight: '1', borderRadius: '50%' }}>&times;</button>}
                    <button type="button" onClick={() => openCrop({ type: 'existing', path: p.path }, p.path)} className="btn btn-sm btn-dark position-absolute" style={{ bottom: -6, right: -6, width: 22, height: 22, padding: 0, fontSize: 10, lineHeight: '1', borderRadius: '50%' }}>C</button>
                    <button type="button" onClick={() => openRotate(p.path, editedBlobs[p.path] ? URL.createObjectURL(editedBlobs[p.path]) : p.path)} className="btn btn-sm btn-primary position-absolute" style={{ bottom: -6, left: -6, width: 22, height: 22, padding: 0, fontSize: 10, lineHeight: '1', borderRadius: '50%' }}>R</button>
                    <button type="button" onClick={() => setWatermarkTarget(p.path)} className="btn btn-sm btn-warning position-absolute" style={{ top: -6, left: -6, width: 22, height: 22, padding: 0, fontSize: 8, lineHeight: '1', borderRadius: '50%' }}>W</button>
                  </div>
                ))}
                {newPreviews.map((u, i) => (
                  <div key={`new-${i}`} className="position-relative" style={{ width: 100 }}>
                    <div style={{ width: 100, height: 100, overflow: 'hidden', borderRadius: 8, border: '2px solid #0d6efd', backgroundColor: '#f1f3f5', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <img
                        src={editedBlobs[`new_${i}`] ? URL.createObjectURL(editedBlobs[`new_${i}`]) : u}
                        style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', transform: `rotate(${rotations[`new_${i}`] || 0}deg)` }}
                      />
                    </div>
                    <button type="button" onClick={() => removeNewFile(i)} className="btn btn-sm btn-danger position-absolute" style={{ top: -6, right: -6, width: 22, height: 22, padding: 0, fontSize: 12, lineHeight: '1', borderRadius: '50%' }}>&times;</button>
                    <button type="button" onClick={() => openCrop({ type: 'new', index: i }, u)} className="btn btn-sm btn-dark position-absolute" style={{ bottom: -6, right: -6, width: 22, height: 22, padding: 0, fontSize: 10, lineHeight: '1', borderRadius: '50%' }}>C</button>
                    <button type="button" onClick={() => openRotate(`new_${i}`, editedBlobs[`new_${i}`] ? URL.createObjectURL(editedBlobs[`new_${i}`]) : u)} className="btn btn-sm btn-primary position-absolute" style={{ bottom: -6, left: -6, width: 22, height: 22, padding: 0, fontSize: 10, lineHeight: '1', borderRadius: '50%' }}>R</button>
                  </div>
                ))}
              </div>
              <input type="file" ref={fileInputRef} className="form-control" accept="image/*" multiple onChange={onFileChange} />
              <small className="text-muted">C 자르기, R 회전, W 워터마크</small>
            </div>

            <div className="mb-3">
              <label className="form-label fw-bold small">제목</label>
              <input type="text" className="form-control" value={title} onChange={e => setTitle(e.target.value)} />
            </div>

            <div className="mb-3">
              <label className="form-label fw-bold small">AI 추천 카테고리</label>
              <input type="text" className="form-control" value={aiCategory} onChange={e => setAiCategory(e.target.value)} placeholder="AI가 추천한 카테고리 (수정 가능)" />
            </div>

            <div className="mb-3">
              <label className="form-label fw-bold small">가게 연결 (카카오맵 검색)</label>
              <input type="text" className="form-control" value={storeQuery} onChange={e => onStoreSearch(e.target.value)} placeholder="가게명 검색" />
              {storeResults.length > 0 && (
                <div className="list-group mt-2">
                  {storeResults.map((p, i) => (
                    <button type="button" key={i} className="list-group-item list-group-item-action" onClick={() => pickStore(p)}>
                      <div className="fw-bold">{p.name}</div><small className="text-muted">{p.address}</small>
                    </button>
                  ))}
                </div>
              )}
              {selectedStore && <div className="mt-1 small text-success fw-bold">{selectedStore}</div>}
            </div>

            <div className="mb-3">
              <label className="form-label fw-bold small">메뉴 검색 (AI 자동 추출)</label>
              <div className="input-group">
                <input type="text" className="form-control" value={menuSearchName} onChange={e => setMenuSearchName(e.target.value)} placeholder="가게명을 입력하면 AI가 메뉴를 추천합니다" />
                <button type="button" className="btn btn-outline-primary" onClick={searchMenus} disabled={menuSearching}>
                  {menuSearching ? '검색 중...' : '메뉴 검색'}
                </button>
              </div>
              {menuSearchResult.length > 0 && (
                <div className="mt-2 p-2 bg-light rounded small">
                  <strong>검색 결과:</strong><br />
                  {menuSearchResult.map((m: any, i: number) => (
                    <span key={i}>
                      <span className="badge bg-success text-white me-1 mb-1">{m.category || '기타'}</span>
                      {m.name} {m.price && <span className="text-muted">({m.price})</span>}
                      <br />
                    </span>
                  ))}
                </div>
              )}
            </div>

            {storeSuggestionId && (
              <div className="mb-3">
                <label className="form-label fw-bold small">가게 메뉴 목록</label>
                {storeMenus.length > 0 && (
                  <div className="mb-2">
                    {storeMenus.map((m: any) => (
                      <div key={m.id} className="d-flex align-items-center gap-2 mb-1 p-1 bg-light rounded small">
                        <span className="badge bg-secondary">{m.sub_category}</span>
                        <span className="flex-grow-1">{m.name}</span>
                        {m.price && <span className="text-muted">{m.price}</span>}
                        <button type="button" className="btn btn-sm btn-outline-danger" onClick={() => deleteMenu(m.id)} style={{ padding: '0 4px', fontSize: 10 }}>X</button>
                      </div>
                    ))}
                  </div>
                )}
                <div className="input-group input-group-sm">
                  <select className="form-select" style={{ maxWidth: 80 }} value={newMenuCat} onChange={e => setNewMenuCat(e.target.value)}>
                    <option value="식사">식사</option>
                    <option value="음료">음료</option>
                    <option value="디저트">디저트</option>
                    <option value="기타">기타</option>
                  </select>
                  <input type="text" className="form-control" value={newMenuName} onChange={e => setNewMenuName(e.target.value)} placeholder="메뉴명" />
                  <input type="text" className="form-control" style={{ maxWidth: 80 }} value={newMenuPrice} onChange={e => setNewMenuPrice(e.target.value)} placeholder="가격" />
                  <button type="button" className="btn btn-outline-success" onClick={addMenu}>+</button>
                </div>
              </div>
            )}

            <div className="mb-3">
              <label className="form-label fw-bold small">메뉴 (AI 자동 분류)</label>
              <textarea className="form-control" rows={3} value={menuText} onChange={e => setMenuText(e.target.value)} placeholder="메뉴를 줄바꿈으로 입력" />
              <button type="button" className="btn btn-sm btn-outline-secondary mt-2" onClick={classifyMenu}>메뉴 AI 분류</button>
              {menuResult && <div className="mt-2 small text-muted" dangerouslySetInnerHTML={{ __html: menuResult }} />}
            </div>

            <div className="mb-3">
              <label className="form-label fw-bold small">설명</label>
              <textarea className="form-control" rows={4} value={description} onChange={e => setDescription(e.target.value)} />
            </div>

            <div className="mb-3">
              <label className="form-label fw-bold small">위치 (마커를 드래그하여 보정)</label>
              <div ref={mapRef} style={{ height: 200, borderRadius: 12 }} className="mb-2" />
              <div className="small text-muted text-center">{lat && lon ? `${lat}, ${lon}` : ''}</div>
            </div>

            <button type="submit" className="btn btn-success w-100 py-3 fw-bold" style={{ borderRadius: 12, fontSize: '1.1rem' }} disabled={submitting}>
              {submitting ? '저장 중...' : '수정 완료'}
            </button>
          </form>
        </div>
      </div>

      {/* 워터마크 모달 */}
      {watermarkTarget && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.7)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: '#fff', borderRadius: 12, maxWidth: '92vw', maxHeight: '92vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ padding: '8px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #eee' }}>
              <strong>워터마크 추가</strong>
              <button type="button" onClick={() => setWatermarkTarget('')} style={{ border: 'none', background: 'none', fontSize: '1.3rem' }}>&times;</button>
            </div>
            <div style={{ padding: 12 }}>
              <div className="mb-2">
                <label className="form-label small fw-bold">워터마크 텍스트</label>
                <input type="text" className="form-control" value={watermarkText} onChange={e => setWatermarkText(e.target.value)} placeholder="예: 양평군청" />
              </div>
              <div className="mb-2">
                <label className="form-label small fw-bold">위치</label>
                <select className="form-select" value={watermarkPos} onChange={e => setWatermarkPos(e.target.value)}>
                  <option value="bottom-right">우측 하단</option>
                  <option value="bottom-left">좌측 하단</option>
                  <option value="top-right">우측 상단</option>
                  <option value="top-left">좌측 상단</option>
                  <option value="center">가운데</option>
                </select>
              </div>
              <div className="mb-2">
                <label className="form-label small fw-bold">불투명도: {Math.round(watermarkOpacity * 100)}%</label>
                <input type="range" className="form-range" min="0.1" max="1" step="0.1" value={watermarkOpacity} onChange={e => setWatermarkOpacity(parseFloat(e.target.value))} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 6, padding: 8, borderTop: '1px solid #eee' }}>
              <span style={{ flex: 1 }} />
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setWatermarkTarget('')}>취소</button>
              <button type="button" className="btn btn-success btn-sm" onClick={() => { applyWatermark(watermarkTarget); setWatermarkTarget('') }} disabled={wmApplying}>
                {wmApplying ? '적용 중...' : '워터마크 적용'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cropper 모달 */}
      {cropOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.7)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: '#fff', borderRadius: 12, maxWidth: '92vw', maxHeight: '92vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ padding: '8px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #eee' }}>
              <strong>사진 자르기</strong>
              <button type="button" onClick={() => { setCropOpen(false); if (cropperRef.current) { cropperRef.current.destroy(); cropperRef.current = null } }} style={{ border: 'none', background: 'none', fontSize: '1.3rem' }}>&times;</button>
            </div>
            <div style={{ padding: 8, overflow: 'hidden', maxHeight: '62vh' }}>
              <img ref={cropImgRef} style={{ maxWidth: '100%', display: 'block' }} />
            </div>
            <div style={{ display: 'flex', gap: 6, padding: 8, borderTop: '1px solid #eee' }}>
              <span style={{ flex: 1 }} />
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => { setCropOpen(false); if (cropperRef.current) { cropperRef.current.destroy(); cropperRef.current = null } }}>취소</button>
              <button type="button" className="btn btn-success btn-sm" onClick={applyCrop}>이 사진 사용</button>
            </div>
          </div>
        </div>
      )}

      {/* 회전 모달 */}
      {rotOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.7)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: '#fff', borderRadius: 12, maxWidth: '92vw', maxHeight: '92vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ padding: '8px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #eee' }}>
              <strong>사진 회전</strong>
              <button type="button" onClick={() => setRotOpen(false)} style={{ border: 'none', background: 'none', fontSize: '1.3rem' }}>&times;</button>
            </div>
            <div style={{ padding: 8, overflow: 'hidden', maxHeight: '62vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <img src={rotSrc} style={{ maxWidth: '80vw', maxHeight: '60vh', objectFit: 'contain', transform: `rotate(${rotAngle}deg)` }} />
            </div>
            <div style={{ display: 'flex', gap: 6, padding: 8, borderTop: '1px solid #eee' }}>
              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setRotAngle(a => (a - 90 + 360) % 360)}>90 Left</button>
              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setRotAngle(a => (a + 90) % 360)}>90 Right</button>
              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setRotAngle(0)}>Reset</button>
              <span style={{ flex: 1 }} />
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setRotOpen(false)}>취소</button>
              <button type="button" className="btn btn-success btn-sm" onClick={applyRotate}>적용</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
