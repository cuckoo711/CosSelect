const MAX_PIXELS = 5_000_000 // <= 5 megapixels
const JPEG_QUALITY = 0.85

/**
 * Compress an image File in the browser: downscale to <= 5MP and re-encode as
 * JPEG. Falls back to the original File if the browser can't decode it
 * (e.g. HEIC) or on any error, so the server-side safety net still applies.
 */
export async function compressImage(file: File): Promise<File> {
  if (!file.type.startsWith('image/')) return file
  // GIF may be animated; don't flatten it here, let the server handle it.
  if (file.type === 'image/gif') return file

  try {
    const bitmap = await loadBitmap(file)
    const { width, height } = bitmap
    const pixels = width * height

    let targetW = width
    let targetH = height
    if (pixels > MAX_PIXELS) {
      const scale = Math.sqrt(MAX_PIXELS / pixels)
      targetW = Math.max(1, Math.round(width * scale))
      targetH = Math.max(1, Math.round(height * scale))
    }

    const canvas = document.createElement('canvas')
    canvas.width = targetW
    canvas.height = targetH
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      closeBitmap(bitmap)
      return file
    }
    ctx.drawImage(bitmap as CanvasImageSource, 0, 0, targetW, targetH)
    closeBitmap(bitmap)

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY),
    )
    if (!blob) return file

    // If the "compressed" result is somehow larger and no resize happened, keep original.
    if (blob.size >= file.size && targetW === width && targetH === height) return file

    const newName = file.name.replace(/\.[^.]+$/, '') + '.jpg'
    return new File([blob], newName, { type: 'image/jpeg', lastModified: Date.now() })
  } catch {
    return file
  }
}

async function loadBitmap(file: File): Promise<ImageBitmap | HTMLImageElement> {
  if ('createImageBitmap' in window) {
    try {
      return await createImageBitmap(file)
    } catch {
      /* fall back to <img> */
    }
  }
  return await new Promise<HTMLImageElement>((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('decode failed'))
    }
    img.src = url
  })
}

function closeBitmap(b: ImageBitmap | HTMLImageElement) {
  if ('close' in b && typeof b.close === 'function') b.close()
}
