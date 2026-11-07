import { create } from 'zustand'

export type ActiveJob = {
  work: string
  createdAt: string
  inputText: string
  targetChapter?: string | null  // set when retranslating an existing chapter in place
}

export type AutoRun = {
  work: string
  source: string
  nextUrl: string
  lastUrl: string
  started: number
  limit: number | null
  status: 'running' | 'stopped' | 'done' | 'error'
  currentUrl: string
  message: string
}

type AppState = {
  selectedWork: string | null
  setSelectedWork: (w: string | null) => void
  // Background translation jobs: jobId -> { work, createdAt, inputText, targetChapter? }.
  activeJobs: Record<string, ActiveJob>
  addActiveJob: (jobId: string, work: string, createdAt: string, inputText: string, targetChapter?: string | null) => void
  removeActiveJob: (jobId: string) => void
  autoRun: AutoRun | null
  startAutoRun: (opts: { work: string; source: string; url: string; limit: number | null }) => void
  stopAutoRun: () => void
  patchAutoRun: (patch: Partial<AutoRun>) => void
}

export const useAppStore = create<AppState>((set) => ({
  selectedWork: null,
  setSelectedWork: (w) => set({ selectedWork: w }),
  activeJobs: {},
  addActiveJob: (jobId, work, createdAt, inputText, targetChapter = null) =>
    set((s) => ({ activeJobs: { ...s.activeJobs, [jobId]: { work, createdAt, inputText, targetChapter } } })),
  removeActiveJob: (jobId) =>
    set((s) => {
      const next = { ...s.activeJobs }
      delete next[jobId]
      return { activeJobs: next }
    }),
  autoRun: null,
  startAutoRun: ({ work, source, url, limit }) =>
    set({
      autoRun: {
        work,
        source,
        nextUrl: url,
        lastUrl: '',
        started: 0,
        limit,
        status: 'running',
        currentUrl: url,
        message: '',
      },
    }),
  stopAutoRun: () =>
    set((s) => {
      if (!s.autoRun || s.autoRun.status !== 'running') return s
      return {
        autoRun: { ...s.autoRun, status: 'stopped', message: '已停止' },
      }
    }),
  patchAutoRun: (patch) =>
    set((s) => (s.autoRun ? { autoRun: { ...s.autoRun, ...patch } } : s)),
}))
