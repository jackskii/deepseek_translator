import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  apiGetChapter,
  apiGetChapters,
  apiTouchLastRead,
  apiRetranslateChapter,
  apiUpdateChapter,
  apiDeleteChapter,
  chapterFilename,
  chapterViewPath,
} from '../services/api'
import { setBookmark } from '../reader/bookmark'
import { chapterTitle, readableChapters } from '../reader/readable'
import { useWorkSync } from '../hooks/useAutoTranslate'
import { isDesktop } from '../appMode'
import { ConfirmDialog } from '../components/modals/ConfirmDialog'

type SaveState = 'idle' | 'saving' | 'saved'

export function ChapterPage() {
  const { work, chapter: slug } = useParams<{ work: string; chapter: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const filename = slug ? chapterFilename(slug) : ''
  const entryIdRef = useRef<string | null>(null)
  const { jobs } = useWorkSync(work)
  const [confirmRetranslate, setConfirmRetranslate] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const [original, setOriginal] = useState('')
  const [translated, setTranslated] = useState('')
  const [newTitle, setNewTitle] = useState('')
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const lastSavedRef = useRef({ original: '', translated: '', newTitle: '' })
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const stateRef = useRef({ original, translated, newTitle })
  stateRef.current = { original, translated, newTitle }

  const { data: chapters } = useQuery({
    queryKey: ['chapters', work],
    queryFn: () => apiGetChapters(work!),
    enabled: !!work,
    refetchInterval: (q) => {
      const rows = q.state.data
      if (rows?.some((e) => e.status === 'pending' || e.status === 'retranslating')) return 2000
      return false
    },
  })
  const { data, isLoading } = useQuery({
    queryKey: ['chapter', work, filename],
    queryFn: () => apiGetChapter(work!, filename),
    enabled: !!work && !!filename,
  })

  const entry = chapters?.find((e) => e.filename === filename)
  if (entry?.id) entryIdRef.current = entry.id
  const pending = entry?.status === 'pending'
  const retranslating =
    entry?.status === 'retranslating' ||
    jobs.some((j) => j.status === 'running' && j.is_retranslate && j.filename === filename)

  useEffect(() => {
    if (!data) return
    setOriginal(data.original || '')
    setTranslated(data.translated || '')
    setNewTitle(filename ? chapterTitle(filename) : '')
    lastSavedRef.current = {
      original: data.original || '',
      translated: data.translated || '',
      newTitle: filename ? chapterTitle(filename) : '',
    }
    setSaveState('idle')
  }, [data, filename])

  const scrollRef = useRef<HTMLElement>(null)
  useEffect(() => {
    scrollRef.current?.scrollTo(0, 0)
  }, [filename])

  useEffect(() => {
    if (!work || !filename || !chapters) return
    if (chapters.some((e) => e.filename === filename)) return
    const id = entryIdRef.current
    if (!id) return
    const renamed = chapters.find((e) => e.id === id && e.filename)
    if (renamed?.filename) {
      navigate(chapterViewPath(work, renamed.filename), { replace: true })
    }
  }, [chapters, filename, work, navigate])

  useEffect(() => {
    if (!work || !filename) return
    if (entry?.status === 'pending') return
    setBookmark(work, filename, chapterTitle(filename))
    apiTouchLastRead(work).catch(() => {})
  }, [work, filename, entry?.status])

  const performSave = useCallback(
    async (force = false) => {
      if (!work || !filename || !isDesktop) return
      const { original: o, translated: t, newTitle: nt } = stateRef.current
      if (
        !force &&
        o === lastSavedRef.current.original &&
        t === lastSavedRef.current.translated &&
        nt === lastSavedRef.current.newTitle
      ) {
        return
      }
      setSaveState('saving')
      try {
        const res = await apiUpdateChapter(work, filename, {
          original: o,
          translated: t,
          new_title: nt,
        })
        lastSavedRef.current = { original: o, translated: t, newTitle: nt }
        setSaveState('saved')
        qc.invalidateQueries({ queryKey: ['chapters', work] })
        if (res.filename !== filename) {
          navigate(chapterViewPath(work, res.filename), { replace: true })
        }
      } catch {
        setSaveState('idle')
      }
    },
    [work, filename, navigate, qc],
  )

  useEffect(() => {
    if (!isDesktop || retranslating || pending) return
    if (!original.trim() && !translated.trim()) return
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      performSave()
    }, 1500)
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [original, translated, newTitle, retranslating, pending, performSave])

  const retranslateMut = useMutation({
    mutationFn: () => apiRetranslateChapter(work!, filename),
    onSuccess: () => {
      setConfirmRetranslate(false)
      qc.invalidateQueries({ queryKey: ['chapters', work] })
      qc.invalidateQueries({ queryKey: ['jobs', work] })
    },
  })
  const deleteMut = useMutation({
    mutationFn: () => apiDeleteChapter(work!, filename),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['chapters', work] })
      qc.invalidateQueries({ queryKey: ['works'] })
      setConfirmDelete(false)
      navigate(`/work/${encodeURIComponent(work!)}`)
    },
  })

  const list = readableChapters(chapters)
  const idx = list.findIndex((e) => e.filename === filename)
  const prev = idx > 0 ? list[idx - 1] : null
  const next = idx >= 0 && idx < list.length - 1 ? list[idx + 1] : null
  const title = filename ? chapterTitle(filename) : ''
  const displayTranslated = isDesktop ? translated : data?.translated || ''
  const canRetranslate = !!data?.original?.trim() && !pending && !retranslating

  return (
    <div className="h-full flex flex-col">
      <header
        className="sticky top-0 z-10 bg-slate-900/95 backdrop-blur border-b border-slate-700 px-3 py-3 flex items-center gap-3"
        style={{ paddingTop: 'max(0.75rem, env(safe-area-inset-top))' }}
      >
        <button
          className="shrink-0 px-2 py-2 text-slate-300 active:text-white"
          onClick={() => navigate(`/work/${encodeURIComponent(work!)}`)}
        >
          ← 目录
        </button>
        <h1 className="flex-1 min-w-0 truncate text-sm font-medium">{title}</h1>
        {isDesktop && saveState === 'saving' ? (
          <span className="text-xs text-slate-500">保存中…</span>
        ) : null}
        {isDesktop && saveState === 'saved' ? (
          <span className="text-xs text-slate-500">已保存</span>
        ) : null}
        {isDesktop && !pending ? (
          <button
            type="button"
            className="shrink-0 text-red-500 text-sm px-2"
            onClick={() => setConfirmDelete(true)}
          >
            删除
          </button>
        ) : null}
      </header>

      <main ref={scrollRef} className="flex-1 overflow-y-auto min-h-0">
        {isLoading ? (
          <p className="px-5 py-8 text-slate-400">加载中…</p>
        ) : !data ? (
          <p className="px-5 py-8 text-slate-400">找不到这一章。</p>
        ) : isDesktop ? (
          <div className="px-4 py-4 flex flex-col gap-3 h-full min-h-[24rem]">
            <input
              className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-md"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="文件重命名"
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 min-h-0">
              <div className="flex flex-col min-h-[12rem]">
                <p className="text-sm text-slate-400 mb-1">原文</p>
                <textarea
                  className="flex-1 w-full p-3 bg-slate-800 border border-slate-600 rounded-md resize-none font-chinese"
                  value={original}
                  onChange={(e) => setOriginal(e.target.value)}
                />
              </div>
              <div className="flex flex-col min-h-[12rem]">
                <p className="text-sm text-slate-400 mb-1">翻译</p>
                {retranslating || pending ? (
                  <div className="flex-1 flex items-center justify-center border border-slate-600 rounded-md text-slate-400">
                    翻译中…
                  </div>
                ) : (
                  <textarea
                    className="flex-1 w-full p-3 bg-slate-800 border border-slate-600 rounded-md resize-none font-chinese"
                    value={translated}
                    onChange={(e) => setTranslated(e.target.value)}
                  />
                )}
              </div>
            </div>
          </div>
        ) : displayTranslated ? (
          <article className="px-5 py-5 font-chinese text-[1.15rem] leading-[1.85] whitespace-pre-wrap">
            {displayTranslated}
          </article>
        ) : (
          <>
            <p className="px-5 pt-5 text-sm text-slate-400">
              {pending || retranslating ? '翻译中…' : '（没有译文）'}
            </p>
            <article className="px-5 py-5 font-chinese text-[1.15rem] leading-[1.85] whitespace-pre-wrap text-slate-300">
              {data.original || '（没有原文）'}
            </article>
          </>
        )}
      </main>

      <nav
        className="shrink-0 grid grid-cols-3 gap-2 px-3 py-3 border-t border-slate-700 bg-slate-900"
        style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}
      >
        <button
          className="py-3 rounded-md bg-slate-800 disabled:opacity-30 active:bg-slate-700"
          disabled={!prev}
          onClick={() => prev && navigate(chapterViewPath(work!, prev.filename!))}
        >
          上一章
        </button>
        <button
          className="py-3 rounded-md bg-slate-800 disabled:opacity-30 active:bg-slate-700"
          disabled={!canRetranslate || retranslateMut.isPending}
          onClick={() => setConfirmRetranslate(true)}
        >
          重译
        </button>
        <button
          className="py-3 rounded-md bg-slate-800 disabled:opacity-30 active:bg-slate-700"
          disabled={!next}
          onClick={() => next && navigate(chapterViewPath(work!, next.filename!))}
        >
          下一章
        </button>
      </nav>

      <ConfirmDialog
        open={confirmRetranslate}
        title="重新翻译"
        confirmLabel="重译"
        cancelLabel="取消"
        onConfirm={() => retranslateMut.mutate()}
        onCancel={() => setConfirmRetranslate(false)}
      >
        将重新翻译这一章，原文保留。确定吗？
      </ConfirmDialog>
      <ConfirmDialog
        open={confirmDelete}
        title="删除章节"
        confirmLabel="删除"
        cancelLabel="取消"
        onConfirm={() => deleteMut.mutate()}
        onCancel={() => setConfirmDelete(false)}
      >
        {`将从磁盘删除「${title}」。无法恢复。`}
      </ConfirmDialog>
    </div>
  )
}
