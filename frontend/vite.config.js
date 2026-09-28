import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The backend has no CORS middleware (and must not be modified), so the dev
// server proxies /api to it. The browser only ever talks to one origin.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } } },
})
