import { useState, useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

interface ShareReport {
  id: number
  title: string
  description: string
  latitude: number
  longitude: number
  image_path: string | null
  ai_category: string
  ai_summary: string
  town: string
  village: string
  status: string
  created_at: string
}

const CATEGORIES = ['전체', '사건', '풍경', '장소', '맛집', '기타']
const CATEGORY_EMOJI: Record<string, string> = {
  사건: '🚨', 풍경: '📸', 장소: '🏠', 맛집: '🍽️', 기타: '📌',
}

function getEmoji(cat: string) {
  return CATEGORY_EMOJI[cat] || '📌'
}

export default function ShareMapPage() {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstance = useRef<L.Map | null>(null)
  const clusterGroup = useRef<L.LayerGroup | null>(null)
  const [reports, setReports] = useState<ShareReport[]>([])
  const [filtered, setFiltered] = useState<ShareReport[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [category, setCategory] = useState('전체')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/admin/share-reports')
      if (!res.ok) throw new Error('불러오기 실패')
      const data = await res.json()
      const approved = data.filter((r: ShareReport) => r.status === 'approved' && r.latitude && r.longitude)
      setReports(approved)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    if (category === '전체') {
      setFiltered(reports)
    } else {
      setFiltered(reports.filter(r => r.ai_category === category))
    }
  }, [category, reports])

  useEffect(() => {
    if (!mapRef.current || mapInstance.current) return
    const map = L.map(mapRef.current).setView([37.5, 127.52], 12)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map)
    mapInstance.current = map
    clusterGroup.current = L.layerGroup()
    map.addLayer(clusterGroup.current)
  }, [])

  useEffect(() => {
    const cg = clusterGroup.current
    if (!cg || !mapInstance.current) return
    cg.clearLayers()
    filtered.forEach(r => {
      const emoji = getEmoji(r.ai_category)
      const icon = L.divIcon({
        html: `<div style="font-size:24px;background:rgba(255,255,255,0.85);border-radius:50%;width:40px;height:40px;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,0.2)">${emoji}</div>`,
        className: '',
        iconSize: [40, 40],
        iconAnchor: [20, 20],
      })
      const imgHtml = r.image_path
        ? `<img src="${r.image_path}" style="width:100%;height:100px;object-fit:cover;border-radius:8px;margin-bottom:6px" />`
        : ''
      const popupHtml = `
        <div style="min-width:200px">
          ${imgHtml}
          <h6 style="margin:0 0 4px;font-weight:700">${r.title}</h6>
          <div style="margin-bottom:4px"><span class="badge bg-info">${r.ai_category}</span></div>
          <div style="font-size:12px;color:#666">📍 ${r.village || r.town || ''}</div>
          <div style="font-size:12px;color:#666;margin-bottom:4px">${(r.ai_summary || r.description || '').substring(0, 80)}</div>
          <a href="/share/detail/${r.id}" style="font-size:12px">자세히 보기 →</a>
        </div>
      `
      const marker = L.marker([r.latitude, r.longitude], { icon })
      marker.bindPopup(popupHtml)
      cg.addLayer(marker)
    })
  }, [filtered])

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div className="container mt-4">
      <h4 className="fw-bold mb-3">🗺️ 공유 지도</h4>
      <div className="d-flex gap-2 mb-3 flex-wrap">
        {CATEGORIES.map(c => (
          <button
            key={c}
            className={`btn btn-sm ${category === c ? 'btn-dark' : 'btn-outline-secondary'}`}
            onClick={() => setCategory(c)}
          >
            {c !== '전체' ? `${getEmoji(c)} ` : ''}{c}
          </button>
        ))}
        <span className="small text-muted align-self-center ms-2">총 {filtered.length}개</span>
      </div>
      <div
        ref={mapRef}
        style={{ width: '100%', height: 'calc(100vh - 250px)', borderRadius: 16, overflow: 'hidden' }}
        className="shadow-sm border"
      />
    </div>
  )
}
