import { defineConfig } from 'vite';
// Base relativa funciona tanto no domínio customizado quanto em /nome-do-repositorio/.
export default defineConfig({ base: './', build: { target: 'es2020', cssCodeSplit: true, chunkSizeWarningLimit: 750 } });
