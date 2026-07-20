import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// 마커 아이콘 fix (leaflet 기본 아이콘 깨짐 방지)
const iconCache: Record<string, L.Icon> = {}
function getIcon(color: string) {
  if (!iconCache[color]) {
    iconCache[color] = new L.Icon({
      iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
      shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
      iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41],
    })
  }
  return iconCache[color]
}

interface Notice {
  id: number; title: string; description?: string; location?: string
  latitude?: number; longitude?: number; notice_type: string; source?: string
  start_date?: string; end_date?: string; distance_km?: number
}
interface Facility {
  id: number; name: string; address?: string; latitude?: number; longitude?: number
  open_hr?: string; tel?: string; emergency_bell?: boolean; cctv?: boolean
  facility_type: string; distance_km?: number
}
interface HeritageItem {
  name: string; lat: number; lng: number; dist?: number; dist_from_home?: number; stamped?: boolean
}

function dirUrl(lat?: number, lng?: number) {
  if (lat == null || lng == null) return '#'
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`
}
function kakaoUrl(name: string, lat?: number, lng?: number) {
  if (lat == null || lng == null) return '#'
  return `https://map.kakao.com/link/to/${encodeURIComponent(name)},${lat},${lng}`
}

function MapView({ items, center, color }: { items: any[]; center: [number, number]; color: string }) {
  return (
    <MapContainer center={center} zoom={13} style={{ height: 320, width: '100%', borderRadius: 16 }} scrollWheelZoom>
      <TileLayer attribution="© OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {items.filter(i => i.latitude && i.longitude).map(i => (
        <Marker key={i.id} position={[i.latitude, i.longitude]} icon={getIcon(color)}>
          <Popup>
            <div style={{ maxWidth: 220 }}>
              <strong>{i.title || i.name}</strong>
              <div className="small text-muted">{i.location || i.address || ''}</div>
              {(i.distance_km != null) && <div className="small">내 위치에서 {i.distance_km}km</div>}
              <a className="btn btn-sm btn-outline-primary mt-1" href={dirUrl(i.latitude, i.longitude, i.title || i.name)} target="_blank" rel="noreferrer">길찾기(구글)</a>{' '}
              <a className="btn btn-sm btn-outline-success mt-1" href={kakaoUrl(i.name || i.title || '', i.latitude, i.longitude)} target="_blank" rel="noreferrer">카카오</a>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}

function useGeo() {
  const [loc, setLoc] = useState<{ lat: number; lng: number } | null>(null)
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        p => setLoc({ lat: p.coords.latitude, lng: p.coords.longitude }),
        () => {}, { enableHighAccuracy: true, timeout: 10000 }
      )
    }
  }, [])
  return loc
}

function ConstructionTab() {
  const [notices, setNotices] = useState<Notice[]>([])
  const [loading, setLoading] = useState(true)
  const [showMap, setShowMap] = useState(false)
  const geo = useGeo()
  useEffect(() => {
    fetch('/api/construction/notices').then(r => r.json()).then(d => { setNotices(d.notices || []); setLoading(false) }).catch(() => setLoading(false))
  }, [])
  const center: [number, number] = geo ? [geo.lat, geo.lng] : [37.49, 127.63]
  const labels: Record<string, string> = { traffic_incident: '교통 돌발', traffic_congestion: '교통 정체', road_construction: '도로공사', building_permit: '건축공사' }
  const colors: Record<string, string> = { traffic_incident: 'red', traffic_congestion: 'grey', road_construction: 'orange', building_permit: 'blue' }
  return (
    <div>
      <div className="d-flex justify-content-end mb-2">
        <button className="btn btn-sm btn-outline-secondary" onClick={() => setShowMap(s => !s)}>{showMap ? '목록만' : '지도 보기'}</button>
      </div>
      {showMap && <MapView items={notices} center={center} color="orange" />}
      {loading && <div className="text-center py-4"><span className="spinner-border spinner-border-sm" /></div>}
      {!loading && notices.length === 0 && <div className="text-center py-5 text-muted">현재 등록된 공사 정보가 없습니다.</div>}
      <div className="row g-3 mt-1">
        {notices.map(n => (
          <div className="col-12" key={n.id}>
            <div className="card border-0 shadow-sm" style={{ borderRadius: 16, borderLeft: `4px solid ${colors[n.notice_type] === 'red' ? '#dc3545' : colors[n.notice_type] === 'grey' ? '#6c757d' : colors[n.notice_type] === 'orange' ? '#fd7e14' : '#0d6efd'}` }}>
              <div className="card-body p-3">
                <div className="d-flex justify-content-between">
                  <h6 className="fw-bold mb-2">{n.title}</h6>
                  <span className={`badge ${colors[n.notice_type] === 'red' ? 'bg-danger' : colors[n.notice_type] === 'grey' ? 'bg-secondary' : colors[n.notice_type] === 'orange' ? 'bg-warning text-dark' : 'bg-info'}`}>{labels[n.notice_type] || n.notice_type}</span>
                </div>
                {n.description && <p className="small text-muted mb-2">{n.description.slice(0, 200)}</p>}
                <div className="d-flex gap-3 flex-wrap small text-muted">
                  {n.location && <span>위치: {n.location}</span>}
                  {n.start_date && <span>시작: {n.start_date}</span>}
                  {n.end_date && <span>종료: {n.end_date}</span>}
                  {n.distance_km != null && <span>내 위치서 {n.distance_km}km</span>}
                  {n.source && <span>출처: {n.source}</span>}
                </div>
                {n.latitude && n.longitude && (
                  <div className="mt-2">
                    <a className="btn btn-sm btn-outline-secondary" href={dirUrl(n.latitude, n.longitude, n.title)} target="_blank" rel="noreferrer">길찾기</a>{' '}
                    <a className="btn btn-sm btn-outline-success" href={kakaoUrl(n.title, n.latitude, n.longitude)} target="_blank" rel="noreferrer">카카오맵</a>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function FacilityTab() {
  const [facs, setFacs] = useState<Facility[]>([])
  const [loading, setLoading] = useState(true)
  const [showMap, setShowMap] = useState(false)
  const geo = useGeo()
  useEffect(() => {
    fetch('/api/facilities?type=toilet').then(r => r.json()).then(d => { setFacs(d.facilities || []); setLoading(false) }).catch(() => setLoading(false))
  }, [])
  const center: [number, number] = geo ? [geo.lat, geo.lng] : [37.49, 127.63]
  return (
    <div>
      <div className="alert alert-light small mb-3">생활안전지도(행정안전부) 공중화장실 정보 · 양평군 필터</div>
      <div className="d-flex justify-content-end mb-2">
        <button className="btn btn-sm btn-outline-secondary" onClick={() => setShowMap(s => !s)}>{showMap ? '목록만' : '지도 보기'}</button>
      </div>
      {showMap && <MapView items={facs} center={center} color="green" />}
      {loading && <div className="text-center py-4"><span className="spinner-border spinner-border-sm" /></div>}
      {!loading && facs.length === 0 && <div className="text-center py-5 text-muted">근처 공중화장실 정보가 없습니다.<br /><small>관리자 메뉴에서 '편의시설 갱신'으로 API 동기화가 필요합니다.</small></div>}
      <div className="row g-3 mt-1">
        {facs.map(f => (
          <div className="col-12" key={f.id}>
            <div className="card border-0 shadow-sm" style={{ borderRadius: 16, borderLeft: '4px solid #198754' }}>
              <div className="card-body p-3">
                <div className="d-flex justify-content-between">
                  <h6 className="fw-bold mb-2">{f.name}</h6>
                  {f.distance_km != null && <span className="badge bg-light text-dark">{f.distance_km}km</span>}
                </div>
                {f.address && <p className="small text-muted mb-1">{f.address}</p>}
                <div className="d-flex gap-3 flex-wrap small text-muted">
                  {f.open_hr && <span>개방: {f.open_hr}</span>}
                  {f.tel && <span>전화: {f.tel}</span>}
                  {f.emergency_bell && <span className="text-danger">비상벨</span>}
                  {f.cctv && <span className="text-primary">CCTV</span>}
                </div>
                {f.latitude && f.longitude && (
                  <div className="mt-2">
                    <a className="btn btn-sm btn-outline-secondary" href={dirUrl(f.latitude, f.longitude, f.name)} target="_blank" rel="noreferrer">길찾기</a>{' '}
                    <a className="btn btn-sm btn-outline-success" href={kakaoUrl(f.name, f.latitude, f.longitude)} target="_blank" rel="noreferrer">카카오맵</a>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function HeritageTab() {
  const geo = useGeo()
  const [items, setItems] = useState<HeritageItem[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    if (!geo) return
    setLoading(true)
    fetch(`/construction/heritage?lat=${geo.lat}&lng=${geo.lng}`).then(r => r.json()).then(d => { setItems(d); setLoading(false) }).catch(() => setLoading(false))
  }, [geo])
  if (!geo) return <div className="text-center py-4 text-muted">위치 권한이 필요합니다.</div>
  if (loading) return <div className="text-center py-4"><span className="spinner-border spinner-border-sm" /></div>
  return (
    <div className="row g-3">
      {items.map((h, i) => (
        <div className="col-12" key={i}>
          <div className="card border-0 shadow-sm" style={{ borderRadius: 16, borderLeft: '4px solid #198754' }}>
            <div className="card-body p-3">
              <h6 className="fw-bold mb-1">{h.name}</h6>
              {h.dist != null && <div className="small text-muted">내 위치서 {h.dist}km</div>}
              <div className="mt-2">
                <a className="btn btn-sm btn-outline-secondary" href={dirUrl(h.lat, h.lng, h.name)} target="_blank" rel="noreferrer">길찾기</a>
              </div>
            </div>
          </div>
        </div>
      ))}
      {items.length === 0 && <div className="text-center py-5 text-muted">근처 국가유산이 없습니다.</div>}
    </div>
  )
}

function SceneryTab() {
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    fetch('/construction/local-scenery').then(r => r.json()).then(d => { setItems(d); setLoading(false) }).catch(() => setLoading(false))
  }, [])
  if (loading) return <div className="text-center py-4"><span className="spinner-border spinner-border-sm" /></div>
  return (
    <div className="row g-2">
      {items.map((s: any) => (
        <div className="col-6 col-md-4" key={s.id}>
          <a href={`/share/detail/${s.id}`} target="_blank" className="text-decoration-none">
            <div className="card border-0 shadow-sm h-100">
              {s.image_path ? <img src={s.image_path} className="card-img-top" style={{ height: 120, objectFit: 'cover' }} alt={s.title} /> : <div className="bg-light text-center py-5">사진</div>}
              <div className="card-body p-2"><div className="small fw-bold text-truncate">{s.title}</div></div>
            </div>
          </a>
        </div>
      ))}
      {items.length === 0 && <div className="text-center py-5 text-muted">등록된 풍경 사진이 없습니다.</div>}
    </div>
  )
}

function HomeTab() {
  const geo = useGeo()
  const [content, setContent] = useState<string>('')
  useEffect(() => {
    if (!geo) return
    fetch(`/construction/home?lat=${geo.lat}&lng=${geo.lng}`).then(r => r.text()).then(setContent).catch(() => setContent('불러오기 실패'))
  }, [geo])
  if (!geo) return <div className="text-center py-4 text-muted">위치 권한이 필요합니다.</div>
  return <div dangerouslySetInnerHTML={{ __html: content }} />
}

const TABS = [
  { key: 'heritage', label: '국가유산' },
  { key: 'scenery', label: '풍경' },
  { key: 'home', label: '집으로' },
  { key: 'construction', label: '공사·건설현황' },
  { key: 'facility', label: '편의시설' },
]

export default function ConstructionPage() {
  const [tab, setTab] = useState('heritage')
  return (
    <div className="container mt-4" style={{ maxWidth: 800 }}>
      <a href="/intro" className="btn btn-sm btn-outline-secondary mb-3">← 인트로로</a>
      <h3 className="fw-bold mb-3">우리 위치기반 안내</h3>
      <ul className="nav nav-tabs mb-4">
        {TABS.map(t => (
          <li className="nav-item" key={t.key}>
            <a href="#" className={`nav-link ${tab === t.key ? 'active' : ''}`} onClick={e => { e.preventDefault(); setTab(t.key) }}>{t.label}</a>
          </li>
        ))}
      </ul>
      {tab === 'heritage' && <HeritageTab />}
      {tab === 'scenery' && <SceneryTab />}
      {tab === 'home' && <HomeTab />}
      {tab === 'construction' && <ConstructionTab />}
      {tab === 'facility' && <FacilityTab />}
    </div>
  )
}
