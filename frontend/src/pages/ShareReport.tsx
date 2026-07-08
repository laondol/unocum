import { useRef, useState, useEffect } from 'react'

export default function ShareReport() {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [lat, setLat] = useState('')
  const [lon, setLon] = useState('')
  const [locationStatus, setLocationStatus] = useState('위치 수집 중... (브라우저 권한 허용 필요)')
  const [addressDetail, setAddressDetail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [cameraReady, setCameraReady] = useState(true)
  const [previews, setPreviews] = useState<string[]>([])
  const [cameraPreview, setCameraPreview] = useState<string | null>(null)
  const [videoPreview, setVideoPreview] = useState<string | null>(null)
  const [canvasVisible, setCanvasVisible] = useState(false)
  const [cameraFile, setCameraFile] = useState<File | null>(null)
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [videoFileUpload, setVideoFileUpload] = useState<File | null>(null)
  const [videoUploadPreview, setVideoUploadPreview] = useState<string | null>(null)
  const [hasContent, setHasContent] = useState(false)

  const canvasRef = useRef<HTMLCanvasElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)
  const videoInputRef = useRef<HTMLInputElement>(null)
  const videoFileInputRef = useRef<HTMLInputElement>(null)
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<any>(null)
  const markerRef = useRef<any>(null)
  const drawingRef = useRef(false)

  const ready = hasContent && lat !== '' && lon !== ''

  useEffect(() => {
    loadLeaflet()
    getLocation()
    checkCamera()
  }, [])

  useEffect(() => {
    if (canvasVisible) setTimeout(initCanvas, 100)
  }, [canvasVisible])

  function loadLeaflet() {
    if (document.getElementById('leaflet-css')) return
    const link = document.createElement('link')
    link.id = 'leaflet-css'; link.rel = 'stylesheet'
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
    document.head.appendChild(link)
    const script = document.createElement('script')
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
    script.onload = () => { if (lat && lon) initMap() }
    document.head.appendChild(script)
  }

  function initMap() {
    const L = (window as any).L
    if (!L || !mapRef.current) return
    const lt = parseFloat(lat); const ln = parseFloat(lon)
    if (isNaN(lt) || isNaN(ln)) return
    if (!mapInstanceRef.current) {
      mapInstanceRef.current = L.map(mapRef.current).setView([lt, ln], 15)
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(mapInstanceRef.current)
      markerRef.current = L.marker([lt, ln]).addTo(mapInstanceRef.current)
    } else {
      mapInstanceRef.current.setView([lt, ln], 15)
      markerRef.current.setLatLng([lt, ln])
    }
    setTimeout(() => mapInstanceRef.current?.invalidateSize(), 300)
  }

  function getLocation() {
    if (!navigator.geolocation) {
      setLocationStatus('이 브라우저는 위치정보를 지원하지 않습니다.')
      return
    }
    navigator.geolocation.getCurrentPosition(
      pos => {
        const lt = pos.coords.latitude.toFixed(6)
        const ln = pos.coords.longitude.toFixed(6)
        setLat(lt)
        setLon(ln)
        setLocationStatus('주소 변환 중...')
        setTimeout(() => initMap(), 500)
        fetch(`/api/reverse-geocode?lat=${lt}&lon=${ln}`)
          .then(r => r.json())
          .then(data => {
            setAddressDetail(data.address || '위치 수집 완료')
          })
          .catch(() => {
            setAddressDetail('위치 수집 완료')
          })
      },
      err => {
        setLocationStatus('위치 수집 실패: ' + err.message)
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    )
  }

  function checkCamera() {
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraReady(false)
      return
    }
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => stream.getTracks().forEach(t => t.stop()))
      .catch(() => setCameraReady(false))
  }

  function onCameraCapture(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setCameraFile(file)
    setCameraPreview(URL.createObjectURL(file))
    setHasContent(true)
  }

  function onVideoCapture(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setVideoFile(file)
    setVideoPreview(URL.createObjectURL(file))
    setHasContent(true)
  }

  function onVideoFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setVideoFileUpload(file)
    setVideoUploadPreview(URL.createObjectURL(file))
    setHasContent(true)
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files
    if (!files?.length) return
    setHasContent(true)
    const urls: string[] = []
    for (const f of files) {
      if (f.type.startsWith('image/')) urls.push(URL.createObjectURL(f))
    }
    setPreviews(urls)
  }

  function initCanvas() {
    const c = canvasRef.current
    if (!c) return
    const rect = c.parentElement?.getBoundingClientRect()
    c.width = rect ? rect.width : 400
    c.height = 300
    const ctx = c.getContext('2d')
    if (!ctx) return

    function getPos(e: MouseEvent | Touch) { const r = c!.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top } }

    const onStart = (e: any) => {
      drawingRef.current = true
      const p = getPos(e.touches ? e.touches[0] : e)
      ctx.beginPath(); ctx.moveTo(p.x, p.y)
      setHasContent(true)
    }
    const onMove = (e: any) => {
      if (!drawingRef.current) return
      const p = getPos(e.touches ? e.touches[0] : e)
      ctx.lineWidth = 3; ctx.lineCap = 'round'; ctx.strokeStyle = '#333'
      ctx.lineTo(p.x, p.y); ctx.stroke(); ctx.beginPath(); ctx.moveTo(p.x, p.y)
    }
    const onEnd = () => { drawingRef.current = false; ctx.beginPath() }

    c.addEventListener('mousedown', onStart)
    c.addEventListener('mousemove', onMove)
    c.addEventListener('mouseup', onEnd)
    c.addEventListener('mouseleave', onEnd)
    c.addEventListener('touchstart', onStart, { passive: false })
    c.addEventListener('touchmove', onMove, { passive: false })
    c.addEventListener('touchend', onEnd)
  }

  function clearCanvas() {
    const c = canvasRef.current
    if (!c) return
    c.getContext('2d')?.clearRect(0, 0, c.width, c.height)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!ready || submitting) return
    setSubmitting(true)

    const fd = new FormData()
    if (cameraFile) fd.append('image', cameraFile)
    if (fileInputRef.current?.files) {
      for (const f of fileInputRef.current.files) fd.append('image', f)
    }
    if (videoFile) {
      fd.append('video', videoFile)
    }
    if (videoFileUpload) {
      fd.append('video', videoFileUpload)
    }
    fd.append('title', title)
    fd.append('description', description)
    fd.append('latitude', lat)
    fd.append('longitude', lon)

    const c = canvasRef.current
    if (c) {
      const dataUrl = c.toDataURL('image/png')
      if (dataUrl.length > 2000) fd.append('drawing_data', dataUrl)
    }

    try {
      const res = await fetch('/share-report', { method: 'POST', body: fd })
      if (!res.ok) {
        const text = await res.text()
        alert('서버 오류: ' + (text.includes('<') ? '요청 처리 중 오류가 발생했습니다. 파일 크기가 너무 크거나 올바르지 않은 형식입니다.' : text))
        setSubmitting(false); return
      }
      const data = await res.json()
      if (data.status === 'success') {
        alert(data.msg)
        window.location.href = '/share'
      } else {
        alert(data.msg || '오류 발생')
        setSubmitting(false)
      }
    } catch (err: any) {
      alert('서버 연결 실패: 서버가 응답하지 않습니다. (파일 용량이 너무 크거나 서버 오류)')
      setSubmitting(false)
    }
  }

  return (
    <div className="container-fluid px-3 py-3" style={{ maxWidth: '100%' }}>
      <h4 className="fw-bold mb-3 text-center">공유하기</h4>
      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-3">
          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <div className="row g-2">
                <div className="col-6">
                  <input type="file" ref={cameraInputRef} accept="image/*" capture="environment" onChange={onCameraCapture} style={{ display: 'none' }} />
                  <button type="button" className="btn btn-success w-100 py-3 fw-bold" style={{ borderRadius: 12, fontSize: '1.1rem' }}
                    onClick={() => cameraInputRef.current?.click()} disabled={!cameraReady}>
                    사진촬영
                  </button>
                </div>
                <div className="col-6">
                  <input type="file" ref={videoInputRef} accept="video/*" capture="environment" onChange={onVideoCapture} style={{ display: 'none' }} />
                  <button type="button" className="btn btn-danger w-100 py-3 fw-bold" style={{ borderRadius: 12, fontSize: '1.1rem' }}
                    onClick={() => videoInputRef.current?.click()} disabled={!cameraReady}>
                    동영상
                  </button>
                </div>
              </div>
              {cameraPreview && (
                <div className="mt-2 text-center">
                  <img src={cameraPreview} className="img-fluid rounded" style={{ maxHeight: 300, objectFit: 'contain' }} />
                  <button type="button" className="btn btn-sm btn-outline-danger mt-1" onClick={() => { setCameraPreview(null); setCameraFile(null); setHasContent(previews.length > 0 || videoFile !== null) }}>삭제</button>
                </div>
              )}
              {videoPreview && (
                <div className="mt-2 text-center">
                  <video src={videoPreview} controls className="w-100 rounded" style={{ maxHeight: 300 }} />
                  <button type="button" className="btn btn-sm btn-outline-danger mt-1" onClick={() => { setVideoPreview(null); setVideoFile(null); setHasContent(cameraFile !== null || videoFileUpload !== null || previews.length > 0) }}>삭제</button>
                </div>
              )}
            </div>
            <div className="mb-3">
              <span className="fw-bold small d-block mb-1">동영상 파일 업로드</span>
              <input type="file" ref={videoFileInputRef} className="form-control" accept="video/mp4,video/avi,video/mov,video/mkv,video/webm" onChange={onVideoFileUpload} />
              {videoUploadPreview && (
                <div className="mt-2 text-center">
                  <video src={videoUploadPreview} controls className="w-100 rounded" style={{ maxHeight: 300 }} />
                  <button type="button" className="btn btn-sm btn-outline-danger mt-1" onClick={() => { setVideoUploadPreview(null); setVideoFileUpload(null); setHasContent(cameraFile !== null || videoFile !== null || previews.length > 0) }}>삭제</button>
                </div>
              )}
            </div>
            <div className="mb-3">
              <span className="fw-bold small d-block mb-1">파일 업로드</span>
              <input type="file" ref={fileInputRef} className="form-control" accept="image/*" multiple onChange={onFileChange} />
              {previews.length > 0 && (
                <div className="mt-2 d-flex flex-wrap gap-1">
                  {previews.map((u, i) => (
                    <img key={i} src={u} style={{ width: 80, height: 80, objectFit: 'cover', borderRadius: 8, border: '1px solid #eee' }} />
                  ))}
                </div>
              )}
            </div>
            <div className="mb-3">
              <label className="form-label fw-bold small">직접 그리기</label>
              <button type="button" className="btn btn-sm btn-outline-secondary mb-2" onClick={() => setCanvasVisible(!canvasVisible)}>
                그리기 열기/닫기
              </button>
              {canvasVisible && (
                <div>
                  <canvas ref={canvasRef} style={{ border: '1px solid #ccc', background: 'white', cursor: 'crosshair', borderRadius: 12, width: '100%', height: 300 }} />
                  <div className="mt-1">
                    <button type="button" className="btn btn-sm btn-light" onClick={clearCanvas}>지우기</button>
                  </div>
                </div>
              )}
            </div>
            <div className="mb-3">
              <label className="form-label fw-bold small">제목 (선택)</label>
              <input type="text" className="form-control" placeholder="예: 양근리 벚꽃길, 용문산 등산로 풍경" value={title} onChange={e => setTitle(e.target.value)} />
            </div>
            <div className="mb-3">
              <label className="form-label fw-bold small">설명 (선택)</label>
              <textarea className="form-control" rows={3} placeholder="자세한 내용이 있으면 적어주세요." value={description} onChange={e => setDescription(e.target.value)} />
            </div>
            <div className="mb-3">
              <label className="form-label fw-bold small">현재 위치</label>
              <div className={`mb-2 text-center small ${lat && lon ? 'text-success' : 'text-muted'}`}>{addressDetail || locationStatus}</div>
              <div ref={mapRef} style={{ height: 200, borderRadius: 12, display: lat && lon ? 'block' : 'none' }} className="mb-2" />
            </div>
            <button type="submit" className="btn btn-success w-100 py-3 fw-bold" style={{ borderRadius: 12, fontSize: '1.1rem' }}
              disabled={!ready || submitting}>
              {submitting ? '접수 중...' : ready ? '공유 접수하기' : !hasContent ? '사진/동영상을 선택해 주세요' : '위치 확인 중...'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
