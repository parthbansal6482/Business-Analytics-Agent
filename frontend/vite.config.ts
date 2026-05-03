import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    host: true,
    allowedHosts: [
      "agent.zerocores.in",
      "zerocores.in",
      ".zerocores.in"
    ]
  },
  define: {
    __BUILD_DATE__: JSON.stringify(new Date().toISOString()),
  }
})