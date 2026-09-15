import { defineConfig } from 'vite'
import path from 'node:path'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import { createHash } from 'node:crypto'

const here = path.dirname(fileURLToPath(import.meta.url))
const tactics = path.resolve(process.env.BRAVEN_TACTICS_PATH || path.join(here, '../../../../braven-tactics-netball-athlete'))
const assets = process.env.BRAVEN_ATHLETE_OUTPUT
if (!assets || !fs.existsSync(path.join(assets, 'netball-athlete.glb'))) {
  throw new Error('Set BRAVEN_ATHLETE_OUTPUT to the directory containing netball-athlete.glb.')
}
if (!fs.existsSync(path.join(tactics, 'src/engine/skinned.ts'))) throw new Error('Set BRAVEN_TACTICS_PATH to the Tactics checkout.')
const served = new Map([
  ['netball-athlete.glb', 'model/gltf-binary'], ['netball-athlete.blend', 'application/octet-stream'],
  ['athlete-source.blend', 'application/octet-stream'], ['manifest.json', 'application/json'],
  ['movement-library.json', 'application/json'],
])
function assetMiddleware(req, res, next) {
  const name = (req.url || '').split('?')[0].replace(/^\/athlete-assets\//, '')
  if (!req.url?.startsWith('/athlete-assets/') || !served.has(name)) return next()
  const file = path.join(assets, name)
  res.setHeader('Content-Type', served.get(name))
  // The generated model can also be loaded by a separate local Tactics instance.
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Cache-Control', 'no-cache')
  if (!fs.existsSync(file)) { res.statusCode = 404; res.end('Asset not built'); return }
  res.setHeader('Content-Length', fs.statSync(file).size)
  fs.createReadStream(file).pipe(res)
}
export default defineConfig({
  resolve: { alias: { '@tactics': path.join(tactics, 'src'), '@': path.join(tactics, 'src') }, dedupe: ['three'] },
  server: { fs: { allow: [here, tactics] } },
  plugins: [{ name: 'athlete-assets', configureServer(server) { server.middlewares.use(assetMiddleware) },
    closeBundle() {
      const destination = path.join(here, 'dist/athlete-assets')
      fs.mkdirSync(destination, { recursive: true })
      for (const name of served.keys()) fs.copyFileSync(path.join(assets, name), path.join(destination, name))
      const dist=path.dirname(destination)
      const files={}
      for(const name of ['index.html',...fs.readdirSync(path.join(dist,'assets')).sort().map(n=>'assets/'+n)]) {
        files[name]=createHash('sha256').update(fs.readFileSync(path.join(dist,name))).digest('hex')
      }
      const manifest=JSON.parse(fs.readFileSync(path.join(assets,'manifest.json'),'utf8'))
      const assetSha256=manifest.files['netball-athlete.glb'].sha256.toLowerCase()
      fs.writeFileSync(path.join(dist,'studio-build.json'),JSON.stringify({app:'braven-studio',schemaVersion:1,
        buildId:createHash('sha256').update(JSON.stringify({files,assetSha256})).digest('hex'),builtAt:new Date().toISOString(),assetSha256,files},null,2))
    } }],
})
