// Web Worker: decode + downscale an image File to a small JPEG blob.
// Runs off the main thread so scrolling stays smooth even with big originals.

interface ReqMsg {
  id: number
  file: File
  size: number
}
interface OkMsg {
  id: number
  ok: true
  blob: Blob
}
interface ErrMsg {
  id: number
  ok: false
  error: string
}

self.onmessage = async (e: MessageEvent<ReqMsg>) => {
  const { id, file, size } = e.data
  try {
    let bmp: ImageBitmap
    try {
      bmp = await createImageBitmap(file, {
        resizeWidth: size,
        resizeQuality: 'low',
      } as any)
    } catch {
      bmp = await createImageBitmap(file)
    }

    let tw = bmp.width
    let th = bmp.height
    if (tw > size) {
      th = Math.max(1, Math.round((th * size) / tw))
      tw = size
    }

    const canvas = new OffscreenCanvas(tw, th)
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('no ctx')
    ctx.drawImage(bmp, 0, 0, tw, th)
    bmp.close?.()

    const blob = await canvas.convertToBlob({ type: 'image/jpeg', quality: 0.7 })
    const msg: OkMsg = { id, ok: true, blob }
    ;(self as any).postMessage(msg)
  } catch (err: any) {
    const msg: ErrMsg = { id, ok: false, error: String(err?.message || err) }
    ;(self as any).postMessage(msg)
  }
}
