import { useNavigate, useLocation } from 'react-router-dom'

const MENUS = [
  { path: '/admin', label: '대시보드', icon: '🏠' },
  { path: '/admin/users', label: '회원관리', icon: '👥' },
  { path: '/admin/news', label: '소식관리', icon: '📰' },
  { path: '/admin/share-reports', label: '공유관리', icon: '📍' },
  { path: '/admin/stores', label: '가게관리', icon: '🏪' },
  { path: '/admin/alerts', label: '알림관리', icon: '🚨' },
  { path: '/admin/ai-chat', label: 'AI 채팅', icon: '🤖' },
  { path: '/admin/ai-feedback', label: 'AI 피드백', icon: '📋' },
  { path: '/admin/ai-train', label: 'AI 가르치기', icon: '📚' },
  { path: '/admin/pending-letters', label: '보류편지', icon: '📨' },
  { path: '/admin/page-managers', label: '페이지관리자', icon: '🔑' },
  { path: '/admin/postgresql', label: 'DB관리', icon: '🗄️' },
  { path: '/admin/ramp-applications', label: '경사로', icon: '♿' },
  { path: '/admin/message', label: '쪽지발송', icon: '✉️' },
]

export default function AdminNav() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <div className="d-flex flex-wrap gap-1 mb-3 pb-2 border-bottom" style={{ overflowX: 'auto', whiteSpace: 'nowrap' }}>
      {MENUS.map(m => (
        <button
          key={m.path}
          onClick={() => navigate(m.path)}
          className={`btn btn-sm ${location.pathname === m.path ? 'btn-success' : 'btn-outline-secondary'}`}
        >
          {m.icon} {m.label}
        </button>
      ))}
    </div>
  )
}
