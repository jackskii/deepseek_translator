import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  apiGetTerms,
  apiAddTerm,
  apiUpdateTerm,
  apiDeleteTerm,
  apiGetUniversalTerms,
  apiAddUniversalTerm,
  apiUpdateUniversalTerm,
  apiDeleteUniversalTerm,
} from '../services/api'
import { Button } from '../components/ui/Button'
import { useWorkName } from '../hooks/useWorkName'

type Tab = 'work' | 'universal'

export function TermsPage() {
  const { work } = useParams<{ work: string }>()
  const workName = useWorkName(work)
  const [tab, setTab] = useState<Tab>('work')

  if (!work) return null

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-100">📚 Macro - {workName}</h2>

      <div className="flex gap-1 mt-4 mb-4 border-b border-slate-700">
        <button
          className={`px-4 py-2 text-sm ${tab === 'work' ? 'text-blue-300 border-b-2 border-blue-400' : 'text-slate-400'}`}
          onClick={() => setTab('work')}
        >
          Work terms
        </button>
        <button
          className={`px-4 py-2 text-sm ${tab === 'universal' ? 'text-blue-300 border-b-2 border-blue-400' : 'text-slate-400'}`}
          onClick={() => setTab('universal')}
        >
          Universal terms
        </button>
      </div>

      {tab === 'work' ? <WorkTerms work={work} /> : <UniversalTerms />}
    </div>
  )
}

function WorkTerms({ work }: { work: string }) {
  const qc = useQueryClient()
  const { data: terms } = useQuery({
    queryKey: ['terms', work],
    queryFn: () => apiGetTerms(work),
  })
  const [newOriginal, setNewOriginal] = useState('')
  const [newTranslation, setNewTranslation] = useState('')
  const addMut = useMutation({
    mutationFn: () => apiAddTerm(work, newOriginal, newTranslation),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['terms', work] })
      setNewOriginal('')
      setNewTranslation('')
    },
  })
  const entries = terms ? Object.entries(terms) : []

  return (
    <>
      <p className="text-sm text-slate-400 mb-4">
        新名词会在翻译时自动添加到此处；你在这里的手动修改是最终版本，模型之后不会覆盖已有条目。
      </p>
      <TermEditor
        newOriginal={newOriginal}
        newTranslation={newTranslation}
        setNewOriginal={setNewOriginal}
        setNewTranslation={setNewTranslation}
        onAdd={() => addMut.mutate()}
        adding={addMut.isPending}
        entries={entries}
        emptyText="No terms defined yet. Add some terms above."
        onSave={(original, editedOriginal, editedTranslation) =>
          apiUpdateTerm(work, original, editedTranslation, editedOriginal !== original ? editedOriginal : undefined)
        }
        onDelete={(original) => apiDeleteTerm(work, original)}
        onSaved={() => qc.invalidateQueries({ queryKey: ['terms', work] })}
      />
    </>
  )
}

function UniversalTerms() {
  const qc = useQueryClient()
  const { data: terms } = useQuery({
    queryKey: ['universal-terms'],
    queryFn: apiGetUniversalTerms,
  })
  const [newOriginal, setNewOriginal] = useState('')
  const [newTranslation, setNewTranslation] = useState('')
  const addMut = useMutation({
    mutationFn: () => apiAddUniversalTerm(newOriginal, newTranslation),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['universal-terms'] })
      setNewOriginal('')
      setNewTranslation('')
    },
  })
  const entries = terms ? Object.entries(terms) : []

  return (
    <>
      <p className="text-sm text-slate-400 mb-4">
        适用于全部作品。只手动添加。出现在正文里时，会和作品名词一起传给模型，不单独标注。
      </p>
      <TermEditor
        newOriginal={newOriginal}
        newTranslation={newTranslation}
        setNewOriginal={setNewOriginal}
        setNewTranslation={setNewTranslation}
        onAdd={() => addMut.mutate()}
        adding={addMut.isPending}
        entries={entries}
        emptyText="No universal terms yet. Add some terms above."
        onSave={(original, editedOriginal, editedTranslation) =>
          apiUpdateUniversalTerm(original, editedTranslation, editedOriginal !== original ? editedOriginal : undefined)
        }
        onDelete={(original) => apiDeleteUniversalTerm(original)}
        onSaved={() => qc.invalidateQueries({ queryKey: ['universal-terms'] })}
      />
    </>
  )
}

function TermEditor({
  newOriginal,
  newTranslation,
  setNewOriginal,
  setNewTranslation,
  onAdd,
  adding,
  entries,
  emptyText,
  onSave,
  onDelete,
  onSaved,
}: {
  newOriginal: string
  newTranslation: string
  setNewOriginal: (v: string) => void
  setNewTranslation: (v: string) => void
  onAdd: () => void
  adding: boolean
  entries: [string, string][]
  emptyText: string
  onSave: (original: string, editedOriginal: string, editedTranslation: string) => Promise<unknown>
  onDelete: (original: string) => Promise<unknown>
  onSaved: () => void
}) {
  return (
    <>
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
          onClick={() => newOriginal.trim() && newTranslation.trim() && onAdd()}
          disabled={!newOriginal.trim() || !newTranslation.trim() || adding}
        >
          Add
        </Button>
      </div>

      <hr className="my-4 border-slate-700" />

      <h3 className="text-lg font-medium mb-3 text-slate-200">Current Terms</h3>
      {entries.length === 0 ? (
        <p className="text-slate-400">{emptyText}</p>
      ) : (
        <div className="flex flex-col gap-3">
          {entries.map(([original, translation]) => (
            <TermRow
              key={original}
              original={original}
              translation={translation}
              onSave={onSave}
              onDelete={onDelete}
              onSaved={onSaved}
            />
          ))}
        </div>
      )}
    </>
  )
}

function TermRow({
  original,
  translation,
  onSave,
  onDelete,
  onSaved,
}: {
  original: string
  translation: string
  onSave: (original: string, editedOriginal: string, editedTranslation: string) => Promise<unknown>
  onDelete: (original: string) => Promise<unknown>
  onSaved: () => void
}) {
  const [editedOriginal, setEditedOriginal] = useState(original)
  const [editedTranslation, setEditedTranslation] = useState(translation)

  const saveMut = useMutation({
    mutationFn: () => onSave(original, editedOriginal, editedTranslation),
    onSuccess: onSaved,
  })
  const deleteMut = useMutation({
    mutationFn: () => onDelete(original),
    onSuccess: onSaved,
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
