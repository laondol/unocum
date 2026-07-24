import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { legalApi } from '../lib/api'
import type { LegalPost } from '../lib/types'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'
import EmptyState from '../components/common/EmptyState'

export default function LegalList() {
  const navigate = useNavigate()
  const [posts, setPosts] = useState<LegalPost[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const data = await legalApi.posts()
      setPosts(Array.isArray(data) ? data : [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h4 className="fw-bold mb-0">법률상담 게시판</h4>
        <button className="btn btn-sm btn-success" onClick={() => navigate('/legal/write')}>상담 글쓰기</button>
      </div>

      {posts.length === 0 ? (
        <EmptyState icon="📋" title="등록된 상담글이 없습니다." />
      ) : (
        <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0 small">
              <thead className="table-light">
                <tr><th>#</th><th>제목</th><th>작성자</th><th>상태</th><th>작성일</th></tr>
              </thead>
              <tbody>
                {posts.map(p => (
                  <tr key={p.id}>
                    <td>{p.id}</td>
                    <td>
                      <span className="text-decoration-none" style={{ cursor: 'pointer', color: 'var(--bs-body-color)' }}
                        onClick={() => navigate(`/legal/${p.id}`)}>
                        {p.title}
                      </span>
                    </td>
                    <td>{p.author_name || '익명'}</td>
                    <td>
                      {p.answer ? <span className="badge bg-success">답변완료</span>
                        : p.status === 'flagged' ? <span className="badge bg-danger">보류</span>
                        : <span className="badge bg-secondary">대기</span>}
                    </td>
                    <td>{p.created_at ? new Date(p.created_at).toLocaleDateString('ko-KR') : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
