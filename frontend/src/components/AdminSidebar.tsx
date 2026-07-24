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
]

export default function AdminSidebar() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
      <div className="card-body p-3">
        <h6 className="fw-bold text-success mb-3 px-2">🛡️ 관리 메뉴</h6>
        {MENUS.map(m => (
          <div key={m.path}
            onClick={() => navigate(m.path)}
            style={{
              padding: '8px 12px', borderRadius: 10, cursor: 'pointer', fontSize: '0.9rem',
              background: location.pathname === m.path ? '#d4f4ec' : undefined,
              color: location.pathname === m.path ? '#0d6e5e' : undefined,
              fontWeight: location.pathname === m.path ? 600 : undefined,
            }}>
            {m.icon} {m.label}
          </div>
        ))}
      </div>
    </div>
  )
}
