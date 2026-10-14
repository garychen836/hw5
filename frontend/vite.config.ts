import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The board runs on http://localhost:5173 and calls the FastAPI backend
// directly at http://localhost:8000 (the backend allows this origin via CORS).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
})
