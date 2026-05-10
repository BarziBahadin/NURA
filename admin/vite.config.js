import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

function apiOrigin() {
  const origin = process.env.NURA_API_ORIGIN || process.env.VITE_NURA_API_ORIGIN || ''
  if (!origin || origin.includes('x.x')) return 'http://localhost:8080'
  return origin
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/v1': {
        target: apiOrigin(),
        changeOrigin: false,
        xfwd: true,
        ws: true,
      },
    },
  },
})
