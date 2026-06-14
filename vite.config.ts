import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'
import http from 'node:http'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // 載入當前 mode 的環境變數 (第三個參數為 '' 載入所有變數)
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [
      vue(),
      tailwindcss(),
    ],
    server: {
      proxy: {
        '/api': {
          target: env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
          changeOrigin: true,
          agent: new http.Agent({ 
            keepAlive: true, 
            keepAliveMsecs: parseInt(env.VITE_PROXY_KEEPALIVE_MSECS || '10000', 10) 
          })
        }
      }
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    }
  }
})
