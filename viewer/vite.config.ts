import { defineConfig } from 'vite';

// While developing, the built archives are served from build/, with range requests, as
// /window/… . A published viewer (scripts/publish.sh) sits beside its build's archives
// instead, so its build copies none of them and uses relative paths.
export default defineConfig(({ command }) => ({
  publicDir: command === 'serve' ? '../build' : false,
  base: './',
  server: { port: 5174, strictPort: true },
  // MapLibre alone is about 1 MB; one chunk is what the page needs anyway.
  build: { chunkSizeWarningLimit: 1500 },
}));
