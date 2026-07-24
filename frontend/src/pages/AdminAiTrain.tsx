import { useEffect, useState } from 'react'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

interface AiKnowledge {
  id: number
  question: string
  answer: string
  category: string
  created_at: string
}

export default function AdminAiTrain() {
  const [items, setItems] = useState<AiKnowledge[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchData = () => {
    setLoading(true)
    setError('')
    fetch('/api/admin/ai-knowledge')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(data => setItems(Array.isArray(data) ? data : []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchData() }, [])

  return (
    <div className="px-0 px-md-2">
      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold mb-4">AI 지식 관리</h5>
          {loading ? (
            <Loading />
          ) : error ? (
            <ErrorMessage message={error} onRetry={fetchData} />
          ) : items.length === 0 ? (
            <div className="text-center py-5 text-muted">
              <p>등록된 AI 지식이 없습니다.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light">
                  <tr>
                    <th>ID</th>
                    <th>질문</th>
                    <th>답변</th>
                    <th>카테고리</th>
                    <th>등록일</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map(item => (
                    <tr key={item.id}>
                      <td className="text-muted small">{item.id}</td>
                      <td>{item.question}</td>
                      <td className="small text-muted">{item.answer.substring(0, 100)}</td>
                      <td>{item.category}</td>
                      <td className="small text-muted">{item.created_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
