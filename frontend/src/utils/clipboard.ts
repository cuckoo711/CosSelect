import { ElMessage } from 'element-plus'

/**
 * Copy text to clipboard with a fallback for non-secure (http) contexts,
 * where navigator.clipboard is unavailable.
 */
export async function copyText(text: string): Promise<boolean> {
  // Preferred: async clipboard API (needs HTTPS or localhost)
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      ElMessage.success('已复制')
      return true
    } catch {
      /* fall through to legacy */
    }
  }

  // Fallback: hidden textarea + execCommand (works over http)
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', '')
    ta.style.position = 'fixed'
    ta.style.top = '0'
    ta.style.left = '0'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.focus()
    ta.select()
    ta.setSelectionRange(0, ta.value.length)
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    if (ok) {
      ElMessage.success('已复制')
      return true
    }
  } catch {
    /* ignore */
  }

  ElMessage.warning('复制失败，请手动长按选择文本')
  return false
}

/** Trigger a browser download of the given text content as a file. */
export function downloadText(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
