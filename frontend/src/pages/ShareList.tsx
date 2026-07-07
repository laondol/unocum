import { useEffect, useState } from 'react'

interface ShareItem {
  id: number; title: string; description: string
  image_path: string | null; drawing_path: string | null
  latitude: number; longitude: number
  town: string; village: string
  ai_category: string; ai_summary: string
  ai_region_news: string; ai_news_links: string
  like_count: number; dislike_count: number
  author_name: string; user_id: number
  status: string; created_at: string
}

function haversine(lat1: number, lon1: number, lat2: number, lon2: number) {
  const R = 6371
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLon = (lon2 - lon1) * Math.PI / 180
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

export default function ShareList() {
  const [items, setItems] = useState<ShareItem[]>([])
  const [towns, setTowns] = useState<string[]>([])
  const [town, setTown] = useState('')
  const [village, setVillage] = useState('')
  const [category, setCategory] = useState('')
  const [loading, setLoading] = useState(true)
  const [nearbyOpen, setNearbyOpen] = useState(false)
  const [nearbyItems, setNearbyItems] = useState<any[]>([])
  const [nearbyLoading, setNearbyLoading] = useState(false)
  const [userLoc, setUserLoc] = useState<{ lat: number; lon: number } | null>(null)
  const [myId, setMyId] = useState<number | null>(null)
  const categories = ['사건', '풍경', '장소', '맛집', '기타']

  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        pos => setUserLoc({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
        () => {},
        { enableHighAccuracy: true, timeout: 10000 }
      )
    }
    fetch('/api/me').then(r => r.json()).then(d => { if (d.id) setMyId(d.id) }).catch(() => {})
  }, [])

  useEffect(() => {
    const params = new URLSearchParams()
    if (town) params.set('town', town)
    if (village) params.set('village', village)
    if (category) params.set('category', category)
    const qs = params.toString()
    fetch(`/api/share/reports${qs ? '?' + qs : ''}`)
      .then(r => r.json())
      .then(data => {
        if (userLoc) {
          data.sort((a: ShareItem, b: ShareItem) => {
            const dA = a.latitude ? haversine(userLoc.lat, userLoc.lon, a.latitude, a.longitude) : 9999
            const dB = b.latitude ? haversine(userLoc.lat, userLoc.lon, b.latitude, b.longitude) : 9999
            return dA - dB
          })
        }
        setItems(data)
        const t = [...new Set(data.map((r: ShareItem) => r.town).filter(Boolean))] as string[]
        setTowns(t)
      })
      .finally(() => setLoading(false))
  }, [town, village, category, userLoc])

  const villages = town
    ? [...new Set(items.filter(r => r.town === town).map(r => r.village).filter(Boolean))] as string[]
    : []

  const resetFilter = () => { setTown(''); setVillage(''); setCategory('') }

  const vote = (id: number, type: 'like' | 'dislike') => {
    if (!confirm(type === 'like' ? '좋아요 하시겠습니까?' : '나빠요 하시겠습니까?')) return
    fetch(`/share-report/${type}/${id}`, { method: 'POST' })
      .then(r => r.json()).then(d => {
        if (d.status === 'success') {
          setItems(prev => prev.map(item =>
            item.id === id ? { ...item, [type === 'like' ? 'like_count' : 'dislike_count']: item[type === 'like' ? 'like_count' : 'dislike_count'] + 1 } : item
          ))
        } else alert(d.msg || '오류')
      }).catch(e => alert('오류: ' + e))
  }

  const deleteShare = (id: number) => {
    if (!confirm('정말 삭제하시겠습니까?')) return
    fetch(`/share-report/delete/${id}`, { method: 'POST' })
      .then(r => r.json()).then(d => {
        if (d.status === 'success') setItems(prev => prev.filter(r => r.id !== id))
        else alert(d.msg || '오류')
      }).catch(e => alert('오류: ' + e))
  }

  const loadNearby = () => {
    if (!navigator.geolocation) return alert('GPS를 지원하지 않습니다')
    setNearbyLoading(true)
    navigator.geolocation.getCurrentPosition(pos => {
      fetch(`/share/nearby?lat=${pos.coords.latitude}&lon=${pos.coords.longitude}&max_km=20`)
        .then(r => r.json()).then(d => {
          setNearbyItems(d.items || [])
          setNearbyOpen(true)
        }).finally(() => setNearbyLoading(false))
    }, () => { alert('GPS 권한 필요'); setNearbyLoading(false) }, { enableHighAccuracy: true, timeout: 10000 })
  }

  return (
    <div className="container mt-4">
      <h3 className="fw-bold mb-4">📍 양평 공유마당</h3>

      <div className="alert alert-success small mb-4">
        <strong>📸 사진과 🎨 그리기로 양평을 공유하세요!</strong> 사건·사고뿐만 아니라 우리 동네의 <strong>아름다운 풍경, 추천 장소, 맛집, 숨은 명소</strong> 모두 환영합니다.
        최신순으로 표시되며, 여러분의 공유가 소상공인과 이웃들에게 도움이 됩니다.
      </div>

      <div className="text-center mb-4">
        <a href="/share/report" className="btn btn-success btn-lg px-5 py-3 fw-bold shadow" style={{borderRadius:16}}>
          📸 사진/그림으로 공유하기
        </a>
        <a href="/share/map" className="btn btn-outline-primary btn-lg px-4 py-3 fw-bold shadow ms-2" style={{borderRadius:16}}>
          🗺️ 지도로 보기
        </a>
      </div>

      <div className="d-flex gap-2 mb-3">
        <button className="btn btn-outline-primary btn-sm" onClick={loadNearby} disabled={nearbyLoading}>
          📍 {nearbyLoading ? '불러오는 중...' : '내 주변 보기'}
        </button>
        {userLoc ? (
          <span className="small text-muted align-self-center">📍 현재 위치 기준 가까운 순</span>
        ) : (
          <span className="small text-muted align-self-center">⏳ 위치 수집 중...</span>
        )}
      </div>

      {nearbyOpen && (
        <div className="mb-4">
          <div className="card border-0 shadow-sm p-3" style={{borderRadius:16}}>
            <h6 className="fw-bold mb-3">📍 내 주변 공유 (20km 이내)</h6>
            {nearbyItems.length > 0 ? (
              <div className="row g-2">
                {nearbyItems.map((item: any) => (
                  <div key={item.id} className="col-6 col-md-4 col-lg-3 p-2" style={{cursor:'pointer',borderRadius:12}}
                    onClick={() => window.location.href = '/share/detail/' + item.id}>
                    <div className="d-flex gap-2 align-items-start">
                      {item.image ? <img src={item.image} style={{width:50,height:50,objectFit:'cover',borderRadius:8}} />
                        : <div style={{width:50,height:50,background:'#eee',borderRadius:8}} />}
                      <div className="small">
                        <strong>{item.title}</strong><br />
                        <span className="text-muted">{item.category} · {item.town} {item.village}</span><br />
                        <span className="text-primary">📍 {item.distance}km</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-muted small py-3 text-center">
                내 주변 20km 이내에 공유가 없습니다. 첫 공유자가 되어보세요!
              </div>
            )}
            <button className="btn btn-sm btn-outline-secondary mt-2" onClick={() => setNearbyOpen(false)}>접기</button>
          </div>
        </div>
      )}

      <div className="card border-0 shadow-sm mb-4 p-3" style={{borderRadius:16}}>
        <div className="row g-2">
          <div className="col-md-3">
            <select className="form-select" value={town} onChange={e => { setTown(e.target.value); setVillage('') }}>
              <option value="">전체 읍/면</option>
              {towns.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="col-md-3">
            <select className="form-select" value={village} onChange={e => setVillage(e.target.value)}>
              <option value="">전체 리</option>
              {villages.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
          <div className="col-md-3">
            <select className="form-select" value={category} onChange={e => setCategory(e.target.value)}>
              <option value="">전체 분류</option>
              {categories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="col-md-3 text-end">
            <button className="btn btn-outline-secondary" onClick={resetFilter}>초기화</button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-5 text-muted"><div className="spinner-border" /></div>
      ) : items.length > 0 ? (
        <div className="row g-3">
          {items.map(r => {
            const dist = userLoc && r.latitude ? haversine(userLoc.lat, userLoc.lon, r.latitude, r.longitude) : null
            return (
            <div key={r.id} className="col-12 col-md-6 col-lg-4">
              <div className="card border-0 shadow-sm h-100" style={{borderRadius:16,overflow:'hidden'}}>
                {r.image_path ? (
                  <img src={r.image_path} className="card-img-top" style={{height:160,objectFit:'cover'}} />
                ) : r.drawing_path ? (
                  <img src={r.drawing_path} className="card-img-top" style={{height:160,objectFit:'cover'}} />
                ) : (
                  <div className="bg-light d-flex align-items-center justify-content-center" style={{height:160}}>
                    <span className="text-muted">이미지 없음</span>
                  </div>
                )}
                <div className="card-body p-3 d-flex flex-column">
                  <div className="d-flex gap-1 flex-wrap mb-2">
                    <span className="badge bg-info">{r.ai_category}</span>
                    <span className="badge bg-light text-dark">{r.town} {r.village}</span>
                    {r.status !== 'approved' && myId === r.user_id && (
                      <span className={`badge ${r.status === 'flagged' ? 'bg-danger' : r.status === 'pending_person' ? 'bg-secondary' : 'bg-warning text-dark'}`}>
                        {r.status === 'pending_person' ? '인물보류' : r.status === 'flagged' ? '차단됨' : '승인대기'}
                      </span>
                    )}
                  </div>
                  <h6 className="fw-bold mb-2">{r.title}</h6>
                  <p className="small text-muted flex-grow-1 mb-2">
                    {(r.ai_summary || r.description || '').substring(0, 120)}
                  </p>

                  {r.ai_region_news && r.ai_region_news !== '관련 뉴스 없음' && (
                    <div className="mb-2 p-2 bg-light rounded small border-start border-5 border-info">
                      <strong>📰 관련 지역 소식:</strong><br />
                      {r.ai_region_news.substring(0, 150)}
                    </div>
                  )}

                  <div className="d-flex justify-content-between align-items-center pt-2 border-top">
                    <small className="text-muted">
                      📍 {r.town} {r.village}
                      {dist !== null && (
                        <span className="text-primary ms-1 fw-bold">{dist.toFixed(1)}km</span>
                      )}
                      {r.latitude && r.longitude && (
                        <a href={`https://maps.google.com/?q=${r.latitude},${r.longitude}`} target="_blank" className="text-decoration-none ms-1">(지도)</a>
                      )}
                    </small>
                    <div className="d-flex gap-1">
                      <button onClick={() => vote(r.id, 'like')} className="btn btn-sm btn-outline-success">👍 {r.like_count}</button>
                      <button onClick={() => vote(r.id, 'dislike')} className="btn btn-sm btn-outline-danger">👎 {r.dislike_count}</button>
                    </div>
                  </div>

                  <div className="d-flex justify-content-between align-items-center mt-2">
                    <a href={`/share/detail/${r.id}`} className="text-decoration-none small text-primary">자세히 보기 →</a>
                  </div>
                </div>
              </div>
            </div>
            )
          })}
        </div>
      ) : (
        <div className="text-center py-5 text-muted">
          <div className="fs-1 mb-3">📍</div>
          <p>아직 공유된 내용이 없습니다. 첫 공유의 주인공이 되어보세요!</p>
        </div>
      )}
    </div>
  )
}
