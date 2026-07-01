import { useEffect } from 'react'

export default function App() {
  useEffect(() => {
    window.location.href = 'http://localhost:5000'
  }, [])
  return null
}
