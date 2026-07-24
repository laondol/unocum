import { useState, useEffect } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

export default function StoreDetailPage() {
  const { storeName } = useParams<{ storeName: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const town = searchParams.get('town') || ''
  const village = searchParams.get('village') || ''
  const [html, setHtml] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!storeName) { setError('가게명이 누락되었습니다.'); setLoading(false); return }
    const fetchStore = async () => {
      setLoading(true); setError('')
      try {
        const params = new URLSearchParams()
        if (town) params.set('town', town)
        if (village) params.set('village', village)
        const res = await fetch(`/construction/store/${encodeURIComponent(storeName)}?${params.toString()}`)
        if (!res.ok) { setError('가게 정보를 불러올 수 없습니다.'); return }
        const text = await res.text()
        setHtml(text)
      } catch { setError('서버 연결 실패') }
      finally { setLoading(false) }
    }
    fetchStore()
  }, [storeName, town, village])

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={() => window.location.reload()} />

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <div className="mb-3">
        <button className="btn btn-sm btn-outline-secondary" onClick={() => navigate('/construction')}>← 위치기반안내</button>
      </div>
      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h4 className="fw-bold mb-1">{decodeURIComponent(storeName || '')}</h4>
          {town && <div className="text-muted small mb-3">{town} {village}</div>}
          <div dangerouslySetInnerHTML={{ __html: html }} />
        </div>
      </div>
    </div>
  )
}
