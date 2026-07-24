import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

interface NewsItem {
  id: number
  title: string
  summary?: string
  source_name?: string
  category?: string
  image_path?: string
  like_count?: number
  dislike_count?: number
  created_at?: string
}

const TABS = [
  { key: 'world', label: '🌍 세계와양평' },
  { key: 'kr_yp', label: '🇰🇷 대한민국과양평' },
  { key: '', label: '📰 전체' },
]

export default function NewsTabsPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('world')
  const [articles, setArticles] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const params = new URLSearchParams()
      if (tab) params.set('category', tab)
      const res = await fetch(`/api/news?${params.toString()}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setArticles(Array.isArray(data) ? data : [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [tab])

  useEffect(() => { load() }, [load])

  const handleVote = async (id: number, vote: 'like' | 'dislike') => {
    try {
      const res = await fetch(`/news/${vote}/${id}`, { method: 'POST', credentials: 'include' })
      const data = await res.json()
      if (data.status === 'success') {
        setArticles(prev => prev.map(a => a.id === id ? {
          ...a,
          like_count: data.likes ?? a.like_count,
          dislike_count: data.dislikes ?? a.dislike_count,
        } : a))
      }
    } catch { /* ignore */ }
  }

  return (
    <div>
      <h3 className="fw-bold mb-4">📰 소식</h3>
      <ul className="nav nav-tabs mb-4">
        {TABS.map(t => (
          <li className="nav-item" key={t.key}>
            <button className={`nav-link ${tab === t.key ? 'active fw-bold' : ''}`}
              onClick={() => setTab(t.key)}>
              {t.label}
            </button>
          </li>
        ))}
      </ul>

      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorMessage message={error} onRetry={load} />
      ) : articles.length === 0 ? (
        <div className="text-center py-5 text-muted">등록된 뉴스가 없습니다.</div>
      ) : (
        <div className="row g-4 row-cols-1 row-cols-md-2 row-cols-lg-3">
          {articles.map(a => (
            <div className="col" key={a.id}>
              <div className="card border-0 shadow-sm h-100" style={{ borderRadius: 18, overflow: 'hidden', cursor: 'pointer' }}
                onClick={() => navigate(`/news/${a.id}`)}>
                {a.image_path && (
                  <img src={a.image_path} className="card-img-top" style={{ height: 180, objectFit: 'cover' }} alt={a.title} />
                )}
                <div className="card-body d-flex flex-column">
                  <span className="badge bg-success-subtle text-success align-self-start mb-2">{a.category}</span>
                  <h6 className="fw-bold card-title mb-2">{a.title}</h6>
                  <p className="small text-muted flex-grow-1">
                    {a.summary ? (a.summary.length > 120 ? a.summary.slice(0, 120) + '...' : a.summary) : ''}
                  </p>
                  <div className="d-flex justify-content-between align-items-center mt-auto pt-2 border-top">
                    <small className="text-muted">{a.source_name || ''}</small>
                    <div className="d-flex gap-1" onClick={e => e.stopPropagation()}>
                      <button className="btn btn-sm btn-outline-success py-0" onClick={() => handleVote(a.id, 'like')}>
                        👍 {a.like_count ?? 0}
                      </button>
                      <button className="btn btn-sm btn-outline-danger py-0" onClick={() => handleVote(a.id, 'dislike')}>
                        👎 {a.dislike_count ?? 0}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
