import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite's SPA fallback skips any URL that looks like a file (has an extension).
// Old chapter links ended in `.json`, so a refresh 404ed. Rewrite those to
// index.html so the router can load the viewer (which then strips `.json`).
function spaFallbackForChapterJson() {
  return {
    name: 'spa-fallback-chapter-json',
    configureServer(server: { middlewares: { use: (fn: (req: { url?: string }, res: unknown, next: () => void) => void) => void } }) {
      server.middlewares.use((req, _res, next) => {
        const path = (req.url ?? '').split('?')[0]
        if (/^\/work\/[^/]+\/chapters\//.test(path)) {
          req.url = '/index.html'
        }
        next()
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), spaFallbackForChapterJson()],
  appType: 'spa',
  server: {
    port: 5173,
    host: true,
    open: false,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
