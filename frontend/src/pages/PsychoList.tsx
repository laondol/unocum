import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { psychoApi } from '../lib/api'
import type { PsychoPost } from '../lib/types'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'
import EmptyState from '../components/common/EmptyState'

export default function PsychoList() {
  const navigate = useNavigate()
  const [posts, setPosts] = useState<PsychoPost[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const data = await psychoApi.posts()
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
        <h4 className="fw-bold mb-0">심리상담 게시판</h4>
        <button className="btn btn-sm btn-success" onClick={() => navigate('/psycho/write')}>상담 글쓰기</button>
      </div>
      <p className="text-muted small mb-3">비회원도 이메일 인증으로 질문할 수 있습니다. 답변 등록 시 입력하신 이메일로 알림이 발송됩니다.</p>

      {posts.length === 0 ? (
        <EmptyState icon="📋" title="상담 글이 없습니다." />
      ) : (
        <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0 small">
              <thead className="table-light">
                <tr><th style={{ width: '5%' }}>#</th><th style={{ width: '45%' }}>제목</th><th style={{ width: '15%' }}>작성자</th><th style={{ width: '15%' }}>답변</th><th style={{ width: '20%' }}>작성일</th></tr>
              </thead>
              <tbody>
                {posts.map(p => (
                  <tr key={p.id}>
                    <td className="text-muted">{p.id}</td>
                    <td>
                      <span className="fw-bold text-decoration-none" style={{ cursor: 'pointer' }}
                        onClick={() => navigate(`/psycho/${p.id}`)}>
                        {p.title}
                      </span>
                    </td>
                    <td>{(p.author_name || '익명').slice(0, 2)}**</td>
                    <td>
                      {p.answer ? <span className="badge bg-success">답변완료</span>
                        : <span className="badge bg-secondary">대기중</span>}
                    </td>
                    <td className="text-muted">{p.created_at ? new Date(p.created_at).toLocaleDateString('ko-KR') : ''}</td>
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
