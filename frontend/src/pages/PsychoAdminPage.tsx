import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'
import EmptyState from '../components/common/EmptyState'

interface PsychoPost {
  id: number
  title: string
  content: string
  author_name: string
  email: string
  answer: string | null
  fee: number | null
  travel_allowance: number | null
  answered_at: string | null
  status: string
  created_at: string
}

export default function PsychoAdminPage() {
  const { user, loading: authLoading } = useAuth()
  const [posts, setPosts] = useState<PsychoPost[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tab, setTab] = useState<'pending' | 'answered'>('pending')
  const [answering, setAnswering] = useState<number | null>(null)
  const [answerText, setAnswerText] = useState('')
  const [fee, setFee] = useState('')
  const [travelAllowance, setTravelAllowance] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/psycho/posts')
      if (!res.ok) throw new Error('불러오기 실패')
      const data = await res.json()
      setPosts(Array.isArray(data) ? data : data.posts || [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { if (!authLoading) load() }, [authLoading])

  const pending = posts.filter(p => !p.answer && p.status !== 'flagged')
  const answered = posts.filter(p => p.answer)

  const handleAnswer = async (postId: number) => {
    if (!answerText.trim()) return alert('답변 내용을 입력하세요.')
    setSubmitting(true)
    try {
      const fd = new FormData()
      fd.append('answer', answerText.trim())
      if (fee) fd.append('fee', fee)
      if (travelAllowance) fd.append('travel_allowance', travelAllowance)
      const res = await fetch(`/psycho/admin/answer/${postId}`, { method: 'POST', body: fd }).then(r => r.json())
      if (res.status === 'success' || res.success) {
        setAnswerText(''); setFee(''); setTravelAllowance(''); setAnswering(null)
        load()
      } else {
        alert(res.error || '답변 등록 실패')
      }
    } catch {
      alert('답변 등록 실패')
    } finally {
      setSubmitting(false)
    }
  }

  if (authLoading || loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />
  if (!user || (user.role !== 'admin' && user.role !== 'leader')) {
    return <ErrorMessage message="접근 권한이 없습니다." />
  }

  return (
    <div className="container mt-4" style={{ maxWidth: 800 }}>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h4 className="fw-bold mb-0">🧑‍⚕️ 심리상담 관리</h4>
        <a href="/psycho/admin/appointments" className="btn btn-outline-primary btn-sm">상담 예약 관리</a>
      </div>

      <ul className="nav nav-tabs mb-4">
        <li className="nav-item">
          <button className={`nav-link ${tab === 'pending' ? 'active fw-bold' : ''}`} onClick={() => setTab('pending')}>
            미답변 질문 {pending.length > 0 && <span className="badge bg-danger ms-1">{pending.length}</span>}
          </button>
        </li>
        <li className="nav-item">
          <button className={`nav-link ${tab === 'answered' ? 'active fw-bold' : ''}`} onClick={() => setTab('answered')}>
            답변 완료
          </button>
        </li>
      </ul>

      {tab === 'pending' && (
        <>
          {pending.length === 0 ? (
            <EmptyState icon="✅" title="모든 질문에 답변되었습니다" />
          ) : (
            <div className="row g-3">
              {pending.map(p => (
                <div key={p.id} className="col-12">
                  <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
                    <div className="card-body p-4">
                      <div className="d-flex justify-content-between align-items-start mb-2">
                        <div>
                          <h6 className="fw-bold mb-1">{p.title}</h6>
                          <div className="small text-muted">
                            {p.author_name} | {new Date(p.created_at).toLocaleString('ko-KR')}
                          </div>
                        </div>
                      </div>
                      <p className="small text-muted mb-3" style={{ whiteSpace: 'pre-wrap' }}>{p.content.substring(0, 200)}</p>
                      {answering === p.id ? (
                        <div>
                          <div className="mb-2">
                            <label className="small text-muted d-block">답변 내용</label>
                            <textarea
                              className="form-control"
                              rows={4}
                              value={answerText}
                              onChange={e => setAnswerText(e.target.value)}
                              placeholder="답변을 입력하세요"
                            />
                          </div>
                          <div className="row g-2 mb-3">
                            <div className="col-6">
                              <label className="small text-muted d-block">상담비</label>
                              <input type="number" className="form-control" value={fee} onChange={e => setFee(e.target.value)} placeholder="금액" />
                            </div>
                            <div className="col-6">
                              <label className="small text-muted d-block">교통비</label>
                              <input type="number" className="form-control" value={travelAllowance} onChange={e => setTravelAllowance(e.target.value)} placeholder="금액" />
                            </div>
                          </div>
                          <div className="d-flex gap-2">
                            <button className="btn btn-sm btn-success" onClick={() => handleAnswer(p.id)} disabled={submitting}>
                              {submitting ? '등록 중...' : '답변 등록'}
                            </button>
                            <button className="btn btn-sm btn-outline-secondary" onClick={() => { setAnswering(null); setAnswerText(''); setFee(''); setTravelAllowance('') }}>
                              취소
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button className="btn btn-sm btn-outline-success" onClick={() => setAnswering(p.id)}>
                          답변 작성
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {tab === 'answered' && (
        <>
          {answered.length === 0 ? (
            <EmptyState icon="📭" title="답변 완료된 질문이 없습니다" />
          ) : (
            <div className="row g-3">
              {answered.map(p => (
                <div key={p.id} className="col-12">
                  <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
                    <div className="card-body p-4">
                      <div className="d-flex justify-content-between align-items-start mb-2">
                        <div>
                          <h6 className="fw-bold mb-1">
                            {p.title}
                            <span className="badge bg-success ms-2">답변완료</span>
                          </h6>
                          <div className="small text-muted">📧 {p.email || p.author_name}</div>
                        </div>
                      </div>
                      <div className="d-flex gap-2 mb-2 flex-wrap">
                        {p.fee && <span className="badge bg-light text-dark border">상담비: {p.fee.toLocaleString()}원</span>}
                        {p.travel_allowance && <span className="badge bg-light text-dark border">교통비: {p.travel_allowance.toLocaleString()}원</span>}
                      </div>
                      <div className="small text-muted">
                        답변일: {p.answered_at ? new Date(p.answered_at).toLocaleString('ko-KR') : '-'}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
