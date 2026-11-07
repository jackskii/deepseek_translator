import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '../components/ui/Button'
import { apiStartTranslation } from '../services/api'
import { useAppStore } from '../stores/appStore'
import { useWorkName } from '../hooks/useWorkName'

export function TranslatorPage() {
  const { work } = useParams<{ work: string }>()
  const qc = useQueryClient()
  const addActiveJob = useAppStore((s) => s.addActiveJob)
  const activeJobs = useAppStore((s) => s.activeJobs)
  const [inputText, setInputText] = useState('')
  const [message, setMessage] = useState('')
  const workName = useWorkName(work)

  const runningCount = work
    ? Object.values(activeJobs).filter((j) => j.work === work).length
    : 0

  const translate = async () => {
    if (!work || !inputText.trim()) return
    setMessage('')
    const now = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
    try {
      const jobId = await apiStartTranslation(work, inputText)
      addActiveJob(jobId, work, now, inputText)
      qc.invalidateQueries({ queryKey: ['chapters', work] })
      setInputText('')  // clear immediately, ready for the next chapter
    } catch (e) {
      setMessage(`Failed to start: ${(e as Error).message}`)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <h1 className="text-2xl font-bold mb-1">📝 Create New Translation Task</h1>
      <p className="text-slate-400 mb-4">Current Work: {workName}</p>

      <label className="text-sm font-medium mb-1 text-slate-300">Input (Japanese)</label>
      <textarea
        className="flex-1 w-full p-3 bg-slate-800 border border-slate-600 rounded-md resize-none font-chinese text-slate-100 mb-4"
        placeholder="Paste Japanese text here, then click Create Task. The page clears so you can paste the next chapter right away."
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
      />

      <div className="flex items-center gap-3">
        <Button onClick={translate} disabled={!inputText.trim()}>Create Task</Button>
        {runningCount > 0 && (
          <span className="text-sm text-slate-400 flex items-center gap-1">
            <span className="inline-block w-3 h-3 border-2 border-slate-500 border-t-slate-300 rounded-full animate-spin" />
            {runningCount} task{runningCount > 1 ? 's' : ''} running
          </span>
        )}
        {message && <span className="text-red-400">{message}</span>}
      </div>
    </div>
  )
}
