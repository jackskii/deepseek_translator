import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export type Work = { id: string; name: string }

export type Chapter = {
  original: string
  translated: string
}

export type ChapterEntry = {
  id: string
  filename: string | null
  status: 'pending' | 'done' | 'retranslating'
}

export type Terms = Record<string, string>

export const apiGetWorks = () => api.get<{ works: Work[] }>('/works').then(r => r.data.works)
export const apiCreateWork = (name: string) =>
  api.post<{ id: string; name: string }>('/works', { name }).then(r => r.data)
export const apiDeleteWork = (workId: string) => api.delete(`/works/${encodeURIComponent(workId)}`)

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

export default api
