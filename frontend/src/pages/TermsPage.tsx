import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiGetTerms, apiAddTerm, apiUpdateTerm, apiDeleteTerm } from '../services/api'
import { Button } from '../components/ui/Button'
import { useWorkName } from '../hooks/useWorkName'

export function TermsPage() {
  const { work } = useParams<{ work: string }>()
  const qc = useQueryClient()
  const workName = useWorkName(work)

  const { data: terms } = useQuery({
    queryKey: ['terms', work],
    queryFn: () => apiGetTerms(work!),
    enabled: !!work,
  })

  const [newOriginal, setNewOriginal] = useState('')
  const [newTranslation, setNewTranslation] = useState('')

  const addMut = useMutation({
    mutationFn: () => apiAddTerm(work!, newOriginal, newTranslation),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['terms', work] })
      setNewOriginal('')
      setNewTranslation('')
    },
  })

  if (!work) return null

  const entries = terms ? Object.entries(terms) : []

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-100">📚 Macro - {workName}</h2>
      <p className="text-sm text-slate-400 mt-1 mb-4">
        新名词会在翻译时自动添加到此处；你在这里的手动修改是最终版本，模型之后不会覆盖已有条目。
      </p>

      {/* Add new term */}
      <h3 className="text-lg font-medium mb-2 text-slate-200">Add New Term</h3>
      <div className="grid grid-cols-[2fr_2fr_1fr] gap-2 items-end mb-6">
        <div>
          <label className="text-sm font-medium text-slate-300">Original Term (Japanese)</label>
          <input
            className="w-full px-3 py-1.5 bg-slate-800 border border-slate-600 rounded-md text-slate-100"
            value={newOriginal}
            onChange={(e) => setNewOriginal(e.target.value)}
          />
        </div>
        <div>
          <label className="text-sm font-medium text-slate-300">Translation (Chinese)</label>
          <input
            className="w-full px-3 py-1.5 bg-slate-800 border border-slate-600 rounded-md text-slate-100"
            value={newTranslation}
            onChange={(e) => setNewTranslation(e.target.value)}
          />
        </div>
        <Button
          onClick={() => newOriginal.trim() && newTranslation.trim() && addMut.mutate()}
          disabled={!newOriginal.trim() || !newTranslation.trim() || addMut.isPending}
        >
          Add
        </Button>
      </div>

      <hr className="my-4 border-slate-700" />

      {/* Current terms */}
      <h3 className="text-lg font-medium mb-3 text-slate-200">Current Terms</h3>
      {!terms || entries.length === 0 ? (
        <p className="text-slate-400">No terms defined yet. Add some terms above.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {entries.map(([original, translation]) => (
            <TermRow key={original} work={work} original={original} translation={translation} />
          ))}
        </div>
      )}
    </div>
  )
}

function TermRow({ work, original, translation }: { work: string; original: string; translation: string }) {
  const qc = useQueryClient()
  const [editedOriginal, setEditedOriginal] = useState(original)
  const [editedTranslation, setEditedTranslation] = useState(translation)

  const saveMut = useMutation({
    mutationFn: () =>
      apiUpdateTerm(
        work,
        original,
        editedTranslation,
        editedOriginal !== original ? editedOriginal : undefined,
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['terms', work] }),
  })

  const deleteMut = useMutation({
    mutationFn: () => apiDeleteTerm(work, original),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['terms', work] }),
  })

  return (
    <div className="grid grid-cols-[2fr_2fr_1fr_1fr] gap-2 items-end">
      <div>
        <label className="text-xs text-slate-400">Original</label>
        <input
          className="w-full px-3 py-1.5 bg-slate-800 border border-slate-600 rounded-md text-slate-100"
          value={editedOriginal}
          onChange={(e) => setEditedOriginal(e.target.value)}
        />
      </div>
      <div>
        <label className="text-xs text-slate-400">Translation</label>
        <input
          className="w-full px-3 py-1.5 bg-slate-800 border border-slate-600 rounded-md text-slate-100"
          value={editedTranslation}
          onChange={(e) => setEditedTranslation(e.target.value)}
        />
      </div>
      <Button
        variant="primary"
        onClick={() => saveMut.mutate()}
        disabled={saveMut.isPending || (!editedOriginal.trim() && !editedTranslation.trim())}
      >
        Save
      </Button>
      <Button variant="secondary" onClick={() => deleteMut.mutate()} disabled={deleteMut.isPending}>
        Delete
      </Button>
    </div>
  )
}
