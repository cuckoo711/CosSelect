// Generate small thumbnails from local File objects without blowing up memory.
//
// Key ideas:
//  - decode-to-size via createImageBitmap({ resizeWidth }) so the full-res image
//    is never fully decoded into memory (a 6000x4000 photo decodes to ~96MB!)
//  - a small concurrency limit so we never decode many big images at once
//  - callers should revoke the returned object URL when done

const MAX_CONCURRENT = 3
let active = 0
const waiters: Array<() => void> = []

function acquire(): Promise<void> {
  if (active < MAX_CONCURRENT) {
    active += 1
    return Promise.resolve()
  }
  return new Promise<void>((resolve) => waiters.push(resolve)).then(() => {
    active += 1
  })
}

function release() {
  active -= 1
  const next = waiters.shift()
  if (next) next()
}

/**
 * Create a small JPEG thumbnail object URL for a local image File.
 * @param file source image
 * @param size max width in px (height scales proportionally)
 */
export async function createThumbUrl(file: File, size = 240): Promise<string> {
  await acquire()
  try {
    let bmp: ImageBitmap
    try {
      // Preferred: decode directly at a small width -> minimal memory.
      bmp = await createImageBitmap(file, { resizeWidth: size, resizeQuality: 'low' } as any)
    } catch {
      // Fallback for browsers ignoring resizeWidth: decode then downscale.
      bmp = await createImageBitmap(file)
    }

    // If the fallback path produced a large bitmap, compute a scaled canvas.
    let tw = bmp.width
    let th = bmp.height
    if (tw > size) {
      th = Math.max(1, Math.round((th * size) / tw))
      tw = size
    }

    const canvas = document.createElement('canvas')
    canvas.width = tw
    canvas.height = th
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      bmp.close?.()
      throw new Error('no 2d context')
    }
    ctx.drawImage(bmp, 0, 0, tw, th)
    bmp.close?.()

    const blob = await new Promise<Blob | null>((r) => canvas.toBlob(r, 'image/jpeg', 0.7))
    // free canvas memory promptly
    canvas.width = 0
    canvas.height = 0
    if (!blob) throw new Error('thumb encode failed')
    return URL.createObjectURL(blob)
  } finally {
    release()
  }
}
