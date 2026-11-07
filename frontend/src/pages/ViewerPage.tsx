import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Save, Check, Clock } from 'lucide-react'
import { apiGetChapter, apiUpdateChapter, apiDeleteChapter, apiRetranslateChapter, chapterFilename, chapterViewPath } from '../services/api'
import { Button } from '../components/ui/Button'
import { ConfirmDialog } from '../components/modals/ConfirmDialog'
import { useAppStore } from '../stores/appStore'

type SaveState = 'idle' | 'saving' | 'saved'

function AutoSaveIndicator({ state, lastSaveTime }: { state: SaveState; lastSaveTime: number | null }) {
  if (state === 'saving') {
    return (
      <span className="flex items-center gap-1 text-sm text-slate-400">
        <Save size={14} className="animate-pulse" />
        <span>自动保存中…</span>
      </span>
    )
  }
  if (state === 'saved' && lastSaveTime) {
    const diff = Date.now() - lastSaveTime
    let label: string
    if (diff < 60000) label = '刚刚保存'
    else if (diff < 3600000) label = `${Math.floor(diff / 60000)}分钟前保存`
    else label = new Date(lastSaveTime).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    return (
      <span className="flex items-center gap-1 text-sm text-slate-400">
        <Check size={14} className="text-green-400" />
        <span>{label}</span>
      </span>
    )
  }
  return (
    <span className="flex items-center gap-1 text-sm text-slate-500">
      <Clock size={14} />
      <span>未保存</span>
    </span>
  )
}

export function ViewerPage() {
  const { work, chapter: chapterSlug } = useParams<{ work: string; chapter: string }>()
  const chapter = chapterSlug ? chapterFilename(chapterSlug) : undefined
  const navigate = useNavigate()
  const qc = useQueryClient()
  const activeJobs = useAppStore((s) => s.activeJobs)
  const addActiveJob = useAppStore((s) => s.addActiveJob)

  const { data, isLoading } = useQuery({
    queryKey: ['chapter', work, chapter],
    queryFn: () => apiGetChapter(work!, chapter!),
    enabled: !!work && !!chapter,
  })

  const [original, setOriginal] = useState('')
  const [translated, setTranslated] = useState('')
  const [newTitle, setNewTitle] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const [lastSaveTime, setLastSaveTime] = useState<number | null>(null)

  // Snapshot of the last persisted state, to skip no-op saves.
  const lastSavedRef = useRef<{ original: string; translated: string; newTitle: string }>({
    original: '', translated: '', newTitle: '',
  })
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  // Latest values for the async save closure to read.
  const stateRef = useRef({ original, translated, newTitle })
  stateRef.current = { original, translated, newTitle }
  // Mirror retranslating for the unmount effect (which has [] deps).
  const retranslatingRef = useRef(false)

  useEffect(() => {
    if (data) {
      setOriginal(data.original || '')
      setTranslated(data.translated || '')
      setNewTitle(chapter ? chapter.replace('.json', '') : '')
      const snap = {
        original: data.original || '',
        translated: data.translated || '',
        newTitle: chapter ? chapter.replace('.json', '') : '',
      }
      lastSavedRef.current = snap
      setSaveState('idle')
    }
  }, [data, chapter])

  // Is a retranslate job currently overwriting this chapter in place?
  const retranslating = work && chapter
    ? Object.values(activeJobs).some((j) => j.work === work && j.targetChapter === chapter)
    : false
  retranslatingRef.current = retranslating

  const performSave = useCallback(
    async (force = false) => {
      if (!work || !chapter) return
      const { original: o, translated: t, newTitle: nt } = stateRef.current
      if (!force &&
          o === lastSavedRef.current.original &&
          t === lastSavedRef.current.translated &&
          nt === lastSavedRef.current.newTitle) {
        return
      }
      setSaveState('saving')
      try {
        const res = await apiUpdateChapter(work, chapter, {
          original: o, translated: t, new_title: nt,
        })
        lastSavedRef.current = { original: o, translated: t, newTitle: nt }
        setLastSaveTime(Date.now())
        setSaveState('saved')
        qc.invalidateQueries({ queryKey: ['chapters', work] })
        if (res.filename !== chapter) {
          navigate(chapterViewPath(work, res.filename), { replace: true })
        }
      } catch {
        setSaveState('idle')
      }
    },
    [work, chapter, navigate, qc],
  )

  // Debounced auto-save on any edit. Skip while retranslating (the backend
  // job overwrites the file on done; auto-save must not race with it) and
  // never save when original is empty (would clobber real content with garbage).
  useEffect(() => {
    if (retranslating) return
    if (!original.trim() && !translated.trim()) return
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => { performSave() }, 1500)
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [original, translated, newTitle, retranslating, performSave])

  // Final save on unmount if dirty. Skip if retranslating (backend owns the
  // file) or if content is empty (would write garbage over real content).
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
      const { original: o, translated: t, newTitle: nt } = stateRef.current
      if ((!o.trim() && !t.trim()) || retranslatingRef.current) return
      if (
        o !== lastSavedRef.current.original ||
        t !== lastSavedRef.current.translated ||
        nt !== lastSavedRef.current.newTitle
      ) {
        // Fire-and-forget final save.
        performSave(true)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Ctrl/Cmd+S -> force immediate save.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        if (timerRef.current) clearTimeout(timerRef.current)
        performSave(true)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [performSave])

  const deleteMut = useMutation({
    mutationFn: () => apiDeleteChapter(work!, chapter!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['chapters', work] })
      navigate(`/work/${encodeURIComponent(work!)}/translate`)
    },
  })

  const retranslateMut = useMutation({
    mutationFn: () => apiRetranslateChapter(work!, chapter!),
    onSuccess: (jobId) => {
      const now = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
      addActiveJob(jobId, work!, now, original, chapter!)
      qc.invalidateQueries({ queryKey: ['chapter', work, chapter] })
    },
  })

  if (isLoading) return <p className="text-slate-400">Loading...</p>
  if (!data) return <p className="text-slate-400">Chapter not found.</p>

  const display = chapter ? chapter.replace('.json', '') : ''

  return (
    <div className="flex flex-col h-full">
      {/* Top: name + rename + autosave indicator */}
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-semibold text-slate-100">📄 {display}</h2>
        <AutoSaveIndicator state={saveState} lastSaveTime={lastSaveTime} />
      </div>
      <input
        className="mt-2 mb-4 w-full px-3 py-1.5 bg-slate-800 border border-slate-600 rounded-md text-slate-100"
        value={newTitle}
        onChange={(e) => setNewTitle(e.target.value)}
        placeholder="文件重命名"
      />

      <hr className="my-2 border-slate-700" />

      {/* Body: original + translated */}
      <div className="grid grid-cols-2 gap-4 flex-1 min-h-0">
        <div className="flex flex-col">
          <h5 className="text-sm font-medium mb-1 text-slate-300">原文</h5>
          <textarea
            className="flex-1 w-full p-3 bg-slate-800 border border-slate-600 rounded-md resize-none font-chinese text-slate-100"
            value={original}
            onChange={(e) => setOriginal(e.target.value)}
          />
        </div>
        <div className="flex flex-col">
          <h5 className="text-sm font-medium mb-1 text-slate-300">翻译</h5>
          {retranslating ? (
            <div className="flex-1 flex items-center justify-center p-3 border border-slate-600 rounded-md bg-slate-800 text-slate-400">
              <div className="flex flex-col items-center gap-3">
                <span className="inline-block w-6 h-6 border-2 border-slate-500 border-t-slate-300 rounded-full animate-spin" />
                <span>Retranslating…</span>
              </div>
            </div>
          ) : (
            <textarea
              className="flex-1 w-full p-3 bg-slate-800 border border-slate-600 rounded-md resize-none font-chinese text-slate-100"
              value={translated}
              onChange={(e) => setTranslated(e.target.value)}
            />
          )}
        </div>
      </div>

      <hr className="my-4 border-slate-700" />

      {/* Bottom: retranslate / delete (no manual Save button) */}
      <div className="grid grid-cols-2 gap-4">
        <Button variant="secondary" onClick={() => retranslateMut.mutate()} disabled={retranslateMut.isPending || retranslating}>
          Retranslate
        </Button>
        <Button variant="danger" onClick={() => setConfirmDelete(true)}>
          Delete File
        </Button>
      </div>
      {retranslateMut.isError && <p className="text-red-400 mt-2">Failed to start retranslate.</p>}

      <ConfirmDialog
        open={confirmDelete}
        title="Confirm delete chapter"
        onConfirm={() => deleteMut.mutate()}
        onCancel={() => setConfirmDelete(false)}
      >
        {`Are you sure you want to delete ${display}?`}
      </ConfirmDialog>
    </div>
  )
}
