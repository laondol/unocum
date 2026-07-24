import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function FriendsMap() {
  const navigate = useNavigate()

  useEffect(() => {
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
    document.head.appendChild(link)
    const script = document.createElement('script')
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
    script.onload = () => initMap()
    document.head.appendChild(script)
    return () => {
      document.head.removeChild(link)
      document.head.removeChild(script)
    }
  }, [])

  const initMap = () => {
    const L = (window as unknown as Record<string, unknown>).L as unknown as {
      map: (el: string, opts?: unknown) => unknown
      tileLayer: (url: string, opts?: Record<string, unknown>) => unknown
      marker: (latlng: [number, number]) => { addTo: (map: unknown) => { bindPopup: (html: string) => unknown } }
      featureGroup: (markers: unknown[]) => { getBounds: () => unknown }
    }
    const map: any = L.map('map')
    map.setView([37.5, 127.5], 11)
    ;(L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: '© OpenStreetMap',
    }) as any).addTo(map)

    fetch('/friends/list')
      .then(r => r.json())
      .then((d: { friends?: { id: number; name: string; town: string; village: string }[] }) => {
        const friends = d.friends || []
        const list = document.getElementById('friend-list')
        if (friends.length === 0) {
          if (list) list.innerHTML = '<div class="text-center text-muted py-4">등록된 벗이 없습니다.</div>'
          return
        }
        if (list) list.innerHTML = ''
        friends.forEach(f => {
          if (list) {
            const col = document.createElement('div')
            col.className = 'col-md-4 col-sm-6'
            col.innerHTML = `
              <div class="card border-0 shadow-sm h-100" style="border-radius: 14px;">
                <div class="card-body p-3">
                  <h6 class="fw-bold mb-1">${f.name}</h6>
                  <small class="text-muted">📍 ${f.town || ''} ${f.village || ''}</small>
                </div>
              </div>
            `
            list.appendChild(col)
          }
        })
      })
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <button className="btn btn-sm btn-outline-secondary mb-3" onClick={() => navigate('/friends')}>← 벗관리로</button>
      <h4 className="fw-bold mb-3">벗 위치 지도</h4>
      <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: 18, overflow: 'hidden' }}>
        <div id="map" style={{ height: 500 }} />
      </div>
      <div className="row g-3" id="friend-list" />
    </div>
  )
}
