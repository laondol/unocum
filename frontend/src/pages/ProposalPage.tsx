import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import type { NewsArticle } from '../lib/types'
import { useAuth } from '../contexts/AuthContext'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

interface CharterData {
  content?: string
}

export default function ProposalPage() {
  const { user } = useAuth()
  const [news, setNews] = useState<NewsArticle[]>([])
  const [charter, setCharter] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [charterOpen, setCharterOpen] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [introData, charterData] = await Promise.all([
        api.get<{ selected_news?: NewsArticle[] }>('/api/page/intro'),
        api.get<CharterData>('/api/page/charter').catch(() => ({ content: '' })),
      ])
      setNews(introData.selected_news || [])
      setCharter(charterData.content || '')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const handleVote = async (id: number, type: 'like' | 'dislike') => {
    try {
      const res = await api.post<{ status: string }>(`/news/${type}/${id}`)
      if (res.status === 'success') {
        setNews(prev => prev.map(n =>
          n.id === id ? { ...n, [type === 'like' ? 'like_count' : 'dislike_count']: (n[type === 'like' ? 'like_count' : 'dislike_count'] || 0) + 1 } : n
        ))
      }
    } catch { /* ignore */ }
  }

  const rights: { name: string; icon: string }[] = [
    { name: '환경', icon: '🍃' }, { name: '건강', icon: '🏥' }, { name: '돌봄', icon: '🫂' },
    { name: '교육', icon: '📚' }, { name: '주거', icon: '🏠' }, { name: '노동', icon: '⚒️' },
    { name: '디지털', icon: '📱' }, { name: '문화', icon: '🎨' },
  ]

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div>
      <div className="text-center py-5 mb-5" style={{ background: 'linear-gradient(135deg, #e8f5e9 0%, #ffffff 100%)', borderRadius: 35, padding: '100px 20px !important' }}>
        <span className="badge bg-success-subtle text-success px-3 py-2 rounded-pill fw-bold mb-3">YANGPYEONG COMMUNITY PLATFORM</span>
        <h1 className="display-3 fw-bold mb-3" style={{ letterSpacing: -2 }}>이웃이 제안하고,<br />공동체가 실현하는 <span className="text-success">양평 자치</span></h1>
        <p className="lead text-secondary mb-4 mx-auto" style={{ maxWidth: 650, lineHeight: 1.6 }}>
          우리는 관(官)의 도움 없이 주민들이 직접 제안하고 상벌점 닢을 쌓으며, 동네의 작은 문턱부터 거대한 프로젝트까지 스스로 해결하는 청정 민간 공간입니다.
        </p>
        <div className="d-flex justify-content-center gap-3 flex-wrap">
          <Link to="/main" className="btn btn-success btn-lg px-5 py-3 fw-bold shadow">주민 광장 입장</Link>
          <Link to="/presentation" className="btn btn-outline-dark btn-lg px-5 py-3">비전 프레젠테이션(IR)</Link>
          {user ? (
            <Link to="/share/report" className="btn btn-warning btn-lg px-5 py-3 fw-bold shadow">📸 공유하기</Link>
          ) : (
            <Link to="/login?next=/share/report" className="btn btn-warning btn-lg px-5 py-3 fw-bold shadow">📸 공유하기</Link>
          )}
        </div>
      </div>

      <div className="card border-0 shadow-sm mb-5 p-4" style={{ borderRadius: 25, background: 'linear-gradient(135deg, #f0fff4 0%, #ffffff 100%)', borderLeft: '6px solid #27ae60' }}>
        <div className="card-body p-3">
          <h5 className="fw-bold text-success mb-1">🌱 사업 소개 (요약)</h5>
          <p className="fw-semibold text-dark mb-3" style={{ fontSize: '1.15rem' }}>
            "양평에서 함께 잘 살기 위해 꿈꾸고, 현실화하는 민간주도 행복추구 커뮤니티"
          </p>
          <p className="text-secondary mb-2" style={{ lineHeight: 1.7 }}>
            '함께사는 양평'은 관의 개입 없이 주민이 직접 예산과 아이디어를 제안하고, 인력을 모아 실행하는 주민 자치 플랫폼입니다. AI를 활용한 투명한 제안 심사, 유료 멤버십 기반의 닢 경제 모델을 통해 지속 가능한 지역 공동체를 지향합니다. 우리는 최소한의 유지를 위한 이익을 추구하며, 주민들의 꿈이 실현되는 양평을 함께 만들어갑니다.
          </p>
        </div>
      </div>

      <div className="row g-4 mb-5">
        <div className="col-12"><h4 className="fw-bold mb-3">📍 현재 함께하고 있는 상시 사업</h4></div>
        <div className="col-md-4">
          <div className="card p-4 border-0 shadow-sm h-100" style={{ borderTop: '5px solid #27ae60' }}>
            <h5 className="fw-bold mb-2">♿ 휠체어 경사로 보급</h5>
            <p className="text-muted small">골목상권 상가와 보행로의 턱을 없애 이동을 편안하게 돕습니다.</p>
            <Link to="/service/ramp" className="btn btn-sm btn-outline-success mt-auto align-self-start">사업 알아보기</Link>
          </div>
        </div>
        <div className="col-md-4">
          <div className="card p-4 border-0 shadow-sm h-100" style={{ borderTop: '5px solid #2980b9' }}>
            <h5 className="fw-bold mb-2">⚖️ 이훈 노무사의 노동법률실</h5>
            <p className="text-muted small">임금 체불, 부당 해고 등 억울한 노동 고민을 무료로 상담해 드립니다.</p>
            <Link to="/service/legal" className="btn btn-sm btn-outline-primary mt-auto align-self-start">상담실 가기</Link>
          </div>
        </div>
        <div className="col-md-4">
          <div className="card p-4 border-0 shadow-sm h-100" style={{ borderTop: '5px solid #8e44ad' }}>
            <h5 className="fw-bold mb-2">🫂 장애인 전문 심리상담소</h5>
            <p className="text-muted small">장애인 당사자와 가족의 아픔과 지친 마음을 전문적으로 안아드립니다.</p>
            <Link to="/service/psycho" className="btn btn-sm btn-outline-secondary mt-auto align-self-start">상담 예약하기</Link>
          </div>
        </div>
      </div>

      {news.length > 0 && (
        <div className="row g-4 mb-5">
          <div className="col-12 d-flex justify-content-between align-items-center">
            <h4 className="fw-bold mb-0">🌍 세계와 양평</h4>
            <small className="text-muted">AI 큐레이션 · 매일 업데이트</small>
          </div>
          {news.map(item => (
            <div key={item.id} className="col-md-6 col-lg-4">
              <div className="card border-0 shadow-sm h-100" style={{ borderRadius: 18, overflow: 'hidden' }}>
                {item.image_path && (
                  <img src={item.image_path} className="card-img-top" style={{ height: 180, objectFit: 'cover' }} alt={item.title} />
                )}
                <div className="card-body d-flex flex-column">
                  <span className="badge bg-success-subtle text-success align-self-start mb-2">{item.category}</span>
                  <h6 className="fw-bold card-title mb-2">
                    <Link to={`/news/${item.id}`} className="text-dark text-decoration-none">{item.title}</Link>
                  </h6>
                  <p className="small text-muted flex-grow-1">
                    {(item.summary || '').substring(0, 150)}{(item.summary || '').length > 150 ? '...' : ''}
                  </p>
                  <div className="d-flex justify-content-between align-items-center mt-auto pt-2 border-top">
                    <small className="text-muted">{item.source_name || 'AI 추천'}</small>
                    {user ? (
                      <div className="d-flex gap-1">
                        <button onClick={() => handleVote(item.id, 'like')} className="btn btn-sm btn-outline-success p-1 px-2">👍 {item.like_count || 0}</button>
                        <button onClick={() => handleVote(item.id, 'dislike')} className="btn btn-sm btn-outline-danger p-1 px-2">👎 {item.dislike_count || 0}</button>
                      </div>
                    ) : (
                      <small className="text-muted">👍 {item.like_count || 0} 👎 {item.dislike_count || 0}</small>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="row g-3 text-center py-5">
        <div className="col-12 mb-4">
          <h4 className="fw-bold m-0">우리가 주민 스스로 지키는 8대 자치권</h4>
          <p className="text-muted small mt-2">함께사는양평의 제안들은 이 여덟 가지의 가치를 기반으로 움직입니다.</p>
        </div>
        {rights.map(r => (
          <div key={r.name} className="col-6 col-md-3">
            <div className="card p-4 border-0 shadow-sm h-100">
              <div className="fs-1 mb-2">{r.icon}</div>
              <div className="fw-bold text-dark" style={{ fontSize: '1.1rem' }}>{r.name}권</div>
            </div>
          </div>
        ))}
      </div>

      <div className="card border-0 shadow-sm mb-5" style={{ borderRadius: 18 }}>
        <div className="card-body p-4">
          <div className="text-center mb-4">
            <span className="badge bg-success px-3 py-2 rounded-pill fw-bold mb-2">SOCIAL COOPERATIVE</span>
            <h4 className="fw-bold">함께사는양평 사회적협동조합 정관</h4>
            <p className="text-muted small">시행일: 2026년 7월 1일 | 제안: 운영위원회</p>
          </div>
          {charter ? (
            <div onClick={() => setCharterOpen(!charterOpen)} style={{ cursor: 'pointer' }}>
              <div className="text-center">
                <span className="badge bg-secondary">{charterOpen ? '접기' : '정관 보기'}</span>
              </div>
              {charterOpen && (
                <div className="mt-3" dangerouslySetInnerHTML={{ __html: charter }} />
              )}
            </div>
          ) : (
            <p className="text-muted small text-center">정관 정보를 불러올 수 없습니다.</p>
          )}
        </div>
      </div>

      <div className="text-center mt-5 pt-4 border-top">
        <Link to="/terms" className="text-muted text-decoration-none small">📋 회원약관 및 닢 운영 규칙</Link>
      </div>
    </div>
  )
}
