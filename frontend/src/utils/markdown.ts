/**
 * Lightweight, XSS-safe Markdown & Code Syntax Highlighter for GeoHarvest AI.
 *
 * Uses Fieldwork Studio CSS variables (`--code-bg`, `--code-keyword`,
 * `--code-string`, `--code-comment`, `--accent-turquoise`) so both Day
 * and Night themes render code blocks natively without external deps.
 */

export function escapeHtml(raw: string): string {
  return raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const PYTHON_KEYWORDS = new Set([
  'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break',
  'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally',
  'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal',
  'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield',
])

const JS_KEYWORDS = new Set([
  'async', 'await', 'break', 'case', 'catch', 'class', 'const', 'continue',
  'default', 'delete', 'do', 'else', 'export', 'extends', 'false', 'finally',
  'for', 'from', 'function', 'if', 'import', 'in', 'instanceof', 'interface',
  'let', 'new', 'null', 'of', 'return', 'static', 'super', 'switch', 'this',
  'throw', 'true', 'try', 'type', 'typeof', 'undefined', 'var', 'void', 'while',
])

const SQL_KEYWORDS = new Set([
  'ALL', 'AND', 'AS', 'ASC', 'BETWEEN', 'BY', 'CASE', 'CREATE', 'DELETE',
  'DESC', 'DISTINCT', 'DROP', 'ELSE', 'END', 'EXISTS', 'FROM', 'GROUP',
  'HAVING', 'IN', 'INNER', 'INSERT', 'INTO', 'IS', 'JOIN', 'LEFT', 'LIKE',
  'LIMIT', 'NOT', 'NULL', 'ON', 'OR', 'ORDER', 'OUTER', 'RIGHT', 'SELECT',
  'SET', 'TABLE', 'THEN', 'UNION', 'UPDATE', 'VALUES', 'WHEN', 'WHERE', 'WITH',
])

const BASH_KEYWORDS = new Set([
  'case', 'cd', 'curl', 'docker', 'do', 'done', 'echo', 'elif', 'else', 'esac',
  'export', 'fi', 'for', 'function', 'if', 'in', 'local', 'python', 'pytest',
  'return', 'set', 'then', 'until', 'while',
])

function resolveKeywordSet(lang: string): Set<string> | null {
  const norm = lang.toLowerCase().trim()
  if (norm === 'py' || norm === 'python') return PYTHON_KEYWORDS
  if (['js', 'jsx', 'ts', 'tsx', 'javascript', 'typescript'].includes(norm)) return JS_KEYWORDS
  if (norm === 'sql' || norm === 'postgres' || norm === 'postgresql') return SQL_KEYWORDS
  if (['sh', 'bash', 'zsh', 'shell'].includes(norm)) return BASH_KEYWORDS
  return null
}

/**
 * Single-pass tokenizer avoids corrupting injected HTML attributes.
 */
export function highlightCode(code: string, lang: string): string {
  const norm = (lang || '').toLowerCase().trim()
  const keywords = resolveKeywordSet(norm)

  // JSON gets specialized key / value highlighting
  if (norm === 'json') {
    const jsonToken = /("(?:\\.|[^"\\])*")\s*:|("(?:\\.|[^"\\])*")|\b(true|false|null)\b|\b(-?\d+(?:\.\d+)?)\b/g
    let out = ''
    let lastIndex = 0
    for (const match of code.matchAll(jsonToken)) {
      const idx = match.index ?? 0
      out += escapeHtml(code.slice(lastIndex, idx))
      if (match[1]) {
        out += `<span style="color:var(--accent-turquoise)">${escapeHtml(match[1])}</span>:`
      } else if (match[2]) {
        out += `<span style="color:var(--code-string)">${escapeHtml(match[2])}</span>`
      } else if (match[3]) {
        out += `<span style="color:var(--code-keyword)">${escapeHtml(match[3])}</span>`
      } else if (match[4]) {
        out += `<span style="color:var(--code-number, var(--accent-turquoise))">${escapeHtml(match[4])}</span>`
      }
      lastIndex = idx + match[0].length
    }
    out += escapeHtml(code.slice(lastIndex))
    return out
  }

  const tokenRegex =
    /(#[^\n]*|\/\/[^\n]*|\/\*[\s\S]*?\*\/)|("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)|\b(\d+(?:\.\d+)?)\b|\b([A-Za-z_][A-Za-z0-9_]*)\b/g

  let result = ''
  let lastIdx = 0
  for (const m of code.matchAll(tokenRegex)) {
    const idx = m.index ?? 0
    result += escapeHtml(code.slice(lastIdx, idx))

    if (m[1]) {
      result += `<span style="color:var(--code-comment);font-style:italic">${escapeHtml(m[1])}</span>`
    } else if (m[2]) {
      result += `<span style="color:var(--code-string)">${escapeHtml(m[2])}</span>`
    } else if (m[3]) {
      result += `<span style="color:var(--code-number, var(--accent-turquoise))">${escapeHtml(m[3])}</span>`
    } else if (m[4]) {
      const word = m[4]
      const isKw =
        keywords?.has(word) ||
        (norm === 'sql' && SQL_KEYWORDS.has(word.toUpperCase())) ||
        (!keywords && (PYTHON_KEYWORDS.has(word) || JS_KEYWORDS.has(word)))
      if (isKw) {
        result += `<span style="color:var(--code-keyword);font-weight:600">${escapeHtml(word)}</span>`
      } else {
        result += escapeHtml(word)
      }
    }
    lastIdx = idx + m[0].length
  }

  result += escapeHtml(code.slice(lastIdx))
  return result
}

function renderCodeBlockHtml(code: string, lang: string): string {
  const displayLang = escapeHtml((lang || 'code').trim() || 'code')
  const highlighted = highlightCode(code.replace(/\n$/, ''), lang)
  const encodedRaw = encodeURIComponent(code.replace(/\n$/, ''))
  return (
    `<div class="gh-code-card">` +
    `<div class="gh-code-card-head">` +
    `<span class="gh-code-lang">${displayLang}</span>` +
    `<button type="button" class="gh-code-copy-btn" data-copy-code="${encodedRaw}">Copy</button>` +
    `</div>` +
    `<pre class="gh-code-pre"><code>${highlighted}</code></pre>` +
    `</div>`
  )
}

function renderInlineMarkdown(text: string): string {
  // Split out inline `code` spans first so markdown symbols inside code stay literal
  const parts = text.split(/(`[^`\n]+`)/g)
  return parts
    .map((part) => {
      if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
        return `<code class="gh-inline-code">${escapeHtml(part.slice(1, -1))}</code>`
      }
      let safe = escapeHtml(part)
      // Safe links [label](url) - allow only http(s) or relative '/'
      safe = safe.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, label: string, url: string) => {
        if (/^(https?:\/\/|\/)/i.test(url)) {
          return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="gh-md-link">${label}</a>`
        }
        return `${label} (${url})`
      })
      safe = safe.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      safe = safe.replace(/__([^_]+)__/g, '<strong>$1</strong>')
      safe = safe.replace(/(^|[^\*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
      safe = safe.replace(/(^|[^_])_([^_\n]+)_/g, '$1<em>$2</em>')
      return safe
    })
    .join('')
}

function renderTextBlocks(markdown: string): string {
  const lines = markdown.split(/\r?\n/)
  const out: string[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]
    const trimmed = line.trim()

    if (!trimmed) {
      i++
      continue
    }

    // Horizontal rule
    if (/^(\*{3,}|-{3,}|_{3,})$/.test(trimmed)) {
      out.push('<hr class="gh-md-hr" />')
      i++
      continue
    }

    // Headings # ... ####
    const headingMatch = trimmed.match(/^(#{1,4})\s+(.+)$/)
    if (headingMatch) {
      const level = headingMatch[1].length
      out.push(`<h${level} class="gh-md-h${level}">${renderInlineMarkdown(headingMatch[2])}</h${level}>`)
      i++
      continue
    }

    // Blockquote
    if (trimmed.startsWith('>')) {
      const quoteLines: string[] = []
      while (i < lines.length && lines[i].trim().startsWith('>')) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ''))
        i++
      }
      out.push(`<blockquote class="gh-md-quote">${renderInlineMarkdown(quoteLines.join('<br/>'))}</blockquote>`)
      continue
    }

    // Markdown table (| a | b |)
    if (trimmed.startsWith('|') && i + 1 < lines.length && /^\s*\|[\s:-]+\|/.test(lines[i + 1])) {
      const headerCells = trimmed.split('|').slice(1, -1).map((c) => c.trim())
      i += 2 // skip header + separator
      const rows: string[][] = []
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        rows.push(lines[i].trim().split('|').slice(1, -1).map((c) => c.trim()))
        i++
      }
      const thHtml = headerCells.map((h) => `<th>${renderInlineMarkdown(h)}</th>`).join('')
      const bodyHtml = rows
        .map((r) => `<tr>${r.map((c) => `<td>${renderInlineMarkdown(c)}</td>`).join('')}</tr>`)
        .join('')
      out.push(`<div class="gh-md-table-wrap"><table class="gh-md-table"><thead><tr>${thHtml}</tr></thead><tbody>${bodyHtml}</tbody></table></div>`)
      continue
    }

    // Unordered list
    if (/^[-*+]\s+/.test(trimmed)) {
      const items: string[] = []
      while (i < lines.length && /^\s*[-*+]\s+/.test(lines[i])) {
        items.push(`<li>${renderInlineMarkdown(lines[i].trim().replace(/^[-*+]\s+/, ''))}</li>`)
        i++
      }
      out.push(`<ul class="gh-md-ul">${items.join('')}</ul>`)
      continue
    }

    // Ordered list
    if (/^\d+\.\s+/.test(trimmed)) {
      const items: string[] = []
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(`<li>${renderInlineMarkdown(lines[i].trim().replace(/^\d+\.\s+/, ''))}</li>`)
        i++
      }
      out.push(`<ol class="gh-md-ol">${items.join('')}</ol>`)
      continue
    }

    // Paragraph (gather until blank line or structural delimiter)
    const paraLines: string[] = []
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^(#{1,4}\s+|>|[-*+]\s+|\d+\.\s+|\|)/.test(lines[i].trim())
    ) {
      paraLines.push(lines[i].trim())
      i++
    }
    out.push(`<p class="gh-md-p">${renderInlineMarkdown(paraLines.join(' '))}</p>`)
  }

  return out.join('')
}

/**
 * Converts Markdown (including closed AND in-progress streaming fenced code blocks)
 * into sanitized semantic HTML.
 */
export function renderMarkdown(source: string): string {
  if (!source) return ''

  const parts: string[] = []
  const fenceRegex = /```([^\n`]*)\n([\s\S]*?)```/g
  let lastIndex = 0

  for (const match of source.matchAll(fenceRegex)) {
    const start = match.index ?? 0
    if (start > lastIndex) {
      parts.push(renderTextBlocks(source.slice(lastIndex, start)))
    }
    parts.push(renderCodeBlockHtml(match[2], match[1]))
    lastIndex = start + match[0].length
  }

  const tail = source.slice(lastIndex)
  // Support an open fenced code block still arriving mid-stream
  const openFenceIdx = tail.indexOf('```')
  if (openFenceIdx !== -1) {
    const before = tail.slice(0, openFenceIdx)
    if (before.trim()) {
      parts.push(renderTextBlocks(before))
    }
    const afterOpen = tail.slice(openFenceIdx + 3)
    const nlIdx = afterOpen.indexOf('\n')
    const lang = nlIdx === -1 ? afterOpen : afterOpen.slice(0, nlIdx)
    const code = nlIdx === -1 ? '' : afterOpen.slice(nlIdx + 1)
    parts.push(renderCodeBlockHtml(code, lang))
  } else if (tail.trim()) {
    parts.push(renderTextBlocks(tail))
  }

  return parts.join('')
}
