import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import type { Post } from '../lib/types'
import { useAuth } from '../contexts/AuthContext'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

function getStatusBadge(p: Post) {
  if (p.total_score !== undefined && p.total_score <= -50) {
    return <span className="badge bg-danger p-2">🚨 보완 필요(격리됨)</span>
  }
  if (p.is_forced_approved) {
    return <span className="badge bg-success-subtle text-success p-2">🟢 강제승인</span>
  }
  if (p.ai_score === 0) {
    return <span className="badge bg-secondary p-2">🔍 검토전</span>
  }
  const createdAt = p.created_at ? new Date(p.created_at).getTime() : 0
  const now = Date.now()
  if (createdAt && now - createdAt < 48 * 60 * 60 * 1000) {
    return <span className="badge bg-warning text-dark p-2">⏳ 심사 중 (시차 격리)</span>
  }
  return <span className="badge bg-success-subtle text-success p-2">🟢 자치 검토 완료 (공개)</span>
}

function CountdownTimer({ createdAt }: { createdAt?: string }) {
  const [display, setDisplay] = useState('')

  useEffect(() => {
    if (!createdAt) return
    const update = () => {
      const deadline = new Date(createdAt).getTime() + 48 * 60 * 60 * 1000
      const diff = deadline - Date.now()
      if (diff <= 0) {
        setDisplay('심사 완료 (공개됨)')
        return
      }
      const h = Math.floor(diff / (1000 * 60 * 60))
      const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
      const s = Math.floor((diff % (1000 * 60)) / 1000)
      setDisplay(`보안 대기: ${h}시간 ${m}분 ${s}초 남음`)
    }
    update()
    const iv = setInterval(update, 1000)
    return () => clearInterval(iv)
  }, [createdAt])

  return <span className="countdown-timer small text-muted">{display}</span>
}

function isImageFile(fp: string) {
  const ext = fp.toLowerCase().split('.').pop() || ''
  return ['png', 'jpg', 'jpeg', 'gif'].includes(ext) || fp.includes('draw_')
}

function isPdfFile(fp: string) {
  return fp.toLowerCase().endsWith('.pdf')
}

export default function AllProposalsPage() {
  const { user } = useAuth()
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res = await api.get<Post[]>('/api/page/all-proposals')
      setPosts(Array.isArray(res) ? res : [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const handleVote = async (id: number, type: 'like' | 'dislike') => {
    try {
      const res = await api.post<{ status: string }>(`/post/${type}/${id}`)
      if (res.status === 'success') {
        setPosts(prev => prev.map(p =>
          p.id === id ? { ...p, [type === 'like' ? 'like_count' : 'dislike_count']: (p[type === 'like' ? 'like_count' : 'dislike_count'] || 0) + 1 } : p
        ))
      }
    } catch { /* ignore */ }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('정말 삭제하시겠습니까? 복구할 수 없습니다.')) return
    try {
      const res = await fetch(`/post/delete/${id}`, { method: 'POST' })
      if (res.ok) setPosts(prev => prev.filter(p => p.id !== id))
      else alert('삭제 실패')
    } catch { alert('오류 발생') }
  }

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  const userId = (user as any)?.id

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h3 className="fw-bold text-success">📜 누구의꿈</h3>
        <Link to="/main" className="btn btn-success fw-bold">새 제안 등록하기</Link>
      </div>

      {posts.length === 0 ? (
        <div className="text-center p-5 text-muted card border-0">현재 표시할 제안이 없습니다. 첫 제안을 남겨보세요!</div>
      ) : (
        <div className="list-group">
          {posts.map(p => {
            const createdAt = p.created_at ? new Date(p.created_at).getTime() : 0
            const now = Date.now()
            const within48 = createdAt && now - createdAt < 48 * 60 * 60 * 1000
            const noScore = (p.admin_score === 0 || p.admin_score == null) && (p.leader_score === 0 || p.leader_score == null)
            const canEdit = userId && p.user_id === userId && !p.is_forced_approved && noScore && within48

            return (
              <div key={p.id} className="list-group-item mb-3 p-4 shadow-sm border-0 bg-white" style={{ borderRadius: 18 }}>
                <div className="d-flex w-100 justify-content-between align-items-center mb-2">
                  <h5 className="fw-bold text-dark m-0">{p.title}</h5>
                  <small className="text-muted">
                    작성자: <Link to={`/user/${p.user_id}`} className="text-decoration-none text-muted">{p.author_name}</Link>
                  </small>
                </div>
                <p className="text-secondary mb-3">{(p.content || '').substring(0, 150)}...</p>

                {p.file_path && (
                  <div className="mb-3 p-2 bg-light rounded">
                    <div className="d-flex gap-2 flex-wrap align-items-center">
                      {isImageFile(p.file_path) ? (
                        <img src={p.file_path} className="rounded" style={{ maxHeight: 120, maxWidth: '100%' }} alt="첨부 이미지" />
                      ) : isPdfFile(p.file_path) ? (
                        <div className="d-flex align-items-center gap-2">
                          <span className="fs-1">📄</span>
                          <a href={p.file_path} target="_blank" rel="noopener noreferrer" className="text-decoration-none">PDF 파일</a>
                        </div>
                      ) : (
                        <div className="d-flex align-items-center gap-2">
                          <span className="fs-1">📎</span>
                          <a href={p.file_path} target="_blank" rel="noopener noreferrer" className="text-decoration-none">첨부파일</a>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {userId && p.user_id === userId && (
                  <div className="mb-3 p-2 bg-light rounded small">
                    <span className="fw-bold me-2">📊 점수:</span>
                    <span className="me-2">AI: <strong>{p.ai_score ?? 0}</strong></span>
                    <span className="me-2">관리자: <strong>{p.admin_score ?? 0}</strong></span>
                    <span className="me-2">책임자: <strong>{p.leader_score ?? 0}</strong></span>
                    <span className="me-2">회원: <strong>{p.member_score ?? 0}</strong></span>
                    <span>합계: <strong>{p.total_score ?? 0}</strong></span>
                  </div>
                )}
                <div className="d-flex justify-content-between align-items-center pt-3 border-top flex-wrap gap-2">
                  <div className="d-flex align-items-center gap-2 flex-wrap">
                    <button onClick={() => handleVote(p.id, 'like')} className="btn btn-sm btn-outline-success py-0 px-2">👍 {p.like_count || 0}</button>
                    <button onClick={() => handleVote(p.id, 'dislike')} className="btn btn-sm btn-outline-danger py-0 px-2">👎 {p.dislike_count || 0}</button>
                    <span className="mx-2">|</span>
                    {getStatusBadge(p)}
                    {p.created_at && within48 && <CountdownTimer createdAt={p.created_at} />}
                  </div>
                  <div className="d-flex align-items-center gap-2">
                    {canEdit && (
                      <>
                        <Link to={`/post/edit/${p.id}`} className="btn btn-sm btn-outline-primary fw-bold">✏️ 수정</Link>
                        <button onClick={() => handleDelete(p.id)} className="btn btn-sm btn-outline-danger">🗑️ 삭제</button>
                      </>
                    )}
                    <Link to={`/post/${p.id}`} className="btn btn-sm btn-link text-decoration-none">자세히 보기 &gt;</Link>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
