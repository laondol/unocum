import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import type { NewsArticle } from '../lib/types'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

interface IntroData {
  yp_news?: NewsArticle[]
  world_news?: NewsArticle[]
  bg_images?: string[]
}

export default function IntroPage() {
  const [data, setData] = useState<IntroData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [bgIndex, setBgIndex] = useState(0)

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res = await api.get<IntroData>('/api/page/intro')
      setData(res)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const bgImages = data?.bg_images || []

  useEffect(() => {
    if (bgImages.length < 2) return
    const iv = setInterval(() => {
      setBgIndex(prev => (prev + 1) % bgImages.length)
    }, 5000)
    return () => clearInterval(iv)
  }, [bgImages.length])

  if (loading) return <Loading />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  const ypNews = (data?.yp_news || []).slice(0, 5)
  const worldNews = (data?.world_news || []).slice(0, 5)

  return (
    <div>
      <div className="position-relative overflow-hidden text-center" style={{ borderRadius: 25, minHeight: 320 }}>
        {bgImages.length > 0 && (
          <div
            className="position-absolute top-0 start-0 w-100 h-100"
            style={{
              backgroundImage: `url(${bgImages[bgIndex]})`,
              backgroundSize: 'cover',
              backgroundPosition: 'center',
              transition: 'background-image 1s ease-in-out',
              opacity: 0.25,
              filter: 'blur(2px)',
              zIndex: 0,
            }}
          />
        )}
        <div className="position-relative d-flex flex-column align-items-center justify-content-center" style={{ zIndex: 1, minHeight: 320 }}>
          <span className="badge bg-success-subtle text-success px-3 py-2 rounded-pill fw-bold mb-3">
            YANGPYEONG COMMUNITY PLATFORM
          </span>
          <h1 className="fw-bold mb-4" style={{ letterSpacing: -1 }}>
            함께 만들어가는 양평, 함께 사는 양평
          </h1>
          <div className="d-flex justify-content-center gap-3 flex-wrap">
            <Link to="/main" className="btn btn-success btn-lg px-4 py-2 fw-bold shadow">꿈꾸기</Link>
            <Link to="/presentation" className="btn btn-outline-dark btn-lg px-4 py-2">비전</Link>
            <Link to="/share/report" className="btn btn-warning btn-lg px-4 py-2 fw-bold shadow">공유하기</Link>
          </div>
        </div>
      </div>

      <div className="row g-3 my-4">
        <div className="col-md-4">
          <div className="card p-4 border-0 shadow-sm h-100" style={{ borderTop: '5px solid #27ae60' }}>
            <h5 className="fw-bold mb-2">♿ 휠체어 경사로</h5>
            <p className="text-muted small flex-grow-1">골목상권 상가와 보행로의 턱을 없애 이동을 편안하게 돕습니다.</p>
            <Link to="/service/ramp" className="btn btn-outline-success btn-sm mt-auto align-self-start">사업 알아보기</Link>
          </div>
        </div>
        <div className="col-md-4">
          <div className="card p-4 border-0 shadow-sm h-100" style={{ borderTop: '5px solid #2980b9' }}>
            <h5 className="fw-bold mb-2">⚖️ 법률상담</h5>
            <p className="text-muted small flex-grow-1">임금 체불, 부당 해고 등 억울한 노동 고민을 무료로 상담해 드립니다.</p>
            <Link to="/service/legal" className="btn btn-outline-primary btn-sm mt-auto align-self-start">상담소 가기</Link>
          </div>
        </div>
        <div className="col-md-4">
          <div className="card p-4 border-0 shadow-sm h-100" style={{ borderTop: '5px solid #8e44ad' }}>
            <h5 className="fw-bold mb-2">🫂 심리상담</h5>
            <p className="text-muted small flex-grow-1">장애인 당사자와 가족의 아픔과 지친 마음을 전문적으로 안아드립니다.</p>
            <Link to="/service/psycho" className="btn btn-outline-secondary btn-sm mt-auto align-self-start">상담 예약하기</Link>
          </div>
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-md-6">
          <div className="card border-0 shadow-sm p-3 h-100" style={{ borderRadius: 15, background: 'linear-gradient(135deg,#e3f2fd,#fff)' }}>
            <h6 className="fw-bold text-primary text-center mb-2">대한민국과 양평</h6>
            {ypNews.length > 0 ? ypNews.map(n => (
              <Link key={n.id} to={`/news/${n.id}`} className="text-decoration-none d-block text-truncate mb-1">
                <small className="text-dark">{n.title}</small>
              </Link>
            )) : (
              <p className="small text-muted text-center mb-0">등록된 소식이 없습니다</p>
            )}
          </div>
        </div>
        <div className="col-md-6">
          <div className="card border-0 shadow-sm p-3 h-100" style={{ borderRadius: 15, background: 'linear-gradient(135deg,#e8f5e9,#fff)' }}>
            <h6 className="fw-bold text-success text-center mb-2">세계와 양평</h6>
            {worldNews.length > 0 ? worldNews.map(n => (
              <Link key={n.id} to={`/news/${n.id}`} className="text-decoration-none d-block text-truncate mb-1">
                <small className="text-dark">{n.title}</small>
              </Link>
            )) : (
              <p className="small text-muted text-center mb-0">등록된 소식이 없습니다</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
