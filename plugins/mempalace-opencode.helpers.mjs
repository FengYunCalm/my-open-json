const SMALL_TALK = new Set(['ok', 'okay', 'yes', 'no', 'thanks', 'thank you', 'continue', 'start', 'go'])

export function collectText(parts = []) {
  return parts
    .filter((part) => part?.type === 'text' && typeof part.text === 'string' && part.text.trim())
    .map((part) => part.text.trim())
    .join('\n\n')
}

export function shouldSearch(text, config = {}) {
  const normalized = (text || '').trim().toLowerCase()
  if (!normalized) return false
  if (normalized.startsWith('/')) return false
  if (normalized.includes('<command-message>')) return false
  if (SMALL_TALK.has(normalized)) return false
  return normalized.length >= (config.minSearchChars ?? 16)
}

export function messagesSinceCheckpoint(messages = [], checkpoint = null) {
  if (!checkpoint) return [...messages]
  const index = messages.findIndex((message) => message?.info?.id === checkpoint)
  if (index === -1) return [...messages]
  return messages.slice(index + 1)
}

export function buildSystemBlock(payload, maxChars = 1800) {
  if (!payload?.results?.length) return ''
  const lines = [
    `MemPalace context for wing '${payload.wing ?? 'unknown'}':`,
  ]
  let used = lines[0].length
  for (const [index, item] of payload.results.entries()) {
    const header = `${index + 1}. [${Number(item.similarity ?? 0).toFixed(2)}] room=${item.room ?? 'unknown'} role=${item.role ?? 'unknown'} src=${item.source_file ?? '?'}`
    if (used + header.length + 1 > maxChars) break
    lines.push(header)
    used += header.length + 1

    const remaining = maxChars - used - 4
    if (remaining <= 0) break
    const rawText = String(item.text ?? item.preview ?? '')
      .replace(/\s+/g, ' ')
      .trim()
    if (!rawText) continue
    const body = rawText.length > remaining ? `${rawText.slice(0, Math.max(0, remaining - 1))}…` : rawText
    lines.push(`   ${body}`)
    used += body.length + 4
  }
  return lines.join('\n')
}
