import { useEffect, useState } from 'react'
import Loading from '../components/common/Loading'
import ErrorMessage from '../components/common/ErrorMessage'

interface AdminPost {
  id: number
  title: string
  content: string
  file_path: string | null
  total_score: number | null
  is_forced_approved: boolean
  created_at: string
}

function getStatus(post: AdminPost): { label: string; color: string } {
  if (post.total_score != null && post.total_score <= -50) {
    return { label: '낙제', color: 'danger' }
  }
  if (post.is_forced_approved) {
    return { label: '강제승인', color: 'success' }
  }
  return { label: '검토중', color: 'warning' }
}

function filePreview(path: string | null) {
  if (!path) return <span className="text-muted">-</span>
  const ext = path.split('.').pop()?.toLowerCase()
  if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext || '')) {
    return <img src={path} alt="" style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: 8 }} />
  }
  if (ext === 'pdf') {
    return <span title="PDF">📄</span>
  }
  return <span title="파일">📎</span>
}

export default function AdminDashboard() {
  const [posts, setPosts] = useState<AdminPost[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchPosts = () => {
    setLoading(true)
    setError('')
    fetch('/api/admin/posts')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(data => setPosts(Array.isArray(data) ? data : []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchPosts() }, [])

  return (
    <div className="px-0 px-md-2">
      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold mb-4">📋 게시글 관리</h5>
            {loading ? (
              <Loading />
            ) : error ? (
              <ErrorMessage message={error} onRetry={fetchPosts} />
            ) : posts.length === 0 ? (
              <div className="text-center py-5 text-muted">
                <p>게시글이 없습니다.</p>
              </div>
            ) : (
              <div className="table-responsive">
                <table className="table table-hover align-middle mb-0">
                  <thead className="table-light">
                    <tr>
                      <th>ID</th>
                      <th>제목</th>
                      <th>첨부파일</th>
                      <th>총점</th>
                      <th>상태</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {posts.map(post => (
                      <tr key={post.id}>
                        <td className="text-muted small">{post.id}</td>
                        <td>
                          <div className="fw-semibold">{post.title}</div>
                          {post.content && (
                            <div className="small text-muted">{post.content.substring(0, 100)}</div>
                          )}
                        </td>
                        <td>{filePreview(post.file_path)}</td>
                        <td>
                          <span className={`fw-bold ${post.total_score != null && post.total_score <= -50 ? 'text-danger' : ''}`}>
                            {post.total_score ?? 0}
                          </span>
                        </td>
                        <td>
                          <span className={`badge bg-${getStatus(post).color}`}>
                            {getStatus(post).label}
                          </span>
                        </td>
                        <td>
                          <a href={`/admin/post/${post.id}`} className="btn btn-sm btn-outline-success">
                            상세보기
                          </a>
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
