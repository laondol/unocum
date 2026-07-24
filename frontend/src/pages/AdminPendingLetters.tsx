import { useState, useEffect } from 'react'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

interface PendingLetter {
  id: number
  subject: string
  content: string
  sender_name: string
  sender_id: number
  receiver_id: number
  created_at: string
}

export default function AdminPendingLetters() {
  const [letters, setLetters] = useState<PendingLetter[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/admin/pending-letters')
      if (!res.ok) throw new Error('불러오기 실패')
      const data = await res.json()
      setLetters(Array.isArray(data) ? data : [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  if (loading) return (
    <div className="px-0 px-md-2">
      <Loading />
    </div>
  )

  if (error) return (
    <div className="px-0 px-md-2">
      <ErrorMessage message={error} onRetry={load} />
    </div>
  )

  return (
    <div className="px-0 px-md-2">
      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold mb-4">보류 편지</h5>
            {letters.length === 0 ? (
              <div className="text-center py-5 text-muted">보류된 편지가 없습니다.</div>
            ) : (
              <div className="table-responsive">
                <table className="table table-hover align-middle mb-0" style={{ fontSize: '0.85rem' }}>
                  <thead className="table-light">
                    <tr>
                      <th>ID</th>
                      <th>제목</th>
                      <th>내용</th>
                      <th>보낸사람</th>
                      <th>받은사람</th>
                      <th>날짜</th>
                    </tr>
                  </thead>
                  <tbody>
                    {letters.map(letter => (
                      <tr key={letter.id}>
                        <td className="text-muted small">{letter.id}</td>
                        <td className="fw-semibold">{letter.subject}</td>
                        <td className="small text-muted">
                          {letter.content.length > 80
                            ? letter.content.substring(0, 80) + '…'
                            : letter.content}
                        </td>
                        <td>{letter.sender_name}</td>
                        <td>{letter.receiver_id}</td>
                        <td className="small text-muted">
                          {new Date(letter.created_at).toLocaleDateString()}
                        </td>
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
