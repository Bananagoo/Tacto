import { copyFileSync, createReadStream, existsSync, mkdirSync } from 'node:fs'
import { createRequire } from 'node:module'
import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

// The voice detector that hears when a spoken answer starts and ends (@ricky0123/vad-web)
// fetches its model, its audio worklet and the ONNX runtime at run time. They are served
// from this laptop, under /vad/, straight out of node_modules: nothing is fetched from a
// CDN and nothing large is committed.
const require = createRequire(import.meta.url)
const vadDist = path.dirname(require.resolve('@ricky0123/vad-web'))
const ortDist = path.dirname(require.resolve('onnxruntime-web', { paths: [vadDist] }))
const VAD_FILE =
  /^(silero_vad_legacy\.onnx|vad\.worklet\.bundle\.min\.js|ort-wasm-simd-threaded(\.jsep|\.asyncify|\.jspi)?\.(wasm|mjs))$/
const VAD_TYPES: Record<string, string> = {
  '.onnx': 'application/octet-stream',
  '.wasm': 'application/wasm',
  '.mjs': 'text/javascript',
  '.js': 'text/javascript',
}

function vadFile(name: string): string | undefined {
  if (!VAD_FILE.test(name)) return undefined
  return [vadDist, ortDist].map((folder) => path.join(folder, name)).find(existsSync)
}

function vadAssets(): Plugin {
  let outDir = 'dist'
  return {
    name: 'tacto-vad-assets',
    configResolved(config) {
      outDir = path.resolve(config.root, config.build.outDir)
    },
    configureServer(server) {
      server.middlewares.use('/vad', (request, response, next) => {
        const name = (request.url ?? '').split('?')[0].replace(/^\//, '')
        const file = vadFile(name)
        if (!file) return next()
        response.setHeader('Content-Type', VAD_TYPES[path.extname(name)])
        createReadStream(file).pipe(response)
      })
    },
    closeBundle() {
      const names = [
        'silero_vad_legacy.onnx',
        'vad.worklet.bundle.min.js',
        'ort-wasm-simd-threaded.wasm',
        'ort-wasm-simd-threaded.mjs',
        'ort-wasm-simd-threaded.jsep.wasm',
        'ort-wasm-simd-threaded.jsep.mjs',
      ]
      mkdirSync(path.join(outDir, 'vad'), { recursive: true })
      for (const name of names) {
        const file = vadFile(name)
        if (file) copyFileSync(file, path.join(outDir, 'vad', name))
      }
    },
  }
}

// The page talks to the Python server through this proxy, so there is one origin
// and no CORS setup. Server: `make server` on port 8000.
export default defineConfig({
  plugins: [react(), tailwindcss(), vadAssets()],
  server: {
    port: 5173,
    proxy: {
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
      '/speech': { target: 'http://127.0.0.1:8000', ws: true },
      '/voice': { target: 'http://127.0.0.1:8000' },
      '/api': { target: 'http://127.0.0.1:8000', rewrite: (p) => p.replace(/^\/api/, '') },
    },
  },
})
