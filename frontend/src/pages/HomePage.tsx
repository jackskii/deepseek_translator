import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { apiGetWorks, apiCreateWork, apiDeleteWork, workDateLabel } from '../services/api'
import { Button } from '../components/ui/Button'
import { ConfirmDialog } from '../components/modals/ConfirmDialog'
import { WorkSortButtons, loadWorkSort, saveWorkSort, sortWorks } from '../components/WorkSort'
import { useAppStore } from '../stores/appStore'

export function HomePage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [newName, setNewName] = useState('')
  const [pendingDelete, setPendingDelete] = useState<string | null>(null)
  const [sort, setSort] = useState(loadWorkSort)
  const activeJobs = useAppStore((s) => s.activeJobs)

  const { data: works, isLoading } = useQuery({
    queryKey: ['works'],
    queryFn: apiGetWorks,
  })

  const createMut = useMutation({
    mutationFn: (name: string) => apiCreateWork(name),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['works'] })
      if (res?.id) {
        navigate(`/work/${encodeURIComponent(res.id)}/translate`)
      }
    },
  })

  const deleteMut = useMutation({
    mutationFn: (workId: string) => apiDeleteWork(workId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['works'] })
      setPendingDelete(null)
    },
  })

  const trimmed = newName.trim()
  const taken = !!(trimmed && works?.some((w) => w.name === trimmed))
  const existsFromApi =
    createMut.isError && axios.isAxiosError(createMut.error) && createMut.error.response?.status === 409
  const showExists = taken || existsFromApi

  function submit() {
    if (!trimmed || taken) return
    createMut.mutate(trimmed)
  }

  const listed = works ? sortWorks(works, sort) : []

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">DeepSeek Translator</h1>
      <p className="text-slate-400 mb-6">一个简单的日语小说翻译工具</p>

      <h2 className="text-lg font-semibold mb-2">Add New Work</h2>
      <div className="flex gap-2">
        <input
          className="flex-1 px-3 py-2 bg-slate-800 border border-slate-600 rounded-md text-slate-100 placeholder-slate-500"
          placeholder="Enter work name here..."
          value={newName}
          onChange={(e) => {
            setNewName(e.target.value)
            createMut.reset()
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') submit()
          }}
        />
        <Button
          onClick={submit}
          disabled={!trimmed || taken || createMut.isPending}
        >
          Create Work
        </Button>
      </div>
      {showExists ? (
        <p className="text-sm text-red-400 mt-2 mb-6">already exists</p>
      ) : (
        <div className="mb-8" />
      )}

      <div className="flex items-center justify-between gap-3 mb-3">
        <h2 className="text-lg font-semibold">Works</h2>
        <WorkSortButtons
          value={sort}
          onChange={(v) => {
            setSort(v)
            saveWorkSort(v)
          }}
        />
      </div>
      {isLoading ? (
        <p className="text-slate-400">Loading...</p>
      ) : listed.length === 0 ? (
        <p className="text-slate-400">No works found. Create your first work above!</p>
      ) : (
        <div className="grid grid-cols-2 gap-4 items-stretch">
          {listed.map((w) => {
            const live = Object.values(activeJobs).filter((j) => j.work === w.id).length
            const running = Math.max(w.runningCount ?? 0, live)
            return (
              <div
                key={w.id}
                className="h-full border border-slate-700 rounded-lg p-4 flex flex-col bg-slate-800 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start gap-2">
                  <button
                    className="flex-1 min-w-0 text-left font-medium text-slate-100 leading-snug"
                    onClick={() => navigate(`/work/${encodeURIComponent(w.id)}/translate`)}
                  >
                    {w.name}
                  </button>
                  <button
                    className="shrink-0 text-red-500 hover:text-red-400 text-lg leading-none"
                    title={`Delete work '${w.name}'`}
                    onClick={() => setPendingDelete(w.id)}
                  >
                    🗑
                  </button>
                </div>
                <p className="mt-3 text-sm text-slate-400">
                  {w.chapterCount ?? 0} 章 · {(w.wordCount ?? 0).toLocaleString('zh-CN')} 字
                </p>
                <p className="mt-1 text-sm text-slate-500">
                  {running > 0 ? `翻译中 ${running} · ` : ''}
                  上次阅读 {workDateLabel(w.lastRead)} · 上次翻译 {workDateLabel(w.lastTranslated)}
                </p>
              </div>
            )
          })}
        </div>
      )}

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Confirm delete work"
        onConfirm={() => pendingDelete && deleteMut.mutate(pendingDelete)}
        onCancel={() => setPendingDelete(null)}
      >
        {`Are you sure you want to delete this work?\nThis will permanently delete the work and all its chapters and terms.`}
      </ConfirmDialog>
    </div>
  )
}
