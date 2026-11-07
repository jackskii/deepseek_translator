import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

function serveReaderHtml() {
  return {
    name: 'serve-reader-html',
    configureServer(server: {
      middlewares: { use: (fn: (req: { url?: string }, res: unknown, next: () => void) => void) => void }
    }) {
      server.middlewares.use((req, _res, next) => {
        const raw = req.url ?? ''
        const path = raw.split('?')[0]
        if (
          path.startsWith('/@') ||
          path.startsWith('/src/') ||
          path.startsWith('/node_modules') ||
          path.startsWith('/api') ||
          path === '/reader.html' ||
          path === '/favicon.svg'
        ) {
          next()
          return
        }
        if (path === '/' || path === '/index.html' || path.startsWith('/work/')) {
          req.url = '/reader.html' + (raw.includes('?') ? '?' + raw.split('?').slice(1).join('?') : '')
        }
        next()
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), serveReaderHtml()],
  appType: 'spa',
  server: {
    port: 5174,
    host: true,
    open: false,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
