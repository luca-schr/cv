import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // 0 est ambigu selon les versions http-proxy — explicite pour Ollama (~1–2 min)
        timeout: 180_000,
        proxyTimeout: 180_000,
      },
    },
  },
})
