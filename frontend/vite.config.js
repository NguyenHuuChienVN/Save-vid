import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    allowedHosts: [
      'kindle-landslide-revenue.ngrok-free.app',
      'kindle-landslide-revenue.ngrok-free.dev',
    ],
  }
})