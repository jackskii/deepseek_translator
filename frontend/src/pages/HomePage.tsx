import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiGetWorks, apiCreateWork, apiDeleteWork } from '../services/api'
import { Button } from '../components/ui/Button'
import { ConfirmDialog } from '../components/modals/ConfirmDialog'

export function HomePage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [newName, setNewName] = useState('')
  const [pendingDelete, setPendingDelete] = useState<string | null>(null)

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

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">DeepSeek Translator</h1>
      <p className="text-slate-400 mb-6">一个简单的日语小说翻译工具</p>

      {/* Add Work */}
      <h2 className="text-lg font-semibold mb-2">Add New Work</h2>
      <div className="flex gap-2 mb-8">
        <input
          className="flex-1 px-3 py-2 bg-slate-800 border border-slate-600 rounded-md text-slate-100 placeholder-slate-500"
          placeholder="Enter work name here..."
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && newName.trim()) createMut.mutate(newName.trim())
          }}
        />
        <Button
          onClick={() => newName.trim() && createMut.mutate(newName.trim())}
          disabled={!newName.trim() || createMut.isPending}
        >
          Create Work
        </Button>
      </div>

      <h2 className="text-lg font-semibold mb-3">Works</h2>
      {isLoading ? (
        <p className="text-slate-400">Loading...</p>
      ) : !works || works.length === 0 ? (
        <p className="text-slate-400">No works found. Create your first work above!</p>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {works.map((w) => (
            <div
              key={w.id}
              className="border border-slate-700 rounded-lg p-4 flex items-center justify-between hover:shadow-md transition-shadow bg-slate-800"
            >
              <button
                className="flex-1 text-left truncate font-medium text-slate-100"
                onClick={() => navigate(`/work/${encodeURIComponent(w.id)}/translate`)}
              >
                📁 {w.name}
              </button>
              <button
                className="ml-3 text-red-500 hover:text-red-400 text-lg"
                title={`Delete work '${w.name}'`}
                onClick={() => setPendingDelete(w.id)}
              >
                🗑
              </button>
            </div>
          ))}
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
