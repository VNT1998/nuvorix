import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const proxyConfig = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
  '/health': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
  '/ready': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
  '/metrics': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: proxyConfig,
  },
  preview: {
    port: 5173,
    proxy: proxyConfig,
  },
})
