import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'
import EmptyState from '../components/common/EmptyState'

interface SearchResult {
  id: number
  title: string
  content?: string
  description?: string
  summary?: string
  created_at?: string
  type?: string
}

interface SearchResponse {
  posts?: SearchResult[]
  shares?: SearchResult[]
  news?: SearchResult[]
}

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const query = searchParams.get('q') || ''
  const [results, setResults] = useState<SearchResponse>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [input, setInput] = useState(query)

  const search = useCallback(async () => {
    if (!query.trim()) return
    setLoading(true); setError('')
    try {
      const res = await fetch(`/api/board/search?q=${encodeURIComponent(query.trim())}`)
      if (!res.ok) throw new Error('검색 실패')
      const data = await res.json()
      setResults(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '검색 중 오류가 발생했습니다.')
    } finally { setLoading(false) }
  }, [query])

  useEffect(() => { search() }, [search])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim()) {
      setSearchParams({ q: input.trim() })
    }
  }

  const truncate = (text: string, max = 100) =>
    text.length > max ? text.slice(0, max) + '...' : text

  const renderGroup = (title: string, items: SearchResult[] | undefined, linkPrefix: string) => {
    if (!items || items.length === 0) return null
    return (
      <div className="mb-4">
        <h6 className="fw-bold mb-3">{title}</h6>
        {items.map(item => (
          <div
            key={item.id}
            className="card border-0 shadow-sm mb-2"
            style={{ borderRadius: 12, cursor: 'pointer' }}
            onClick={() => navigate(`${linkPrefix}${item.id}`)}
          >
            <div className="card-body p-3">
              <h6 className="fw-bold mb-1 small">{item.title}</h6>
              <p className="small text-muted mb-1">
                {truncate(item.content || item.description || item.summary || '')}
              </p>
              {item.created_at && (
                <small className="text-muted">{new Date(item.created_at).toLocaleDateString('ko-KR')}</small>
              )}
            </div>
          </div>
        ))}
      </div>
    )
  }

  const emptyGroup = (title: string, items: SearchResult[] | undefined) => {
    if (items && items.length === 0) {
      return (
        <div className="mb-4">
          <h6 className="fw-bold mb-3 text-muted">{title}</h6>
          <EmptyState icon="🔍" title="검색 결과가 없습니다" />
        </div>
      )
    }
    return null
  }

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <h4 className="fw-bold mb-4">검색</h4>
      <form onSubmit={handleSubmit} className="mb-4">
        <div className="input-group">
          <input
            className="form-control"
            placeholder="검색어를 입력하세요..."
            value={input}
            onChange={e => setInput(e.target.value)}
          />
          <button className="btn btn-success" type="submit">검색</button>
        </div>
      </form>

      {loading && <Loading text="검색 중..." />}
      {error && <ErrorMessage message={error} onRetry={search} />}

      {!loading && !error && query && (
        <>
          {renderGroup('제안', results.posts, '/post/')}
          {renderGroup('공유', results.shares, '/share/detail/')}
          {renderGroup('소식', results.news, '/news/')}

          {(!results.posts || results.posts.length === 0) &&
           (!results.shares || results.shares.length === 0) &&
           (!results.news || results.news.length === 0) && (
            <EmptyState icon="🔍" title={`"${query}"에 대한 검색 결과가 없습니다`} />
          )}

          {results.posts?.length === 0 && emptyGroup('제안', results.posts)}
          {results.shares?.length === 0 && emptyGroup('공유', results.shares)}
          {results.news?.length === 0 && emptyGroup('소식', results.news)}
        </>
      )}

      {!loading && !query && (
        <EmptyState icon="🔍" title="검색어를 입력하세요" message="원하는 정보를 검색해보세요." />
      )}
    </div>
  )
}
