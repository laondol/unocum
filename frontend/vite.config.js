import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:5000',
      '/login': 'http://localhost:5000',
      '/logout': 'http://localhost:5000',
      '/register': 'http://localhost:5000',
      '/intro': 'http://localhost:5000',
      '/static': 'http://localhost:5000',
    }
  },
  build: {
    outDir: '../static/spa',
    emptyOutDir: true
  }
})
