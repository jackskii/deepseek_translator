import type { ChapterEntry } from '../services/api'

export function readableChapters(entries: ChapterEntry[] | undefined): ChapterEntry[] {
  if (!entries) return []
  // Translator stores newest-first; reader wants story order (oldest first).
  return entries
    .filter((e) => e.filename && (e.status === 'done' || e.status === 'retranslating'))
    .reverse()
}

export function chapterTitle(filename: string): string {
  return filename.replace(/\.json$/i, '')
}
