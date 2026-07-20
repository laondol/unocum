import { useEffect, useState } from 'react'

interface NearbyShare { id: number; title: string; town: string; village: string; image_path: string | null; ai_category: string; distance: number }
interface LocalNews { source: string; title: string; url: string }
interface LocalLink { name: string; url: string }
interface ConstructionItem { title: string; location: string | null; notice_type: string; start_date: string | null; end_date: string | null }
interface ReplyData { id: number; author: string; content: string; user_id: number; created_at: string }
interface CommentData { id: number; author: string; content: string; user_id: number; created_at: string; replies: ReplyData[] }

interface ShareDetailData {
  id: number; title: string; description: string
  image_path: string | null; extra_images: string
  drawing_path: string | null; video_path: string | null
  latitude: number; longitude: number
  town: string; village: string; address: string
  author_name: string; user_id: number
  ai_category: string; ai_summary: string
  ai_confidence: number; ai_region_news: string
  ai_danger_alert: boolean
  like_count: number; dislike_count: number
  status: string; created_at: string; moderation_at?: string | null
  store_suggestion_id?: number | null; store_menus?: any[]; sub_category?: string; my_role?: string
  nearby_shares: NearbyShare[]
  local_news: LocalNews[]
  local_links: LocalLink[]
  nearby_construction: ConstructionItem[]
  comments: CommentData[]
}

export default function ShareDetail() {
  const id = window.location.pathname.split('/').pop()
  const [r, setR] = useState<ShareDetailData | null>(null)
  const [myId, setMyId] = useState<number | null>(null)
  const [commentText, setCommentText] = useState('')
  const [replyTo, setReplyTo] = useState<{ id: number; author: string } | null>(null)
  const [watermarkText, setWatermarkText] = useState('')
  const [watermarkPos, setWatermarkPos] = useState('bottom-right')
  const [watermarkOpacity, setWatermarkOpacity] = useState(0.5)
  const [watermarkTarget, setWatermarkTarget] = useState('')
  const [wmApplying, setWmApplying] = useState(false)

  useEffect(() => {
    fetch(`/api/share/report/${id}`).then(r => r.json()).then(setR)
    fetch('/api/me').then(r => r.json()).then(d => { if (d.id) setMyId(d.id) }).catch(() => {})
  }, [id])

  useEffect(() => {
    if (r?.latitude && r?.longitude) {
      if (!document.getElementById('leaflet-css')) {
        const link = document.createElement('link')
        link.id = 'leaflet-css'; link.rel = 'stylesheet'
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
        document.head.appendChild(link)
      }
      if (!(window as any).L) {
        const script = document.createElement('script')
        script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
        script.onload = initMap
        document.head.appendChild(script)
      } else initMap()
    }
    function initMap() {
      setTimeout(() => {
        const L = (window as any).L
        const map = L.map('detailMap').setView([r!.latitude, r!.longitude], 15)
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map)
        L.marker([r!.latitude, r!.longitude]).addTo(map).bindPopup(r!.title || '공유 위치')
      }, 100)
    }
  }, [r])

  const vote = (type: 'like' | 'dislike') => {
    if (!confirm(type === 'like' ? '좋아요 하시겠습니까?' : '나빠요 하시겠습니까?')) return
    fetch(`/share-report/${type}/${id}`, { method: 'POST' })
      .then(r => r.json()).then(d => { if (d.status === 'success') location.reload(); else alert(d.msg || '오류') })
      .catch(e => alert('오류: ' + e))
  }

  const submitComment = (e: React.FormEvent) => {
    e.preventDefault()
    if (!commentText.trim()) return alert('내용을 입력하세요.')
    const fd = new URLSearchParams()
    fd.set('content', commentText)
    if (replyTo) fd.set('parent_id', String(replyTo.id))
    fetch(`/share/comment/${id}`, { method: 'POST', body: fd, headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
      .then(r => r.json()).then(d => {
        if (d.status === 'success') { setCommentText(''); setReplyTo(null); location.reload() }
        else alert(d.msg || '오류')
      }).catch(e => alert('오류: ' + e))
  }

  const deleteComment = (commentId: number) => {
    if (!confirm('삭제하시겠습니까?')) return
    fetch(`/share/comment/delete/${commentId}`, { method: 'POST' })
      .then(r => r.json()).then(d => { if (d.status === 'success') location.reload(); else alert(d.msg || '오류') })
      .catch(e => alert('오류: ' + e))
  }

  const mosaicShare = () => {
    if (!confirm('AI 모자이크를 적용하시겠습니까?')) return
    fetch(`/share-report/mosaic/${id}`, { method: 'POST' })
      .then(r => r.json()).then(d => { if (d.status === 'success') location.reload(); else alert(d.msg || '오류') })
      .catch(e => alert('오류: ' + e))
  }

  const applyWatermark = (imagePath: string) => {
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

  if (!r) return <div className="text-center py-5"><div className="spinner-border" /></div>

  const extraImages = r.extra_images ? r.extra_images.split(',').filter(Boolean) : []
  const catColor: Record<string, string> = { '사건': 'danger', '풍경': 'success', '맛집': 'warning' }
  const isAuthor = myId === r.user_id
  const isAdminEditTarget = (r.my_role === 'admin' || r.my_role === 'leader') && (!r.user_id || r.user_id === 0)
  const canEdit = isAuthor || isAdminEditTarget
  const isBlocked = r.status !== 'approved'

  if (isBlocked && !isAuthor) {
    return (
      <div className="container mt-4" style={{maxWidth: 700}}>
        <a href="/share" className="btn btn-sm btn-outline-secondary mb-3">← 공유마당으로</a>
        <div className="card border-0 shadow-sm" style={{borderRadius: 18}}>
          <div className="card-body p-5 text-center">
            <div className="fs-1 mb-3">🚧</div>
            <h5 className="fw-bold">아직 공개되지 않은 콘텐츠입니다</h5>
            <p className="text-muted small">검토가 완료되면 모든 회원에게 공개됩니다.</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mt-4" style={{maxWidth: 700}}>
      <a href="/share" className="btn btn-sm btn-outline-secondary mb-3">← 공유마당으로</a>

      {isBlocked && isAuthor && (
        <div className="alert alert-warning small mb-3">
          ⏳ <strong>검토 중</strong>인 콘텐츠입니다. 작성자 본인에게만 표시되며, 검열 완료 후 모든 회원에게 공개됩니다.
          {r.moderation_at && (
            <> 30일 동안 수정·보완되지 않으면 자동 삭제됩니다. (보류일: {new Date(r.moderation_at).toLocaleDateString()})</>
          )}
        </div>
      )}

      <div className="card border-0 shadow-sm mb-4" style={{borderRadius: 18}}>
        <div className="card-body p-4">
          <div className="d-flex gap-2 flex-wrap mb-3">
            <span className="badge bg-info">{r.ai_category}</span>
            <span className="badge bg-light text-dark">{r.town} {r.village}</span>
          </div>
          <h3 className="fw-bold mb-3">{r.title}</h3>

          {r.image_path && (
            <div className="row g-2 mb-3">
              <div className="col-12">
                <img src={r.image_path} className="img-fluid rounded" style={{maxHeight: 400, width: '100%', objectFit: 'cover'}} />
              </div>
              {extraImages.map((img, i) => (
                <div key={i} className="col-4 col-md-3">
                  <img src={img} className="img-fluid rounded" style={{height: 120, objectFit: 'cover', width: '100%'}} />
                </div>
              ))}
            </div>
          )}

          {r.drawing_path && <img src={r.drawing_path} className="img-fluid rounded mb-3" style={{maxHeight: 400}} />}
          {r.video_path && (
            <video controls className="w-100 rounded mb-3" style={{maxHeight: 400}}>
              <source src={r.video_path} />
            </video>
          )}

          {r.ai_summary && (
            <div className="p-3 bg-light rounded mb-3 border-start border-5 border-info">
              <strong>🤖 AI 요약:</strong><br />{r.ai_summary}
            </div>
          )}

          {r.ai_region_news && r.ai_region_news !== '관련 뉴스 없음' && (
            <div className="p-3 bg-light rounded mb-3 border-start border-5 border-info">
              <strong>📰 AI 지역 분석:</strong><br />{r.ai_region_news}
            </div>
          )}

          {r.ai_danger_alert && (
            <div className="mb-4 p-3 bg-danger bg-opacity-10 rounded border border-danger">
              <strong className="text-danger">🚨 위험/긴급 상황 감지</strong><br />
              <small className="text-muted">관리자와 책임자에게 자동 통보되었습니다.</small>
            </div>
          )}

          {r.description && <p style={{whiteSpace: 'pre-wrap'}}>{r.description}</p>}
          <hr />

          <div className="d-flex justify-content-between small text-muted">
            <span>공유자: <strong>{r.author_name}</strong></span>
            <span>{r.created_at}</span>
          </div>
          <div className="d-flex justify-content-between small text-muted">
            <span>위치: 양평군 {r.town} {r.village}</span>
            {r.ai_confidence ? <span>AI 신뢰도: {Math.round(r.ai_confidence * 100)}%</span> : null}
          </div>

          {canEdit && (
            <div className="mt-3 d-flex gap-2">
              <a href={`/share/edit/${r.id}`} className="btn btn-sm btn-outline-primary">✏️ 수정</a>
              <button onClick={() => {
                if (!confirm('정말 삭제하시겠습니까?')) return
                fetch(`/share-report/delete/${r.id}`, { method: 'POST' })
                  .then(r => r.json()).then(d => {
                    if (d.status === 'success') { alert('삭제되었습니다.'); window.location.href = '/share' }
                    else alert(d.msg || '오류')
                  }).catch(e => alert('오류: ' + e))
              }} className="btn btn-sm btn-outline-danger">🗑️ 삭제</button>
            </div>
          )}
        </div>
      </div>

      {r.nearby_shares.length > 0 && (
        <div className="mb-4 p-3 bg-light rounded border-start border-5 border-primary">
          <h6 className="fw-bold mb-2">📍 가까운 소식</h6>
          {r.nearby_shares.map(s => (
            <div key={s.id} className="d-flex align-items-center gap-2 mb-2 pb-2 border-bottom border-light">
              {s.image_path && <img src={s.image_path} className="rounded" style={{width: 50, height: 50, objectFit: 'cover'}} />}
              <div className="flex-grow-1 min-w-0">
                <a href={`/share/detail/${s.id}`} className="text-dark text-decoration-none fw-medium small d-block text-truncate">{s.title || '제목 없음'}</a>
                <span className="text-muted small">{s.town} {s.village} · {s.distance}km
                  {catColor[s.ai_category] && <span className={`badge bg-${catColor[s.ai_category]} bg-opacity-10 text-${catColor[s.ai_category]} ms-1`}>{s.ai_category}</span>}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {r.local_news.length > 0 && (
        <div className="mb-4 p-3 bg-light rounded border-start border-5 border-info">
          <h6 className="fw-bold mb-2">📰 지역 소식</h6>
          {r.local_news.slice(0, 5).map((item, i) => (
            <div key={i} className="d-flex align-items-center gap-2 mb-1 pb-1 border-bottom border-light">
              <span className="badge bg-secondary small" style={{fontSize: '0.65rem'}}>{item.source}</span>
              <a href={item.url} target="_blank" className="text-decoration-none small flex-grow-1 text-truncate">{item.title}</a>
            </div>
          ))}
          {r.local_links.length > 0 && (
            <div className="d-flex gap-1 mt-2 flex-wrap">
              {r.local_links.map((lnk, i) => (
                <a key={i} href={lnk.url} target="_blank" className="btn btn-sm btn-outline-info">{lnk.name}</a>
              ))}
            </div>
          )}
        </div>
      )}

      {r.nearby_construction.length > 0 && (
        <div className="card border-0 shadow-sm mb-4" style={{borderRadius: 18, borderLeft: '4px solid #fd7e14'}}>
          <div className="card-body p-3">
            <h6 className="fw-bold mb-2">🚧 이 근처 공사 정보</h6>
            {r.nearby_construction.slice(0, 3).map((n, i) => (
              <div key={i} className="border-bottom py-1 small">
                <span className="badge bg-warning text-dark">
                  {{'traffic_incident': '교통', 'traffic_congestion': '정체', 'road_construction': '도로', 'building_permit': '건축'}[n.notice_type] || n.notice_type}
                </span>
                <strong> {n.title}</strong>
                {n.location && <><br /><small>📍 {n.location}</small></>}
              </div>
            ))}
          </div>
        </div>
      )}

      {r.latitude && r.longitude && (
        <>
          <div className="card border-0 shadow-sm mb-4" style={{borderRadius: 18, overflow: 'hidden'}}>
            <div id="detailMap" style={{height: 300}}></div>
          </div>
          <div className="text-center mb-4">
            <a href={`https://www.google.com/maps/dir/?api=1&destination=${r.latitude},${r.longitude}`} target="_blank" className="btn btn-outline-primary">🗺️ 길찾기</a>
            <a href={`https://maps.google.com/?q=${r.latitude},${r.longitude}`} target="_blank" className="btn btn-outline-secondary ms-2">📍 구글맵</a>
          </div>
        </>
      )}

          {r.image_path && !r.video_path && isAuthor && (
        <div className="text-center mb-3">
          <button onClick={mosaicShare} className="btn btn-sm btn-warning">AI 모자이크 처리</button>
          <small className="d-block text-muted mt-1">얼굴/번호판을 자동으로 모자이크합니다</small>
          <button onClick={() => setWatermarkTarget(r.image_path || '')} className="btn btn-sm btn-info mt-2">워터마크 추가</button>
          <small className="d-block text-muted mt-1">사진에 워터마크 텍스트를 추가합니다</small>
        </div>
      )}

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

      <div className="d-flex gap-2 justify-content-center mb-4">
        <button onClick={() => vote('like')} className="btn btn-outline-success btn-lg px-4">👍 좋아요 {r.like_count}</button>
        <button onClick={() => vote('dislike')} className="btn btn-outline-danger btn-lg px-4">👎 나빠요 {r.dislike_count}</button>
      </div>

      <div className="card border-0 shadow-sm mb-4" style={{borderRadius: 18}}>
        <div className="card-body p-4">
          <h5 className="fw-bold mb-3">💬 댓글 ({r.comments.length})</h5>

          {myId ? (
            <form onSubmit={submitComment} className="mb-4">
              {replyTo && (
                <div className="small text-muted mb-2">
                  💬 {replyTo.author}님에게 답글 작성 중...
                  <button type="button" className="btn btn-sm btn-link" onClick={() => setReplyTo(null)}>취소</button>
                </div>
              )}
              <div className="mb-2 d-flex gap-2 align-items-center">
                <textarea className="form-control" rows={2} placeholder="댓글을 입력하세요..." value={commentText}
                  onChange={e => setCommentText(e.target.value)} required />
                <button type="submit" className="btn btn-primary px-3" style={{whiteSpace: 'nowrap'}}>등록</button>
              </div>
            </form>
          ) : (
            <div className="alert alert-light text-center small mb-4">
              <a href={`/login?next=/share/detail/${r.id}`} className="text-decoration-none">로그인</a> 후 댓글을 작성할 수 있습니다.
            </div>
          )}

          {r.comments.map(c => (
            <div key={c.id} className="mb-3 p-3 bg-light rounded">
              <div className="d-flex justify-content-between">
                <strong className="small">{c.author}</strong>
                <div>
                  <small className="text-muted">{c.created_at}</small>
                  {myId === c.user_id && (
                    <button onClick={() => deleteComment(c.id)} className="btn btn-sm btn-link text-danger p-0 ms-2">삭제</button>
                  )}
                </div>
              </div>
              <p className="mb-1 mt-1">{c.content}</p>
              {myId && (
                <button onClick={() => setReplyTo({id: c.id, author: c.author})} className="btn btn-sm btn-link p-0 text-primary">답글</button>
              )}
              {c.replies.length > 0 && (
                <div className="mt-2 ps-3 border-start border-3">
                  {c.replies.map(rp => (
                    <div key={rp.id} className="mb-2">
                      <div className="d-flex justify-content-between">
                        <strong className="small">↳ {rp.author}</strong>
                        <div>
                          <small className="text-muted">{rp.created_at}</small>
                          {myId === rp.user_id && (
                            <button onClick={() => deleteComment(rp.id)} className="btn btn-sm btn-link text-danger p-0 ms-2">삭제</button>
                          )}
                        </div>
                      </div>
                      <p className="mb-0 mt-1">{rp.content}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
