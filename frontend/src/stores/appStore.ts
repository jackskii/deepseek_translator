import { create } from 'zustand'

export type ActiveJob = {
  work: string
  createdAt: string
  inputText: string
  targetChapter?: string | null  // set when retranslating an existing chapter in place
}

type AppState = {
  selectedWork: string | null
  setSelectedWork: (w: string | null) => void
  // Background translation jobs: jobId -> { work, createdAt, inputText, targetChapter? }.
  activeJobs: Record<string, ActiveJob>
  addActiveJob: (jobId: string, work: string, createdAt: string, inputText: string, targetChapter?: string | null) => void
  removeActiveJob: (jobId: string) => void
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
}))
