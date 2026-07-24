import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Loading from '../components/common/Loading'

export default function AdminStoreEdit() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)

  const [name, setName] = useState('')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [town, setTown] = useState('')
  const [village, setVillage] = useState('')
  const [ourLink, setOurLink] = useState('')
  const [storeHomepage, setStoreHomepage] = useState('')
  const [smartplace, setSmartplace] = useState('')

  useEffect(() => {
    if (!id) return
    const load = async () => {
      try {
        const res = await fetch('/api/admin/stores')
        if (!res.ok) throw new Error()
        const data = await res.json()
        const store = Array.isArray(data) ? data.find((s: { id: number }) => s.id === Number(id)) : null
        if (store) {
          setName(store.name || '')
          setLatitude(store.latitude != null ? String(store.latitude) : '')
          setLongitude(store.longitude != null ? String(store.longitude) : '')
          setTown(store.town || '')
          setVillage(store.village || '')
          setOurLink(store.our_link || '')
          setStoreHomepage(store.store_homepage || '')
          setSmartplace(store.smartplace || '')
        }
      } catch { alert('데이터를 불러오는데 실패했습니다.') }
      finally { setLoading(false) }
    }
    load()
  }, [id])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) { alert('가게 이름을 입력하세요.'); return }
    setSaving(true)
    try {
      const fd = new FormData()
      fd.append('name', name.trim())
      fd.append('latitude', latitude)
      fd.append('longitude', longitude)
      fd.append('town', town)
      fd.append('village', village)
      fd.append('our_link', ourLink)
      fd.append('store_homepage', storeHomepage)
      fd.append('smartplace', smartplace)

      const url = isEdit ? `/admin/stores/edit/${id}` : '/admin/stores/new'
      const res = await fetch(url, { method: 'POST', body: fd })
      if (res.ok || res.redirected) {
        navigate('/admin/stores')
      } else {
        alert('저장 실패')
      }
    } catch { alert('저장 중 오류가 발생했습니다.') }
    finally { setSaving(false) }
  }

  if (loading) return <Loading />

  return (
    <div className="container mt-4" style={{ maxWidth: 600 }}>
      <a href="/admin/stores" className="btn btn-sm btn-outline-secondary mb-3">← 가게 목록</a>
      <h4 className="fw-bold mb-3">{isEdit ? '가게 수정' : '가게 등록'}</h4>

      <form onSubmit={handleSubmit} className="card border-0 shadow-sm p-3" style={{ borderRadius: 16 }}>
        <div className="mb-3">
          <label className="form-label small fw-bold">🏪 가게 이름</label>
          <input type="text" className="form-control" value={name} onChange={e => setName(e.target.value)} required />
        </div>
        <div className="row g-2 mb-3">
          <div className="col-6">
            <label className="form-label small fw-bold">위도</label>
            <input type="text" className="form-control" value={latitude} onChange={e => setLatitude(e.target.value)} placeholder="37.12345" />
          </div>
          <div className="col-6">
            <label className="form-label small fw-bold">경도</label>
            <input type="text" className="form-control" value={longitude} onChange={e => setLongitude(e.target.value)} placeholder="127.12345" />
          </div>
        </div>
        <div className="row g-2 mb-3">
          <div className="col-6">
            <label className="form-label small fw-bold">읍/면</label>
            <input type="text" className="form-control" value={town} onChange={e => setTown(e.target.value)} placeholder="양서면" />
          </div>
          <div className="col-6">
            <label className="form-label small fw-bold">리</label>
            <input type="text" className="form-control" value={village} onChange={e => setVillage(e.target.value)} placeholder="양수리" />
          </div>
        </div>
        <hr />
        <p className="small text-muted mb-2">{'🔗 링크 (우선순위: 자체소개 > 가게홈피 > 스마트플레이스)'}</p>
        <div className="mb-2">
          <label className="form-label small fw-bold">1순위: 자체 사이트 가게소개 링크</label>
          <input type="url" className="form-control form-control-sm" value={ourLink} onChange={e => setOurLink(e.target.value)} placeholder="https://함께사는양평.com/store/..." />
        </div>
        <div className="mb-2">
          <label className="form-label small fw-bold">2순위: 가게 자체 홈페이지</label>
          <input type="url" className="form-control form-control-sm" value={storeHomepage} onChange={e => setStoreHomepage(e.target.value)} placeholder="https://..." />
        </div>
        <div className="mb-3">
          <label className="form-label small fw-bold">3순위: 네이버 스마트플레이스</label>
          <input type="url" className="form-control form-control-sm" value={smartplace} onChange={e => setSmartplace(e.target.value)} placeholder="https://naver.me/..." />
        </div>
        <button type="submit" className="btn btn-success w-100" disabled={saving}>
          {saving ? '저장 중...' : '저장'}
        </button>
      </form>
    </div>
  )
}
