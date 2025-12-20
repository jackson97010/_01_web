import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const PORT = Number(process.env.DEV_PORT || 5173);

export default defineConfig({
  plugins: [react()],
  base: './', // 使用相對路徑，這對 Electron 很重要
  server: {
    port: PORT,
    strictPort: true
  },
  clearScreen: false,
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
});
