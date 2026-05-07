/**
 * Fix "N.Title" -> "N. Title" in ### headings and TOC;
 * set (#fragment) to GitHub heading IDs (ordered slugger, incl. duplicates).
 */
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import GithubSlugger from 'github-slugger'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(__dirname, '..')

function fixHeadingLine(line) {
  return line.replace(/^###(\s+\d+)\.(?=\S)/, '###$1. ')
}

function normalizeTocLinkText(text) {
  return text.replace(/^(\d+)\.(?=\S)/, '$1. ')
}

/** Align TOC text with heading text for lookup (GitHub slugs ignore ** in headings). */
function tocMatchKey(text) {
  return normalizeTocLinkText(text.replace(/\*\*/g, '').trim())
}

function stripHeadingTitle(line) {
  const m = line.match(/^#{2,6}\s+(.+)$/)
  if (!m) return null
  let t = m[1].trim()
  t = t.replace(/\s+#+\s*$/, '').trim()
  return t
}

function processFile(relPath, tocHeaderRe) {
  const fp = path.join(root, relPath)
  let lines = fs.readFileSync(fp, 'utf8').split(/\r?\n/)

  lines = lines.map((line) =>
    /^###\s+\d+\.(?=\S)/.test(line) ? fixHeadingLine(line) : line
  )

  const slugger = new GithubSlugger()
  /** @type {Map<string, string[]>} */
  const slugQueues = new Map()
  for (const line of lines) {
    const title = stripHeadingTitle(line)
    if (!title) continue
    const slug = slugger.slug(title)
    const key = tocMatchKey(title)
    if (!slugQueues.has(key)) slugQueues.set(key, [])
    slugQueues.get(key).push(slug)
  }

  function takeSlug(key) {
    const q = slugQueues.get(key)
    if (!q || !q.length) return null
    return q.shift()
  }

  let inToc = false
  const out = []
  for (const line of lines) {
    if (tocHeaderRe.test(line)) {
      inToc = true
      out.push(line)
      continue
    }
    if (inToc) {
      if (/^##\s+/.test(line) && !line.startsWith('###')) {
        inToc = false
        out.push(line)
        continue
      }
      const m = line.match(/^(\s*-\s*\[)([^\]]+)(\]\(#)([^)]*)(\).*)$/)
      if (m) {
        const [, p1, rawText, p3, , p5] = m
        const linkText = normalizeTocLinkText(rawText)
        const slug = takeSlug(tocMatchKey(rawText))
        if (slug !== null) {
          out.push(`${p1}${linkText}${p3}${slug}${p5}`)
          continue
        }
      }
      out.push(line)
      continue
    }
    out.push(line)
  }

  fs.writeFileSync(fp, out.join('\n'), 'utf8')
  console.log('updated', relPath)
}

processFile('README.md', /^## Table of Contents\s*$/)
processFile('交易系统开发.md', /^## 目录\s*$/)
