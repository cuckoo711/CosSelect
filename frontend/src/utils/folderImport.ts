// Parse a dropped/selected folder tree into an import plan.
// Rules:
//  - keep only .jpg/.jpeg files (others filtered out)
//  - prune folders that contain no jpg anywhere
//  - strip the outermost container folder (its children become top-level categories)
//  - collapse single-child chains: a folder with no direct jpg and exactly one
//    child folder is ignored (its child is promoted)
//  - a folder maps to a category; its direct jpg files upload into that category

export interface ImportNode {
  name: string
  files: File[]
  children: ImportNode[]
}

const JPG_RE = /\.jpe?g$/i

export function isJpeg(file: File): boolean {
  return JPG_RE.test(file.name) || file.type === 'image/jpeg'
}

interface RawNode {
  name: string
  files: File[]
  children: Map<string, RawNode>
}

function newRaw(name: string): RawNode {
  return { name, files: [], children: new Map() }
}

/**
 * Build an import plan from a flat list of files that carry a relative path
 * (webkitRelativePath from <input webkitdirectory> or drag-drop entries).
 * Returns the list of top-level ImportNodes to create as categories, plus the
 * total jpg count and skipped (non-jpg) count.
 */
export function buildImportPlan(files: { file: File; path: string }[]): {
  roots: ImportNode[]
  jpgCount: number
  skipped: number
  looseFiles: File[] // jpgs sitting directly at the dropped root (no subfolder)
} {
  const root = newRaw('')
  let jpgCount = 0
  let skipped = 0

  for (const { file, path } of files) {
    const segments = path.split('/').filter(Boolean)
    if (segments.length === 0) continue
    // last segment is the filename
    const dirs = segments.slice(0, -1)
    if (!isJpeg(file)) {
      skipped += 1
      continue
    }
    jpgCount += 1
    let cur = root
    for (const d of dirs) {
      if (!cur.children.has(d)) cur.children.set(d, newRaw(d))
      cur = cur.children.get(d)!
    }
    cur.files.push(file)
  }

  // prune folders with no jpg anywhere
  function prune(node: RawNode): boolean {
    for (const [k, child] of [...node.children]) {
      if (!prune(child)) node.children.delete(k)
    }
    return node.files.length > 0 || node.children.size > 0
  }
  prune(root)

  // collapse single-child chains (no direct files + exactly one child):
  // absorb the redundant child's content but KEEP the outer meaningful name.
  function collapse(node: RawNode): RawNode {
    let files = node.files
    let children = node.children
    while (files.length === 0 && children.size === 1) {
      const only = [...children.values()][0]
      files = only.files
      children = only.children
    }
    const collapsedChildren = [...children.values()].map(collapse)
    return {
      name: node.name,
      files,
      children: new Map(collapsedChildren.map((c) => [c.name, c])),
    }
  }

  // Strip the outermost container: root has no name; its children are the
  // dropped top-level folder(s). If there is exactly one such folder, we treat
  // that folder's children as the top-level categories (strip the container).
  const topLevel = [...root.children.values()]
  let effectiveRoots: RawNode[]
  const looseRaw: File[] = []

  if (topLevel.length === 1) {
    const container = collapse(topLevel[0])
    // container's own files (jpgs directly under the dropped folder) are "loose"
    looseRaw.push(...container.files)
    effectiveRoots = [...container.children.values()]
  } else {
    // multiple top-level items dropped: keep each as a category
    effectiveRoots = topLevel.map((n) => collapse(n))
    // any files at the synthetic root (shouldn't happen normally)
    looseRaw.push(...root.files)
  }

  function toImport(node: RawNode): ImportNode {
    return {
      name: node.name,
      files: node.files,
      children: [...node.children.values()].map(toImport),
    }
  }

  return {
    roots: effectiveRoots.map(toImport),
    jpgCount,
    skipped,
    looseFiles: looseRaw,
  }
}

/** Count total jpg files in a node subtree (for preview). */
export function countFiles(node: ImportNode): number {
  return node.files.length + node.children.reduce((s, c) => s + countFiles(c), 0)
}

/** Flatten the plan into ordered upload tasks with their folder path (for nesting). */
export interface UploadTask {
  path: string[] // category name path, e.g. ["part_1"] or ["part_5", "sub"]
  files: File[]
}

export function flattenTasks(roots: ImportNode[]): UploadTask[] {
  const tasks: UploadTask[] = []
  function walk(node: ImportNode, prefix: string[]) {
    const here = [...prefix, node.name]
    if (node.files.length > 0) tasks.push({ path: here, files: node.files })
    else tasks.push({ path: here, files: [] }) // still create the (parent) category
    for (const c of node.children) walk(c, here)
  }
  for (const r of roots) walk(r, [])
  return tasks
}
