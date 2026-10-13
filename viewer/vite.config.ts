import { defineConfig } from 'vite';

// The built archives are served from build/, with range requests, as /window/… .
export default defineConfig({
  publicDir: '../build',
  server: { port: 5174, strictPort: true },
});
