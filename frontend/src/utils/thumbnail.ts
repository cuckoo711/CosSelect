// Generate small thumbnails from local File objects, fast and memory-safe.
//
// Strategy:
//  - A pool of Web Workers decodes + downscales off the main thread (parallel,
//    uses multiple CPU cores), so scrolling stays smooth even with big originals.
//  - Falls back to main-thread createImageBitmap if workers/OffscreenCanvas
//    aren't available.

type PendingResolver = { resolve: (b: Blob) => void; reject: (e: any) => void }

const POOL_SIZE = Math.min(
  6,
  Math.max(2, (navigator.hardwareConcurrency || 4) - 1),
)

let workers: Worker[] = []
let roundRobin = 0
let seq = 0
const pending = new Map<number, PendingResolver>()
let workersOk = true

function initWorkers() {
  if (workers.length || !workersOk) return
  if (typeof Worker === 'undefined' || typeof OffscreenCanvas === 'undefined') {
    workersOk = false
    return
  }
  try {
    for (let i = 0; i < POOL_SIZE; i++) {
      const w = new Worker(new URL('./thumbnailWorker.ts', import.meta.url), {
        type: 'module',
      })
      w.onmessage = (e: MessageEvent) => {
        const { id, ok, blob, error } = e.data
        const p = pending.get(id)
        if (!p) return
        pending.delete(id)
        if (ok) p.resolve(blob)
        else p.reject(new Error(error))
      }
      w.onerror = () => {
        /* worker-level error; individual tasks reject via timeout below */
      }
      workers.push(w)
    }
  } catch {
    workersOk = false
    workers.forEach((w) => w.terminate())
    workers = []
  }
}

function runInWorker(file: File, size: number): Promise<Blob> {
  const id = ++seq
  const w = workers[roundRobin++ % workers.length]
  return new Promise<Blob>((resolve, reject) => {
    pending.set(id, { resolve, reject })
    w.postMessage({ id, file, size })
  })
}

// ---- main-thread fallback (bounded concurrency) ----
const MAX_CONCURRENT = 3
let active = 0
const waiters: Array<() => void> = []
function acquire(): Promise<void> {
  if (active < MAX_CONCURRENT) {
    active += 1
    return Promise.resolve()
  }
  return new Promise<void>((r) => waiters.push(r)).then(() => {
    active += 1
  })
}
function release() {
  active -= 1
  waiters.shift()?.()
}

async function runOnMain(file: File, size: number): Promise<Blob> {
  await acquire()
  try {
    let bmp: ImageBitmap
    try {
      bmp = await createImageBitmap(file, { resizeWidth: size, resizeQuality: 'low' } as any)
    } catch {
      bmp = await createImageBitmap(file)
    }
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
    canvas.width = 0
    canvas.height = 0
    if (!blob) throw new Error('thumb encode failed')
    return blob
  } finally {
    release()
  }
}

/**
 * Create a small JPEG thumbnail object URL for a local image File.
 * Caller must URL.revokeObjectURL when done.
 */
export async function createThumbUrl(file: File, size = 240): Promise<string> {
  initWorkers()
  let blob: Blob
  if (workersOk && workers.length) {
    try {
      blob = await runInWorker(file, size)
    } catch {
      blob = await runOnMain(file, size)
    }
  } else {
    blob = await runOnMain(file, size)
  }
  return URL.createObjectURL(blob)
}
