import { fileURLToPath } from 'node:url';

const here = fileURLToPath(new URL('.', import.meta.url));
const modules = fileURLToPath(new URL('../../../frontend/node_modules/', import.meta.url));

// The page reuses the frontend's graph code and dependencies without its own install.
export default {
  root: here,
  cacheDir: modules + '.vite-demo-forming',
  resolve: { alias: Object.fromEntries(['graphology', 'graphology-layout-forceatlas2', 'sigma'].map(name => [name, modules + name])) },
  server: { port: 18090, strictPort: true, fs: { allow: [fileURLToPath(new URL('../../../', import.meta.url))] } },
};
