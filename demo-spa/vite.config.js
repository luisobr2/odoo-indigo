import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base relativa: necesario cuando la SPA se embebe dentro de wp-admin
export default defineConfig({
  plugins: [react()],
  base: './',
})
