import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/static': 'http://localhost:5000',
      '/favicon.ico': 'http://localhost:5000',
    }
  },
  build: {
    outDir: '../static/spa',
    emptyOutDir: true
  }
})
