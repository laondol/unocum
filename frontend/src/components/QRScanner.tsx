import { useEffect, useRef, useState } from 'react'

interface QRScannerProps {
  onScan: (data: string) => void
  onError?: (err: string) => void
}

export default function QRScanner({ onScan, onError }: QRScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [scanning, setScanning] = useState(false)

  useEffect(() => {
    let scanner: any = null
    let mounted = true

    const init = async () => {
      try {
        const { Html5Qrcode } = await import('html5-qrcode')
        scanner = new Html5Qrcode('qr-reader')
        setScanning(true)
        await scanner.start(
          { facingMode: 'environment' },
          { fps: 10, qrbox: { width: 250, height: 250 } },
          (decodedText: string) => {
            if (mounted) {
              onScan(decodedText)
              scanner.stop().catch(() => {})
              setScanning(false)
            }
          },
          () => {}
        )
      } catch (e: unknown) {
        if (mounted) {
          setScanning(false)
          onError?.(e instanceof Error ? e.message : '카메라 접근 실패')
        }
      }
    }

    init()

    return () => {
      mounted = false
      if (scanner) scanner.stop().catch(() => {})
    }
  }, [])

  return (
    <div>
      <div id="qr-reader" style={{ width: '100%', maxWidth: 400 }} />
      {scanning && <div className="small text-muted mt-1">📷 QR 코드를 스캔하세요...</div>}
    </div>
  )
}
