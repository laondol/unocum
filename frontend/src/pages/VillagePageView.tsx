import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

interface PageData {
  id: number
  myeon: string
  ri: string
  title: string
  content: string
  visibility: string
  created_at?: string
}

export default function VillagePageView() {
  const { tmyeon, tri } = useParams<{ tmyeon: string; tri: string }>()
  const [page, setPage] = useState<PageData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!tmyeon || !tri) return
    const load = async () => {
      setLoading(true); setError('')
      try {
        const res = await fetch(`/api/village/page?myeon=${encodeURIComponent(tmyeon)}&ri=${encodeURIComponent(tri)}`)
        if (!res.ok) {
          if (res.status === 404) throw new Error('페이지를 찾을 수 없습니다.')
          throw new Error(`HTTP ${res.status}`)
        }
        const data = await res.json()
        setPage(data)
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : '불러오기 실패')
      } finally { setLoading(false) }
    }
    load()
  }, [tmyeon, tri])

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} />
  if (!page) return <ErrorMessage message="페이지를 불러올 수 없습니다." />

  return (
    <div className="container py-4" style={{ maxWidth: 900 }}>
      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h4 className="fw-bold mb-3">{page.title}</h4>
          <div className="mb-3 small text-muted">
            {page.myeon} {page.ri} | {page.created_at ? new Date(page.created_at).toLocaleDateString('ko-KR') : ''}
          </div>
          <hr />
          <div className="village-content" dangerouslySetInnerHTML={{ __html: page.content }} />
        </div>
      </div>
    </div>
  )
}
