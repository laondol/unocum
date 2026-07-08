import { useEffect, useState, useRef } from 'react'

interface Photo { path: string }

export default function ShareEdit() {
  const id = window.location.pathname.split('/').filter(Boolean).pop()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [photos, setPhotos] = useState<Photo[]>([])
  const [lat, setLat] = useState('')
  const [lon, setLon] = useState('')
  const [newPreviews, setNewPreviews] = useState<string[]>([])
  const [newFiles, setNewFiles] = useState<File[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [loading, setLoading] = useState(true)
  const [leafletReady, setLeafletReady] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<any>(null)
  const originalLatRef = useRef('')
  const originalLonRef = useRef('')

  useEffect(() => {
    fetch(`/api/share/report/${id}`).then(r => r.json()).then(d => {
      setTitle(d.title || '')
      setDescription(d.description || '')
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
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView([lt, ln], 15)
      return
    }
    mapInstanceRef.current = L.map(mapRef.current).setView([lt, ln], 15)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(mapInstanceRef.current)
    const marker = L.marker([lt, ln], { draggable: true }).addTo(mapInstanceRef.current)
    marker.on('dragend', (e: any) => {
      const pos = e.target.getLatLng()
      setLat(pos.lat.toFixed(7))
      setLon(pos.lng.toFixed(7))
    })
    setTimeout(() => mapInstanceRef.current?.invalidateSize(), 300)
  }, [lat, lon, leafletReady])

  function loadLeaflet() {
    if (document.getElementById('leaflet-css')) return
    const link = document.createElement('link')
    link.id = 'leaflet-css'; link.rel = 'stylesheet'
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
    document.head.appendChild(link)
    const script = document.createElement('script')
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
    script.onload = () => { setLeafletReady(true) }
    document.head.appendChild(script)
  }

  function deletePhoto(path: string) {
    if (!confirm('이 사진을 삭제하시겠습니까?')) return
    fetch(`/share-report/delete-image/${id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_path: path })
    }).then(r => r.json()).then(d => {
      if (d.status === 'success') setPhotos(prev => prev.filter(p => p.path !== path))
      else alert(d.msg || '오류')
    })
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files
    if (!files?.length) return
    const arr: File[] = []
    const urls: string[] = []
    for (const f of files) {
      arr.push(f)
      if (f.type.startsWith('image/')) urls.push(URL.createObjectURL(f))
    }
    setNewFiles(prev => [...prev, ...arr])
    setNewPreviews(prev => [...prev, ...urls])
  }

  function removeNewFile(idx: number) {
    setNewFiles(prev => prev.filter((_, i) => i !== idx))
    setNewPreviews(prev => {
      URL.revokeObjectURL(prev[idx])
      return prev.filter((_, i) => i !== idx)
    })
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (submitting) return
    setSubmitting(true)
    const fd = new FormData()
    fd.append('title', title)
    fd.append('description', description)
    fd.append('latitude', lat)
    fd.append('longitude', lon)
    fd.append('original_lat', originalLatRef.current)
    fd.append('original_lon', originalLonRef.current)
    for (const f of newFiles) fd.append('image', f)
    try {
      const res = await fetch(`/share-report/edit/${id}`, { method: 'POST', body: fd })
      const data = await res.json()
      if (data.status === 'success') {
        alert(data.msg)
        window.location.href = `/share/detail/${id}`
      } else {
        alert(data.msg || '오류')
        setSubmitting(false)
      }
    } catch (err: any) {
      alert('오류: ' + err.message)
      setSubmitting(false)
    }
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
                  <div key={i} className="position-relative">
                    <img src={p.path} style={{ width: 100, height: 100, objectFit: 'cover', borderRadius: 8 }} />
                    {photos.length > 1 && (
                      <button type="button" onClick={() => deletePhoto(p.path)}
                        className="btn btn-sm btn-danger position-absolute" style={{ top: -6, right: -6, width: 22, height: 22, padding: 0, fontSize: 12, lineHeight: '1', borderRadius: '50%' }}>×</button>
                    )}
                  </div>
                ))}
                {newPreviews.map((u, i) => (
                  <div key={`new-${i}`} className="position-relative">
                    <img src={u} style={{ width: 100, height: 100, objectFit: 'cover', borderRadius: 8, border: '2px solid #0d6efd' }} />
                    <button type="button" onClick={() => removeNewFile(i)}
                      className="btn btn-sm btn-danger position-absolute" style={{ top: -6, right: -6, width: 22, height: 22, padding: 0, fontSize: 12, lineHeight: '1', borderRadius: '50%' }}>×</button>
                  </div>
                ))}
              </div>
              <input type="file" ref={fileInputRef} className="form-control" accept="image/*" multiple onChange={onFileChange} />
            </div>
            <div className="mb-3">
              <label className="form-label fw-bold small">제목</label>
              <input type="text" className="form-control" value={title} onChange={e => setTitle(e.target.value)} />
            </div>
            <div className="mb-3">
              <label className="form-label fw-bold small">설명</label>
              <textarea className="form-control" rows={4} value={description} onChange={e => setDescription(e.target.value)} />
            </div>
            <div className="mb-3">
              <label className="form-label fw-bold small">위치 (마커를 드래그하여 보정)</label>
              <div ref={mapRef} style={{ height: 200, borderRadius: 12 }} className="mb-2" />
              <div className="small text-muted text-center">
                {lat && lon ? `${lat}, ${lon}` : ''}
              </div>
            </div>
            <button type="submit" className="btn btn-success w-100 py-3 fw-bold" style={{ borderRadius: 12, fontSize: '1.1rem' }} disabled={submitting}>
              {submitting ? '저장 중...' : '수정 완료'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
