import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { newsApi } from '../lib/api'
import type { NewsArticle } from '../lib/types'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'
import EmptyState from '../components/common/EmptyState'

const TABS = [
  { key: 'kr_yp', label: '🇰🇷 대한민국과양평' },
  { key: 'world', label: '🌍 세계와양평' },
  { key: '', label: '📰 전체' },
]

export default function NewsList() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const tab = searchParams.get('category') || 'kr_yp'
  const page = parseInt(searchParams.get('page') || '1')
  const [articles, setArticles] = useState<NewsArticle[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [content, setContent] = useState<{ id: number; title: string; content: string; category: string } | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const data = await newsApi.list(tab || undefined, page)
      setArticles(Array.isArray(data) ? data : [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [tab, page])

  useEffect(() => { load() }, [load])

  const handleVote = async (id: number, vote: 'like' | 'dislike') => {
    try {
      const res = await newsApi.vote(id, vote)
      if (res.status === 'success') {
        setArticles(prev => prev.map(a => a.id === id ? {
          ...a,
          like_count: res.likes ?? a.like_count,
          dislike_count: res.dislikes ?? a.dislike_count,
        } : a))
      }
    } catch { /* ignore */ }
  }

  const showContent = async (id: number) => {
    try {
      const d = await newsApi.get(id)
      setContent({ id, title: d.title || '', content: d.content || '', category: d.category || '' })
    } catch { alert('본문을 불러올 수 없습니다.') }
  }

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div>
      <h3 className="fw-bold mb-4">📰 소식</h3>
      <ul className="nav nav-tabs mb-4">
        {TABS.map(t => (
          <li className="nav-item" key={t.key}>
            <button className={`nav-link ${tab === t.key ? 'active' : ''}`}
              onClick={() => setSearchParams(t.key ? { category: t.key } : {})}>
              {t.label}
            </button>
          </li>
        ))}
      </ul>

      {articles.length === 0 ? (
        <EmptyState icon="📰" title="등록된 뉴스가 없습니다." />
      ) : (
        <div className="row g-4">
          {articles.map(a => (
            <div className="col-md-6 col-lg-4" key={a.id}>
              <div className="card border-0 shadow-sm h-100" style={{ borderRadius: 18, overflow: 'hidden' }}>
                {a.image_path && (
                  <img src={a.image_path} className="card-img-top" style={{ height: 180, objectFit: 'cover' }} alt={a.title} />
                )}
                <div className="card-body d-flex flex-column">
                  <span className="badge bg-success-subtle text-success align-self-start mb-2">{a.category}</span>
                  <h6 className="fw-bold card-title mb-2">
                    <span className="text-dark text-decoration-none" style={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/news/${a.id}`)}>{a.title}</span>
                  </h6>
                  <p className="small text-muted flex-grow-1">{a.summary?.slice(0, 120)}{a.summary && a.summary.length > 120 ? '...' : ''}</p>
                  <div className="d-flex justify-content-between align-items-center mt-auto pt-2 border-top">
                    <div className="d-flex gap-1">
                      <button className="btn btn-sm btn-outline-success py-0" onClick={() => handleVote(a.id, 'like')}>
                        👍 {a.like_count ?? 0}
                      </button>
                      <button className="btn btn-sm btn-outline-danger py-0" onClick={() => handleVote(a.id, 'dislike')}>
                        👎 {a.dislike_count ?? 0}
                      </button>
                    </div>
                    <button className="btn btn-sm btn-outline-primary py-0" onClick={() => showContent(a.id)}>
                      📄 본문보기
                    </button>
                  </div>
                  <div className="d-flex gap-2 mt-2">
                    <button className="btn btn-sm btn-outline-info py-0 flex-grow-1"
                      onClick={() => navigate(`/news/${a.id}`)}>
                      💬 자세히보기
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {content && (
        <div className="modal fade show d-block" tabIndex={-1} style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
            <div className="modal-content" style={{ borderRadius: 18 }}>
              <div className="modal-header">
                <h5 className="fw-bold">{content.title}</h5>
                <button type="button" className="btn-close" onClick={() => setContent(null)} />
              </div>
              <div className="modal-body" style={{ lineHeight: 1.8 }}>{content.content}</div>
              <div className="modal-footer">
                <small className="text-muted">{content.category}</small>
                <button className="btn btn-sm btn-secondary" onClick={() => setContent(null)}>닫기</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* comment form: navigate to detail page for full interaction */}
    </div>
  )
}
