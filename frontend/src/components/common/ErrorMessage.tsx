interface ErrorMessageProps {
  message: string
  onRetry?: () => void
}

export default function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div className="alert alert-danger text-center py-4" role="alert">
      <div className="fs-3 mb-2">⚠️</div>
      <p className="mb-2">{message}</p>
      {onRetry && (
        <button className="btn btn-sm btn-outline-danger" onClick={onRetry}>
          다시 시도
        </button>
      )}
    </div>
  )
}
