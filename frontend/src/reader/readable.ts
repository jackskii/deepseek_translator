import type { ChapterEntry } from '../services/api'

function listed(entries: ChapterEntry[] | undefined): ChapterEntry[] {
  if (!entries) return []
  return entries.filter(
    (e) =>
      e.filename &&
      (e.status === 'done' || e.status === 'retranslating' || e.status === 'pending'),
  )
}

/** Oldest → newest by id. New translations land at the end. */
export function readableChapters(entries: ChapterEntry[] | undefined): ChapterEntry[] {
  return listed(entries).sort((a, b) => a.id.localeCompare(b.id))
}

export function translatedCount(entries: ChapterEntry[] | undefined): number {
  return readableChapters(entries).filter((e) => e.status !== 'pending').length
}

export function chapterTitle(filename: string): string {
  return filename.replace(/\.json$/i, '')
}
