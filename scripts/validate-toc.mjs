import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import GithubSlugger from 'github-slugger'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(__dirname, '..')

function stripHeadingTitle(line) {
  const m = line.match(/^#{2,6}\s+(.+)$/)
  if (!m) return null
  let t = m[1].trim().replace(/\s+#+\s*$/, '').trim()
  return t
}

function check(relPath, tocHeader) {
  const fp = path.join(root, relPath)
  const lines = fs.readFileSync(fp, 'utf8').split(/\r?\n/)
  const slugger = new GithubSlugger()
  const slugs = new Set()
  for (const line of lines) {
    const t = stripHeadingTitle(line)
    if (t) slugs.add(slugger.slug(t))
  }
  let inToc = false
  let bad = 0
  for (const line of lines) {
    if (new RegExp(`^${tocHeader}\\s*$`).test(line)) {
      inToc = true
      continue
    }
    if (inToc) {
      if (/^##\s+/.test(line) && !line.startsWith('###')) inToc = false
      const m = line.match(/\]\(#([^)]+)\)/)
      if (m && !slugs.has(m[1])) {
        console.error('missing anchor', m[1], 'in', relPath)
        bad++
      }
    }
  }
  return bad
}

const a = check('README.md', '## Table of Contents')
const b = check('交易系统开发.md', '## 目录')
process.exit(a + b > 0 ? 1 : 0)
