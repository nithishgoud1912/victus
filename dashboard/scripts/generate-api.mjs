import { spawnSync } from 'node:child_process'
import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { createClient } from '@hey-api/openapi-ts'

const root = fileURLToPath(new URL('../../', import.meta.url))
const python = process.env.VICTUS_PYTHON ?? `${root}backend/.venv/${process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python'}`
const schemaPath = fileURLToPath(new URL('../openapi.json', import.meta.url))
const result = spawnSync(python, ['-c', 'from victus.cli import main; main()', 'export-openapi', '--output', schemaPath], {
  cwd: root, stdio: 'inherit', shell: false,
})
if (result.error || result.status !== 0) throw new Error('Backend schema export failed; prepare backend/.venv first.')

await createClient({
  input: schemaPath,
  output: fileURLToPath(new URL('../src/api/generated', import.meta.url)),
  plugins: ['@hey-api/typescript'],
})

// Only types are generated: all HTTP/authentication remains in client.ts.
const schema = JSON.parse(await readFile(schemaPath, 'utf8'))
const generated = await readFile(new URL('../src/api/generated/types.gen.ts', import.meta.url), 'utf8')
const entries = []
for (const [path, methods] of Object.entries(schema.paths)) {
  for (const [method, operation] of Object.entries(methods)) {
    if (!['get', 'post', 'delete'].includes(method)) continue
    const name = operation.operationId.split('_').filter(Boolean).map(part => part[0].toUpperCase() + part.slice(1)).join('')
    if (!generated.includes(`export type ${name}Data`) || !generated.includes(`export type ${name}Responses`)) {
      throw new Error(`Unsupported generated operation name: ${operation.operationId}`)
    }
    entries.push(`  ${JSON.stringify(`${method.toUpperCase()} ${path}`)}: { request: Types.${name}Data; response: Types.${name}Responses[keyof Types.${name}Responses] }`)
  }
}
await writeFile(new URL('../src/api/generated/operations.gen.ts', import.meta.url),
  `// Generated from the current backend OpenAPI schema. Do not edit.\nimport type * as Types from './types.gen'\n\nexport interface ApiOperations {\n${entries.join('\n')}\n}\n`)
