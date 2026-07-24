export default function Loading({ text = '불러오는 중...' }: { text?: string }) {
  return (
    <div className="text-center py-5 text-muted">
      <div className="spinner-border spinner-border-sm mb-2" role="status" />
      <p className="small">{text}</p>
    </div>
  )
}
