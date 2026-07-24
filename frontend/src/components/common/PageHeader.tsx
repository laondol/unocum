interface PageHeaderProps {
  title: string
  subtitle?: string
  action?: { label: string; href?: string; onClick?: () => void }
}

export default function PageHeader({ title, subtitle, action }: PageHeaderProps) {
  return (
    <div className="d-flex justify-content-between align-items-center mb-4">
      <div>
        <h4 className="fw-bold mb-1">{title}</h4>
        {subtitle && <p className="text-muted small mb-0">{subtitle}</p>}
      </div>
      {action && (
        action.href
          ? <a href={action.href} className="btn btn-sm btn-outline-primary">{action.label}</a>
          : <button className="btn btn-sm btn-outline-primary" onClick={action.onClick}>{action.label}</button>
      )}
    </div>
  )
}
