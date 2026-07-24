interface EmptyStateProps {
  icon?: string
  title?: string
  message?: string
  action?: { label: string; href: string }
}

export default function EmptyState({ icon = '📭', title = '정보가 없습니다', message, action }: EmptyStateProps) {
  return (
    <div className="text-center py-5 text-muted">
      <div className="fs-1 mb-3">{icon}</div>
      <p className="fw-bold mb-1">{title}</p>
      {message && <p className="small mb-3">{message}</p>}
      {action && (
        <a href={action.href} className="btn btn-sm btn-outline-primary">
          {action.label}
        </a>
      )}
    </div>
  )
}
