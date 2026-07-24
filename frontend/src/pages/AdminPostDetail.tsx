import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import Loading from '../components/common/Loading'

interface DebateLog {
  time: string
  admin: string
  ai: string
}

interface PostDetail {
  id: number; title: string; content: string; file_path?: string
  author_name?: string; category?: string; status?: string
  ai_score: number; admin_score: number; leader_score: number; member_score: number
  total_score: number; ai_summary?: string; ai_reason?: string
  is_forced_approved: boolean; is_finalized: boolean
  created_at?: string; debate_logs: DebateLog[]
}

export default function AdminPostDetail() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const role = (user as any)?.role
  const [post, setPost] = useState<PostDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [adminScore, setAdminScore] = useState(0)
  const [leaderScore, setLeaderScore] = useState(0)
  const [forceApprove, setForceApprove] = useState(false)
  const [saving, setSaving] = useState(false)

  const [opinion, setOpinion] = useState('')
  const [suggestedScore, setSuggestedScore] = useState(0)
  const [debating, setDebating] = useState(false)

  const fetchPost = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res = await fetch(`/api/admin/post/${id}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: PostDetail = await res.json()
      setPost(data)
      setAdminScore(data.admin_score)
      setLeaderScore(data.leader_score)
      setSuggestedScore(data.ai_score)
      setForceApprove(data.is_forced_approved)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [id])

  useEffect(() => { fetchPost() }, [fetchPost])

  const handleSaveScores = async () => {
    setSaving(true)
    try {
      const body: Record<string, unknown> = {}
      if (role === 'admin') body.admin_score = adminScore
      if (role === 'leader') body.leader_score = leaderScore
      body.is_forced_approved = forceApprove
      const res = await fetch(`/api/admin/post/${id}/scores`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error('저장 실패')
      const data = await res.json()
      setPost(prev => prev ? { ...prev, total_score: data.total_score, is_forced_approved: data.is_forced_approved } : prev)
      alert('저장되었습니다.')
    } catch { alert('저장 실패') }
    finally { setSaving(false) }
  }

  const handleDebate = async () => {
    if (!opinion.trim()) return
    setDebating(true)
    try {
      const fd = new FormData()
      fd.append('admin_opinion', opinion)
      fd.append('suggested_score', String(suggestedScore))
      const res = await fetch(`/admin/debate/${id}`, { method: 'POST', body: fd })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.msg || '오류 발생')
      }
      await fetchPost()
      setOpinion('')
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : '오류 발생')
    } finally { setDebating(false) }
  }

  if (loading) return <Loading />
  if (error) return <div className="text-center py-5 text-danger">{error}</div>
  if (!post) return null

  return (
    <div className="px-0 px-md-2">
      <Link to="/admin" className="btn btn-sm btn-outline-secondary mb-3">← 목록</Link>
      <div className="row g-4">
        <div className="col-lg-7">
          <div className="card border-0 shadow-sm p-4 mb-4" style={{ borderRadius: 16 }}>
            <h3 className="fw-bold">{post.title}</h3>
            <p className="text-muted small mb-0">
              {post.author_name && `작성자: ${post.author_name}`}
              {post.created_at && ` · ${new Date(post.created_at).toLocaleDateString('ko-KR')}`}
            </p>
          </div>

          <div className="card border-0 shadow-sm p-4 bg-light" style={{ borderRadius: 16 }}>
            <h5 className="fw-bold mb-4">🗨️ AI 지킴이와 숙의중</h5>
            <div style={{ height: 400, overflowY: 'auto', background: 'white', padding: 20, borderRadius: 15 }}>
              {post.debate_logs.length === 0 ? (
                <div className="text-center text-muted py-5">
                  <div className="fs-1 mb-3">💬</div>
                  <p>아직 AI와의 숙의 기록이 없습니다.<br />우측 패널에서 AI에게 의견을 전달해보세요.</p>
                </div>
              ) : (
                post.debate_logs.map((log, i) => (
                  <div key={i} className="mb-3">
                    <small className="text-muted d-block text-center mb-1">{log.time}</small>
                    <div className="text-end mb-2">
                      <div className="d-inline-block bg-primary text-white rounded-3 p-3 shadow-sm text-start" style={{ maxWidth: '80%', borderRadius: '18px 18px 4px 18px' }}>
                        <small className="fw-bold d-block mb-1">👮 운영진 의견</small>
                        {log.admin}
                      </div>
                    </div>
                    <div className="text-start">
                      <div className="d-inline-block bg-light border rounded-3 p-3 text-start" style={{ maxWidth: '80%', borderRadius: '18px 18px 18px 4px' }}>
                        <small className="fw-bold d-block mb-1 text-success">🤖 AI 지킴이 응답</small>
                        {log.ai}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {post.content && (
            <div className="card border-0 shadow-sm p-4 mt-4" style={{ borderRadius: 16 }}>
              <h6 className="fw-bold mb-3">📄 본문</h6>
              <div dangerouslySetInnerHTML={{ __html: post.content }} />
            </div>
          )}
        </div>

        <div className="col-lg-5">
          <div className="card border-0 shadow-sm p-4" style={{ borderRadius: 16, position: 'sticky', top: 20 }}>
            <h4 className="fw-bold mb-4">⚖️ 판정 컨트롤 패널</h4>

            {post.is_finalized && (
              <div className="alert alert-success">✅ 점수가 확정되었습니다. 변경할 수 없습니다.</div>
            )}
            {post.admin_score !== 0 && post.leader_score !== 0 && post.is_forced_approved && (
              <div className="alert alert-info">✅ 관리자·책임자 점수 확정 → 자동 공개되었습니다.</div>
            )}

            <div className="mb-4">
              <div className="row g-2 mb-3">
                {role === 'admin' && (
                  <>
                    <div className="col-6">
                      <label className="small">👮 관리자 점수(-10~10)</label>
                      <input type="number" className="form-control" value={adminScore} onChange={e => setAdminScore(Number(e.target.value))} disabled={post.is_finalized} />
                    </div>
                    <div className="col-6">
                      <label className="small">👑 책임자 점수</label>
                      <input type="number" className="form-control" value={post.leader_score} disabled />
                    </div>
                  </>
                )}
                {role === 'leader' && (
                  <>
                    <div className="col-6">
                      <label className="small">👮 관리자 점수</label>
                      <input type="number" className="form-control" value={post.admin_score} disabled />
                    </div>
                    <div className="col-6">
                      <label className="small">👑 책임자 점수(-10~10)</label>
                      <input type="number" className="form-control" value={leaderScore} onChange={e => setLeaderScore(Number(e.target.value))} disabled={post.is_finalized} />
                    </div>
                  </>
                )}
              </div>
              {!post.is_finalized && (
                <div className="form-check mb-3">
                  <input className="form-check-input" type="checkbox" id="forceApprove" checked={forceApprove} onChange={e => setForceApprove(e.target.checked)} />
                  <label className="form-check-label" htmlFor="forceApprove">강제 승인</label>
                </div>
              )}
              {!post.is_finalized && (
                <button className="btn btn-dark w-100" onClick={handleSaveScores} disabled={saving}>
                  {saving ? '저장 중...' : '운영진 점수 확정'}
                </button>
              )}
            </div>

            <div className="mb-3 p-3 bg-light rounded-4">
              <h6>📊 종합 점수</h6>
              <div className="row small">
                <div className="col-4">AI: {post.ai_score}</div>
                <div className="col-4">관리자: {post.admin_score}</div>
                <div className="col-4">책임자: {post.leader_score}</div>
                <div className="col-6 mt-1">회원: {post.member_score}</div>
                <div className="col-6 mt-1 fw-bold">합계: {post.total_score}</div>
              </div>
            </div>

            {post.ai_reason && (
              <div className="mb-3 p-3 bg-light rounded-4">
                <h6>🤖 AI 심사 사유</h6>
                <p className="small mb-0">{post.ai_reason}</p>
              </div>
            )}

            <div className="p-3 rounded-4 bg-warning bg-opacity-10 border border-warning">
              <h6 className="fw-bold">🤖 AI 점수 조정 토론</h6>
              <div className="mb-2 small text-muted">
                현재 AI 점수: <strong>{post.ai_score}</strong>점
                {post.debate_logs.length > 0 && (
                  <> · 마지막 AI 제안: <strong>{post.ai_score}</strong>점</>
                )}
              </div>
              <input type="number" className="form-control mb-2" placeholder="제안할 AI 점수 (-50~50)" value={suggestedScore} onChange={e => setSuggestedScore(Number(e.target.value))} />
              <textarea className="form-control mb-2" rows={4} placeholder="AI를 설득할 논리적 근거를 입력하세요..." value={opinion} onChange={e => setOpinion(e.target.value)} />
              <button className="btn btn-warning w-100 fw-bold" onClick={handleDebate} disabled={debating || !opinion.trim()}>
                {debating ? <><span className="spinner-border spinner-border-sm me-1" /> AI가 분석 중...</> : 'AI에게 의견 전달'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
