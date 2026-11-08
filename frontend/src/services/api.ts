import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export type Work = {
  id: string
  name: string
  chapterCount: number
  wordCount: number
  lastRead: string
  lastTranslated: string
  added: string
  finished?: boolean
  lastDownload?: string
  lastDownloadFrom?: number
  lastDownloadTo?: number
  runningCount?: number
}

export function formatTimestamp(iso: string | undefined): string {
  if (!iso) return '—'
  const s = iso.replace('T', ' ')
  return s.length >= 19 ? s.slice(0, 19) : s
}

/** Most recent of lastRead / lastTranslated (ISO). Empty if neither. */
export function lastActivityISO(w: Work): string {
  const a = w.lastRead || ''
  const b = w.lastTranslated || ''
  return a >= b ? a : b
}

export function lastActivityLine(w: Work): string {
  const a = w.lastRead || ''
  const b = w.lastTranslated || ''
  if (!a && !b) return '上次阅读：—'
  if (a >= b) return `上次阅读：${formatTimestamp(a)}`
  return `上次翻译：${formatTimestamp(b)}`
}

export function lastDownloadLine(w: Work): string {
  if (!w.lastDownload) return '上次下载：—'
  const range =
    w.lastDownloadFrom && w.lastDownloadTo
      ? ` ${w.lastDownloadFrom}-${w.lastDownloadTo}`
      : ''
  return `上次下载：${formatTimestamp(w.lastDownload)}${range}`
}

export type Chapter = {
  original: string
  translated: string
}

export type ChapterEntry = {
  id: string
  filename: string | null
  status: 'pending' | 'done' | 'retranslating' | 'failed'
}

export type Terms = Record<string, string>

export type DeletedWork = {
  id: string
  name: string
  status: 'deleted'
  chapterCount: number
  deletedAt: string
}

export const apiGetWorksBundle = () =>
  api.get<{ works: Work[]; deleted?: DeletedWork[] }>('/works').then((r) => ({
    works: r.data.works,
    deleted: r.data.deleted ?? [],
  }))
export const apiGetWorks = () => apiGetWorksBundle().then((r) => r.works)
export const apiGetDeletedWorks = () => apiGetWorksBundle().then((r) => r.deleted)
export type WorkFromUrl = {
  id: string
  name: string
  source: string
  workUrl: string
  nextUrl: string
}
export const apiCreateWorkFromUrl = (source: string, url: string) =>
  api.post<WorkFromUrl>('/works/from-url', { source, url }).then((r) => r.data)
export const apiDeleteWork = (workId: string) => api.delete(`/works/${encodeURIComponent(workId)}`)
export const apiRestoreWork = (workId: string) =>
  api.post<{ id: string; name: string }>(`/works/${encodeURIComponent(workId)}/restore`).then((r) => r.data)
export const apiPurgeWork = (workId: string) =>
  api.post(`/works/${encodeURIComponent(workId)}/purge`)
export const apiTouchLastRead = (workId: string) =>
  api.post(`/works/${encodeURIComponent(workId)}/last-read`).then((r) => r.data)
export const apiSetFinished = (workId: string, finished: boolean) =>
  api.put(`/works/${encodeURIComponent(workId)}/finished`, { finished }).then((r) => r.data)

export type AutoProgress = {
  source: string
  lastUrl: string
  nextUrl: string
  workUrl?: string
  running?: boolean
  started?: number
  limit?: number | null
  currentUrl?: string
  message?: string
}

export const apiGetAutoProgress = (workId: string) =>
  api.get<AutoProgress>(`/works/${encodeURIComponent(workId)}/auto`).then(r => r.data)
export const apiStartAuto = (workId: string, count: number) =>
  api.post<AutoProgress>(`/works/${encodeURIComponent(workId)}/auto/start`, { count }).then((r) => r.data)
export const apiStopAuto = (workId: string) =>
  api.post<AutoProgress>(`/works/${encodeURIComponent(workId)}/auto/stop`).then((r) => r.data)

export const apiGetChapters = (workId: string) =>
  api.get<{ chapters: ChapterEntry[] }>(`/works/${encodeURIComponent(workId)}/chapters`).then(r => r.data.chapters)
export const apiGetChapter = (workId: string, chapter: string) =>
  api.get<Chapter>(`/works/${encodeURIComponent(workId)}/chapters/${encodeURIComponent(chapter)}`).then(r => r.data)
export const apiUpdateChapter = (workId: string, chapter: string, body: { original: string; translated: string; new_title?: string }) =>
  api.put<{ filename: string }>(`/works/${encodeURIComponent(workId)}/chapters/${encodeURIComponent(chapter)}`, body).then(r => r.data)
export const apiDeleteChapter = (workId: string, chapter: string) =>
  api.delete(`/works/${encodeURIComponent(workId)}/chapters/${encodeURIComponent(chapter)}`)

export const apiGetTerms = (workId: string) =>
  api.get<{ terms: Terms }>(`/works/${encodeURIComponent(workId)}/terms`).then(r => r.data.terms)
export const apiAddTerm = (workId: string, original: string, translation: string) =>
  api.post(`/works/${encodeURIComponent(workId)}/terms`, { original, translation })
export const apiUpdateTerm = (workId: string, original: string, translation: string, newOriginal?: string) =>
  api.put(`/works/${encodeURIComponent(workId)}/terms/${encodeURIComponent(original)}`, { translation, new_original: newOriginal })
export const apiDeleteTerm = (workId: string, original: string) =>
  api.delete(`/works/${encodeURIComponent(workId)}/terms/${encodeURIComponent(original)}`)

export const apiGetUniversalTerms = () =>
  api.get<{ terms: Terms }>('/universal-terms').then(r => r.data.terms)
export const apiAddUniversalTerm = (original: string, translation: string) =>
  api.post('/universal-terms', { original, translation })
export const apiUpdateUniversalTerm = (original: string, translation: string, newOriginal?: string) =>
  api.put(`/universal-terms/${encodeURIComponent(original)}`, { translation, new_original: newOriginal })
export const apiDeleteUniversalTerm = (original: string) =>
  api.delete(`/universal-terms/${encodeURIComponent(original)}`)

export type JobInfo = {
  id: string
  status: 'running' | 'done' | 'error' | 'cancelled'
  filename: string | null
  is_retranslate: boolean
  created_at: string
  input_text: string
  error: string | null
}

export const apiGetJobs = (workId: string) =>
  api.get<{ jobs: JobInfo[] }>(`/works/${encodeURIComponent(workId)}/translate/jobs`).then((r) => r.data.jobs)

export const apiRetranslateChapter = (workId: string, chapter: string) =>
  api.post<{ job_id: string }>(`/works/${encodeURIComponent(workId)}/chapters/${encodeURIComponent(chapter)}/retranslate`).then(r => r.data.job_id)

export function apiErrorMessage(e: unknown): string {
  if (typeof e === 'object' && e && 'response' in e) {
    const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
  }
  return e instanceof Error ? e.message : String(e)
}

/** Viewer URL slug: filename without a trailing .json (Vite 404s on reload if the path looks like a file). */
export function chapterSlug(filename: string): string {
  return filename.replace(/\.json$/i, '')
}

/** Turn a viewer slug (or a filename) back into the on-disk chapter filename. */
export function chapterFilename(slug: string): string {
  return slug.toLowerCase().endsWith('.json') ? slug : `${slug}.json`
}

export function chapterViewPath(workId: string, filename: string): string {
  return `/work/${encodeURIComponent(workId)}/chapters/${encodeURIComponent(chapterSlug(filename))}`
}
