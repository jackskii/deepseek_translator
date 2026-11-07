const key = (workId: string) => `reader:bookmark:${workId}`

export type Bookmark = { filename: string; title: string }

export function getBookmark(workId: string): Bookmark | null {
  try {
    const raw = localStorage.getItem(key(workId))
    if (!raw) return null
    const data = JSON.parse(raw) as Bookmark
    if (typeof data?.filename === 'string' && typeof data?.title === 'string') {
      return data
    }
  } catch {
    // ignore bad JSON
  }
  return null
}

export function setBookmark(workId: string, filename: string, title: string): void {
  localStorage.setItem(key(workId), JSON.stringify({ filename, title }))
}
