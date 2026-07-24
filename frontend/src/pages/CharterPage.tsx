import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

export default function CharterPage() {
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res = await api.get<{ content?: string }>('/api/page/charter')
      setContent(res.content || '')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div className="container py-4" style={{ maxWidth: 800 }}>
      <h3 className="fw-bold text-center mb-4">📜 정관 (사회적협동조합 제안)</h3>
      <div className="card border-0 shadow-sm" style={{ borderRadius: 18 }}>
        <div className="card-body p-4" dangerouslySetInnerHTML={{ __html: content }} />
      </div>
      <div className="text-center mt-4">
        <Link to="/intro" className="btn btn-sm btn-outline-secondary">← 사업소개</Link>
      </div>
    </div>
  )
}
