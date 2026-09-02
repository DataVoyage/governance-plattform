/// <reference types="vitest/config" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  // Unterpfad, unter dem die Anwendung ausgeliefert wird (z.B. hinter einem
  // Reverse Proxy). Leer bzw. ungesetzt bedeutet: an der Wurzel.
  base: process.env.VITE_BASIS_PFAD || '/',
  plugins: [react()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: { port: 5173, host: true },
  preview: { port: 4173, host: true },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.test.tsx', 'tests/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/main.tsx', 'src/**/*.d.ts'],
      thresholds: { lines: 90, statements: 90, functions: 90, branches: 85 },
    },
  },
});
