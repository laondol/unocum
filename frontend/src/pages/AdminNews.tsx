import { useState, useEffect } from 'react'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

interface NewsItem {
  id: number
  title: string
  summary: string
  category: string
  source_url: string
  ai_reason: string
  ai_generated: boolean
  ai_approved: boolean
  admin_approved: boolean
  is_selected: boolean
  created_at: string
}

const TABS = [
  { key: 'all', label: '전체' },
  { key: 'world', label: '🌍 세계와양평' },
  { key: 'kr_yp', label: '🇰🇷 대한민국과양평' },
]

type TabKey = 'all' | 'world' | 'kr_yp'

export default function AdminNews() {
  const [tab, setTab] = useState<TabKey>('all')
  const [news, setNews] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [importUrl, setImportUrl] = useState('')
  const [importing, setImporting] = useState(false)
  const [importMsg, setImportMsg] = useState('')
  const [importMsgOk, setImportMsgOk] = useState(false)
  const [suggesting, setSuggesting] = useState(false)
  const [cleaning, setCleaning] = useState(false)

  const fetchNews = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`/api/admin/news?tab=${tab}&page=${page}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setNews(data.items ?? [])
      setTotalPages(data.total_pages ?? 1)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setPage(1)
  }, [tab])

  useEffect(() => {
    fetchNews()
  }, [tab, page])

  const handleImportUrl = async () => {
    if (!importUrl.trim()) return
    setImporting(true)
    setImportMsg('')
    try {
      const formData = new FormData()
      formData.append('url', importUrl)
      formData.append('tab', tab)
      const res = await fetch('/admin/news/import-url', { method: 'POST', body: formData })
      const data = await res.json()
      if (data.status === 'success' || data.success) {
        setImportMsg('가져오기 성공!')
        setImportMsgOk(true)
        setImportUrl('')
        fetchNews()
      } else {
        setImportMsg(data.msg || data.message || '가져오기 실패')
        setImportMsgOk(false)
      }
    } catch {
      setImportMsg('오류가 발생했습니다.')
      setImportMsgOk(false)
    } finally {
      setImporting(false)
    }
  }

  const handleAiSuggest = async () => {
    setSuggesting(true)
    try {
      const res = await fetch('/admin/news/ai-suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `tab=${tab}`,
      })
      const data = await res.json()
      if (data.status === 'success' || data.success) {
        alert(data.msg || `✅ ${data.count}개의 실제 뉴스를 가져왔습니다.`)
        fetchNews()
      } else {
        alert(data.msg || data.message || '추천 실패')
      }
    } catch {
      alert('오류가 발생했습니다.')
    } finally {
      setSuggesting(false)
    }
  }

  const handleCleanCjk = async () => {
    if (!confirm('선택한 탭의 모든 뉴스에서 깨진 글자와 어색한 문장을 정리하시겠습니까?\nGroq API를 사용하므로 시간이 소요될 수 있습니다.')) return
    setCleaning(true)
    try {
      const res = await fetch('/admin/news/clean-cjk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `tab=${tab}`,
      })
      const data = await res.json()
      if (data.status === 'success' || data.success) {
        alert(data.msg || '정리 완료')
        fetchNews()
      } else {
        alert(data.msg || data.message || '정리 실패')
      }
    } catch {
      alert('오류가 발생했습니다.')
    } finally {
      setCleaning(false)
    }
  }

  const handleApprove = async (id: number, approver: 'ai' | 'admin') => {
    setNews(prev => prev.map(n => n.id === id ? { ...n, [approver === 'ai' ? 'ai_approved' : 'admin_approved']: !n[approver === 'ai' ? 'ai_approved' : 'admin_approved'] } : n))
    try {
      const res = await fetch(`/admin/news/approve/${id}/${tab}/${approver}`)
      const data = await res.json()
      if (!(data.status === 'success' || data.success)) {
        setNews(prev => prev.map(n => n.id === id ? { ...n, [approver === 'ai' ? 'ai_approved' : 'admin_approved']: !n[approver === 'ai' ? 'ai_approved' : 'admin_approved'] } : n))
        alert(data.msg || data.message || '승인 처리 실패')
      }
    } catch {
      setNews(prev => prev.map(n => n.id === id ? { ...n, [approver === 'ai' ? 'ai_approved' : 'admin_approved']: !n[approver === 'ai' ? 'ai_approved' : 'admin_approved'] } : n))
      alert('오류가 발생했습니다.')
    }
  }

  const handleToggle = async (id: number) => {
    try {
      const res = await fetch(`/admin/news/toggle/${id}`)
      const data = await res.json()
      if (data.status === 'success' || data.success) {
        fetchNews()
      } else {
        alert(data.msg || data.message || '토글 실패')
      }
    } catch {
      alert('오류가 발생했습니다.')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('삭제하시겠습니까?')) return
    try {
      const res = await fetch(`/admin/news/delete/${id}`, { method: 'POST' })
      const data = await res.json()
      if (data.status === 'success' || data.success) {
        setNews(prev => prev.filter(n => n.id !== id))
      } else {
        alert(data.msg || data.message || '삭제 실패')
      }
    } catch {
      alert('오류가 발생했습니다.')
    }
  }

  return (
    <div className="container mt-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h3 className="fw-bold mb-0">📰 AI 뉴스 큐레이션</h3>
        <a href="/admin/news/create" className="btn btn-success">✏️ 직접 작성</a>
      </div>

      {/* Tabs */}
      <ul className="nav nav-tabs mb-3">
        {TABS.map(t => (
          <li key={t.key} className="nav-item">
            <button
              className={`nav-link ${tab === t.key ? 'active fw-bold' : ''}`}
              onClick={() => setTab(t.key as TabKey)}
            >
              {t.label}
            </button>
          </li>
        ))}
      </ul>

      {/* URL Import + Action Buttons (hidden on 'all' tab) */}
      {tab !== 'all' && (
        <div className="card border-0 shadow-sm mb-4 p-3">
          <div className="input-group">
            <input
              type="url"
              className="form-control"
              placeholder="뉴스 URL을 붙여넣으세요..."
              value={importUrl}
              onChange={e => setImportUrl(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleImportUrl()}
            />
            <button
              className="btn btn-outline-primary"
              onClick={handleImportUrl}
              disabled={importing || !importUrl.trim()}
            >
              {importing ? '⏳ 가져오는 중...' : '🌐 가져오기 + AI 요약'}
            </button>
          </div>
          {importMsg && (
            <div className={`mt-2 small ${importMsgOk ? 'text-success' : 'text-danger'}`}>{importMsg}</div>
          )}
          <div className="mt-2">
            <button className="btn btn-outline-success btn-sm" onClick={handleAiSuggest} disabled={suggesting}>
              {suggesting ? '⏳ 생성 중...' : '🤖 AI 뉴스 추천'}
            </button>
            <button className="btn btn-outline-warning btn-sm ms-1" onClick={handleCleanCjk} disabled={cleaning}>
              {cleaning ? '⏳ 정리 중...' : '🗣️ 깨진 글자 정리'}
            </button>
            <small className="text-muted ms-2">
              {tab === 'world' ? '🌐 영문 검색 → 해외 기사 중심' : '🇰🇷 국내 검색 → 한국 뉴스 중심'} (자동 가져오기)
            </small>
          </div>
        </div>
      )}

      {/* News Table */}
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorMessage message={error} onRetry={fetchNews} />
      ) : news.length === 0 ? (
        <div className="card border-0 shadow-sm">
          <div className="text-center py-5 text-muted">
            등록된 뉴스가 없습니다. AI 추천 또는 직접 작성해 주세요.
          </div>
        </div>
      ) : (
        <div className="card border-0 shadow-sm">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr className="text-center small">
                  <th style={{ width: '5%' }}>ID</th>
                  <th style={{ width: '22%' }}>제목</th>
                  <th style={{ width: '7%' }}>분류</th>
                  <th style={{ width: '12%' }}>AI 선정 이유</th>
                  <th style={{ width: '8%' }}>원본링크</th>
                  <th style={{ width: '4%' }}>AI</th>
                  <th style={{ width: '8%' }}>채자(AI)</th>
                  <th style={{ width: '8%' }}>채자(관리)</th>
                  <th style={{ width: '8%' }}>등록일</th>
                  <th style={{ width: '10%' }}>관리</th>
                </tr>
              </thead>
              <tbody>
                {news.map(item => (
                  <tr key={item.id} className="text-center">
                    <td className="text-muted">{item.id}</td>
                    <td className="text-start ps-3">
                      <div className="fw-bold text-dark">
                        {item.title.length > 60 ? item.title.slice(0, 60) + '...' : item.title}
                      </div>
                      <small className="text-muted">
                        {item.summary && item.summary.length > 80
                          ? item.summary.slice(0, 80) + '...'
                          : item.summary}
                      </small>
                    </td>
                    <td><span className="badge bg-secondary">{item.category}</span></td>
                    <td className="text-start small" style={{ maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={item.ai_reason || ''}>
                      {item.ai_reason ? (
                        <span className="text-success" title={item.ai_reason}>
                          💡 {item.ai_reason.length > 50 ? item.ai_reason.slice(0, 50) + '...' : item.ai_reason}
                        </span>
                      ) : (
                        <span className="text-muted">-</span>
                      )}
                    </td>
                    <td>
                      {item.source_url ? (
                        <div className="d-flex gap-1 justify-content-center">
                          <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-outline-primary">🔗 원문</a>
                          <a href={`https://translate.google.com/translate?sl=auto&tl=ko&u=${encodeURIComponent(item.source_url)}`} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-outline-info">🌐 번역</a>
                        </div>
                      ) : (
                        <span className="text-muted small">-</span>
                      )}
                    </td>
                    <td>{item.ai_generated ? '🤖' : '✏️'}</td>
                    <td>
                      <button
                        className={`btn btn-sm ${item.ai_approved ? 'btn-success' : 'btn-outline-secondary'}`}
                        style={{ minWidth: 44 }}
                        onClick={() => handleApprove(item.id, 'ai')}
                      >
                        {item.ai_approved ? '✅' : '⭕'}
                      </button>
                    </td>
                    <td>
                      <button
                        className={`btn btn-sm ${item.admin_approved ? 'btn-primary' : 'btn-outline-secondary'}`}
                        style={{ minWidth: 44 }}
                        onClick={() => handleApprove(item.id, 'admin')}
                      >
                        {item.admin_approved ? '✅' : '⭕'}
                      </button>
                    </td>
                    <td className="small text-muted">
                      {item.created_at ? new Date(item.created_at).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-'}
                    </td>
                    <td>
                      <button className={`btn btn-sm ${item.is_selected ? 'btn-outline-success' : 'btn-outline-secondary'} me-1`} onClick={() => handleToggle(item.id)} title={item.is_selected ? '표시중' : '비활성'}>
                        {item.is_selected ? '👁️' : '🚫'}
                      </button>
                      <a href={`/admin/news/edit/${item.id}`} className="btn btn-sm btn-outline-success me-1">편집</a>
                      <button className="btn btn-sm btn-outline-danger" onClick={() => handleDelete(item.id)}>삭제</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <nav className="mt-3">
          <ul className="pagination justify-content-center">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
              <li key={p} className={`page-item ${p === page ? 'active' : ''}`}>
                <button className="page-link" onClick={() => setPage(p)}>{p}</button>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </div>
  )
}
