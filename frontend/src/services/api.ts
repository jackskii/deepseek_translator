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
  runningCount?: number
}

export function workDateLabel(iso: string | undefined): string {
  if (!iso) return '—'
  return iso.slice(0, 10)
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

export const apiGetWorks = () => api.get<{ works: Work[] }>('/works').then(r => r.data.works)
export const apiCreateWork = (name: string) =>
  api.post<{ id: string; name: string }>('/works', { name }).then(r => r.data)
export const apiDeleteWork = (workId: string) => api.delete(`/works/${encodeURIComponent(workId)}`)
export const apiTouchLastRead = (workId: string) =>
  api.post(`/works/${encodeURIComponent(workId)}/last-read`).then((r) => r.data)

export type AutoProgress = { source: string; lastUrl: string; nextUrl: string }

export const apiGetAutoProgress = (workId: string) =>
  api.get<AutoProgress>(`/works/${encodeURIComponent(workId)}/auto`).then(r => r.data)
export const apiSaveAutoProgress = (workId: string, body: AutoProgress) =>
  api.put<AutoProgress>(`/works/${encodeURIComponent(workId)}/auto`, body).then(r => r.data)

export const apiGetChapters = (workId: string) =>
  api.get<{ chapters: ChapterEntry[] }>(`/works/${encodeURIComponent(workId)}/chapters`).then(r => r.data.chapters)
export const apiSaveChapter = (workId: string, original: string, translated: string, title?: string) =>
  api.post<{ filename: string }>(`/works/${encodeURIComponent(workId)}/chapters`, { original, translated, title }).then(r => r.data)
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

// --- Async translation jobs ---
export type JobStatus = {
  status: 'running' | 'done' | 'error' | 'cancelled'
  filename: string | null
  added_names: number
  error: string | null
  created_at: string
}

export const apiStartTranslation = (workId: string, inputText: string) =>
  api.post<{ job_id: string }>(`/works/${encodeURIComponent(workId)}/translate`, { input_text: inputText }).then(r => r.data.job_id)
export const apiCancelTranslation = (workId: string, jobId: string) =>
  api.post(`/works/${encodeURIComponent(workId)}/translate/jobs/${encodeURIComponent(jobId)}/cancel`)
export const apiGetJobStatus = (workId: string, jobId: string) =>
  api.get<JobStatus>(`/works/${encodeURIComponent(workId)}/translate/jobs/${encodeURIComponent(jobId)}`).then(r => r.data)

export const apiSetChapterOrder = (workId: string, ids: string[]) =>
  api.put(`/works/${encodeURIComponent(workId)}/chapters/order`, { order: ids })

export const apiRetranslateChapter = (workId: string, chapter: string) =>
  api.post<{ job_id: string }>(`/works/${encodeURIComponent(workId)}/chapters/${encodeURIComponent(chapter)}/retranslate`).then(r => r.data.job_id)

export type ScrapeResult = {
  empty: boolean
  title: string
  body: string
  next_url: string | null
}

export const apiScrape = (source: string, url: string) =>
  api.post<ScrapeResult>('/scrape', { source, url }).then(r => r.data)

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

export default api
