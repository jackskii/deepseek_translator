import { useParams } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'

export function TranslatingPage() {
  const { work, jobId } = useParams<{ work: string; jobId: string }>()
  const job = useAppStore((s) => (jobId ? s.activeJobs[jobId] : undefined))

  if (!work || !jobId) {
    return <div className="p-4 text-slate-400">No active task.</div>
  }
  if (!job) {
    // Job already finished and was removed from the store - the real chapter
    // should now be in the list.
    return <div className="p-4 text-slate-400">This task has finished.</div>
  }

  return (
    <div className="flex flex-col h-full">
      <h1 className="text-2xl font-bold mb-1">📝 Translating…</h1>
      <p className="text-slate-400 mb-4">
        Task {job.createdAt} is translating in the background. This page will
        update when it finishes.
      </p>

      <div className="grid grid-cols-2 gap-4 flex-1 min-h-0">
        {/* Left: original text */}
        <div className="flex flex-col min-h-0">
          <label className="text-sm font-medium mb-1 text-slate-300">Original (Japanese)</label>
          <div className="flex-1 overflow-y-auto p-3 bg-slate-800 border border-slate-600 rounded-md whitespace-pre-wrap font-chinese text-slate-100">
            {job.inputText}
          </div>
        </div>

        {/* Right: translating indicator */}
        <div className="flex flex-col min-h-0">
          <label className="text-sm font-medium mb-1 text-slate-300">Translation (Chinese)</label>
          <div className="flex-1 flex items-center justify-center p-3 border border-slate-600 rounded-md bg-slate-800 text-slate-400">
            <div className="flex flex-col items-center gap-3">
              <span className="inline-block w-6 h-6 border-2 border-slate-500 border-t-slate-300 rounded-full animate-spin" />
              <span>Translating…</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
