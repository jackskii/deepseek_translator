import { Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { HomePage } from './pages/HomePage'
import { TranslatorPage } from './pages/TranslatorPage'
import { AutoTranslatePage } from './pages/AutoTranslatePage'
import { ViewerPage } from './pages/ViewerPage'
import { TermsPage } from './pages/TermsPage'
import { TranslatingPage } from './pages/TranslatingPage'
import { useAppStore } from './stores/appStore'
import {
  apiGetWorks,
  apiGetChapters,
  apiGetJobStatus,
  apiSetChapterOrder,
  apiStartTranslation,
  apiScrape,
  apiErrorMessage,
  chapterViewPath,
  type ChapterEntry,
} from './services/api'

export default function App() {
  const navigate = useNavigate()
  const location = useLocation()
  const qc = useQueryClient()
  const setSelectedWork = useAppStore((s) => s.setSelectedWork)
  const activeJobs = useAppStore((s) => s.activeJobs)
  const removeActiveJob = useAppStore((s) => s.removeActiveJob)
  const autoRun = useAppStore((s) => s.autoRun)
  const [collapsed, setCollapsed] = useState(false)

  // Keep selectedWork in sync with the URL's :work param.
  useEffect(() => {
    const m = location.pathname.match(/^\/work\/([^/]+)/)
    if (m) setSelectedWork(decodeURIComponent(m[1]))
    else setSelectedWork(null)
  }, [location.pathname, setSelectedWork])

  // Global background-job watcher: poll active jobs every 2s. When a job
  // finishes (done/error), invalidate that work's chapter + term queries so
  // the sidebar chapter list refreshes, and remove the job from the store.
  // This lets a translation finish and auto-appear even after the user has
  // navigated away from the TranslatorPage.
  useEffect(() => {
    const jobIds = Object.keys(activeJobs)
    if (jobIds.length === 0) return
    let cancelled = false
    const poll = async () => {
      for (const jobId of Object.keys(activeJobs)) {
        const info = activeJobs[jobId]
        const workName = info.work
        try {
          const st = await apiGetJobStatus(workName, jobId)
          if (st.status === 'done' || st.status === 'error' || st.status === 'cancelled') {
            qc.invalidateQueries({ queryKey: ['chapters', workName] })
            qc.invalidateQueries({ queryKey: ['terms', workName] })
            // For retranslate jobs, also refresh the in-place chapter content.
            if (info.targetChapter) {
              qc.invalidateQueries({ queryKey: ['chapter', workName, info.targetChapter] })
            }
            removeActiveJob(jobId)
          }
        } catch {
          // ignore transient errors; will retry next tick
        }
      }
      if (!cancelled) setTimeout(poll, 2000)
    }
    poll()
    return () => { cancelled = true }
  }, [activeJobs, qc, removeActiveJob])

  // Auto-scrape loop. Lives here (not on the Auto page) so navigating away
  // does not abort a long run. Stop flips autoRun.status; this effect then exits.
  useEffect(() => {
    if (autoRun?.status !== 'running') return
    let cancelled = false
    const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms))
    const stillRunning = () => {
      const run = useAppStore.getState().autoRun
      return !cancelled && run?.status === 'running'
    }

    ;(async () => {
      while (stillRunning()) {
        const run = useAppStore.getState().autoRun
        if (!run || run.status !== 'running') break
        const url = run.nextUrl
        useAppStore.getState().patchAutoRun({ currentUrl: url })
        try {
          const scraped = await apiScrape(run.source, url)
          if (!stillRunning()) break
          if (scraped.empty) {
            useAppStore.getState().patchAutoRun({
              status: 'done',
              message: '已结束（空页）',
            })
            break
          }
          const text = `${scraped.title}\n\n${scraped.body}`.trim()
          const jobId = await apiStartTranslation(run.work, text)
          if (!stillRunning()) break
          const now = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
          useAppStore.getState().addActiveJob(jobId, run.work, now, text)
          qc.invalidateQueries({ queryKey: ['chapters', run.work] })
          const started = (useAppStore.getState().autoRun?.started ?? 0) + 1
          const limit = useAppStore.getState().autoRun?.limit ?? null
          const hitLimit = limit != null && started >= limit
          useAppStore.getState().patchAutoRun({
            started,
            lastUrl: url,
            nextUrl: scraped.next_url ?? '',
            ...(hitLimit
              ? { status: 'done' as const, message: `已结束（${started} 章）` }
              : {}),
          })
          if (hitLimit || !scraped.next_url) {
            if (!hitLimit) {
              useAppStore.getState().patchAutoRun({
                status: 'done',
                message: '已结束（空页）',
              })
            }
            break
          }
          await sleep(2000)
        } catch (e) {
          if (!stillRunning()) break
          useAppStore.getState().patchAutoRun({
            status: 'error',
            message: apiErrorMessage(e),
          })
          break
        }
      }
    })()

    return () => { cancelled = true }
  }, [autoRun?.status, qc])

  const onHome = location.pathname === '/'

  return (
    <div className="h-full overflow-hidden flex bg-slate-900 text-slate-200">
      {/* Sidebar */}
      <aside
        className={`${collapsed ? 'w-14' : 'w-64'} shrink-0 border-r border-slate-700 bg-slate-800 flex flex-col transition-all duration-200 overflow-hidden`}
      >
        <div className="p-2 flex items-center justify-between border-b border-slate-700">
          {!collapsed && <span className="text-sm font-semibold text-slate-300 px-2">Menu</span>}
          <button
            className="p-1.5 rounded hover:bg-slate-700 text-slate-400"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            onClick={() => setCollapsed((c) => !c)}
          >
            {collapsed ? '▶' : '◀'}
          </button>
        </div>
        <div className="flex-1 min-h-0 overflow-hidden p-2 flex flex-col">
          {onHome ? (
            <IntroGuide collapsed={collapsed} />
          ) : (
            <Routes>
              <Route path="/work/:work/*" element={<WorkSidebar collapsed={collapsed} />} />
            </Routes>
          )}
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-h-0 p-6 overflow-auto">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/work/:work/translate" element={<TranslatorPage />} />
          <Route path="/work/:work/auto" element={<AutoTranslatePage />} />
          <Route path="/work/:work/translating/:jobId" element={<TranslatingPage />} />
          <Route path="/work/:work/chapters/:chapter" element={<ViewerPage />} />
          <Route path="/work/:work/terms" element={<TermsPage />} />
        </Routes>
      </main>
    </div>
  )
}

function IntroGuide({ collapsed }: { collapsed: boolean }) {
  if (collapsed) return null
  return (
    <div className="px-2 py-2 text-sm text-slate-300 flex flex-col gap-3">
      <div className="font-semibold text-base flex items-center gap-2">
        <img src="/favicon.svg" alt="" className="w-5 h-5" />
        DeepSeek Translator
      </div>
      <div className="text-xs text-slate-400">一个简单的日语小说翻译工具</div>
      <hr className="border-slate-700" />
      <div className="font-medium">快速上手</div>
      <ol className="list-decimal list-inside text-xs text-slate-400 flex flex-col gap-1">
        <li>在右侧输入作品名，点击 Create Work。</li>
        <li>进入「Create New Task」页面，粘贴日文原文。</li>
        <li>点击 Create Task 创建翻译任务，页面会清空，可继续粘贴下一章。</li>
        <li>翻译在后台进行，完成后自动出现在左侧章节列表；可拖拽调整顺序。</li>
      </ol>
      <hr className="border-slate-700" />
      <div className="font-medium">名词表</div>
      <div className="text-xs text-slate-400">
        翻译时模型会自动识别新专有名词并添加到名词表。你可以在 Manage Terms 里手动编辑，手动修改不会被覆盖。
      </div>
      <hr className="border-slate-700" />
      <div className="font-medium">切换提供商</div>
      <div className="text-xs text-slate-400">
        在 .env 里设置 LLM_PROVIDER 为 deepseek 或 openrouter，并填入对应的 API Key 和模型名。
      </div>
    </div>
  )
}

function WorkSidebar({ collapsed }: { collapsed: boolean }) {
  const navigate = useNavigate()
  const location = useLocation()
  const work = useAppStore((s) => s.selectedWork)
  const { data: works } = useQuery({
    queryKey: ['works'],
    queryFn: apiGetWorks,
  })
  if (!work) return null

  // `work` is now a work_id; look up the display name from the works list.
  const workName = works?.find((w) => w.id === work)?.name ?? work

  const translatePath = `/work/${encodeURIComponent(work)}/translate`
  const autoPath = `/work/${encodeURIComponent(work)}/auto`
  const termsPath = `/work/${encodeURIComponent(work)}/terms`

  // An item is "active" only when the current pathname exactly matches its
  // target path. Chapter viewer paths look like /work/:work/chapters/:name
  // and won't match either of these, so no sidebar item is highlighted there.
  const isActive = (path: string) => location.pathname === path

  const activeClass = 'bg-blue-900 text-blue-300'
  const idleClass = 'text-slate-200'

  if (collapsed) {
    return (
      <div className="flex flex-col gap-2 items-center">
        <button
          className="text-xl p-1.5 rounded hover:bg-slate-700"
          title="Back to Works"
          onClick={() => navigate('/')}
        >
          🏠
        </button>
        <button
          className={`text-xl p-1.5 rounded hover:bg-slate-700 ${isActive(translatePath) ? 'bg-slate-700' : ''}`}
          title="Create New Task"
          onClick={() => navigate(translatePath)}
        >
          📝
        </button>
        <button
          className={`text-xl p-1.5 rounded hover:bg-slate-700 ${isActive(autoPath) ? 'bg-slate-700' : ''}`}
          title="Auto Translate"
          onClick={() => navigate(autoPath)}
        >
          ⚡
        </button>
        <button
          className={`text-xl p-1.5 rounded hover:bg-slate-700 ${isActive(termsPath) ? 'bg-slate-700' : ''}`}
          title="Manage Terms"
          onClick={() => navigate(termsPath)}
        >
          📚
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2 h-full min-h-0">
      <button
        className="text-left px-3 py-2 rounded-md hover:bg-slate-700 font-medium text-slate-200"
        onClick={() => navigate('/')}
      >
        ← Back to Works
      </button>
      <div className="px-3 py-2 font-semibold truncate text-slate-100">📁 {workName}</div>
      <button
        className={`text-left px-3 py-2 rounded-md hover:bg-slate-700 ${isActive(translatePath) ? activeClass : idleClass}`}
        onClick={() => navigate(translatePath)}
      >
        📝 Create New Task
      </button>
      <button
        className={`text-left px-3 py-2 rounded-md hover:bg-slate-700 ${isActive(autoPath) ? activeClass : idleClass}`}
        onClick={() => navigate(autoPath)}
      >
        ⚡ Auto Translate
      </button>
      <button
        className={`text-left px-3 py-2 rounded-md hover:bg-slate-700 ${isActive(termsPath) ? activeClass : idleClass}`}
        onClick={() => navigate(termsPath)}
      >
        📚 Manage Terms
      </button>
      <ChapterList work={work} />
    </div>
  )
}

function formatEntryId(id: string): string {
  // id is a 20-char microsecond timestamp: YYYYMMDDHHMMSS + 6 digits.
  if (id.length < 14) return id
  const y = id.slice(0, 4), mo = id.slice(4, 6), d = id.slice(6, 8)
  const h = id.slice(8, 10), mi = id.slice(10, 12), s = id.slice(12, 14)
  return `${y}-${mo}-${d} ${h}:${mi}:${s}`
}

function SortableChapterRow({
  entry,
  work,
  active,
  onNavigate,
}: {
  entry: ChapterEntry
  work: string
  active: boolean
  onNavigate: (path: string) => void
}) {
  const isRetranslating = entry.status === 'retranslating'
  const isPending = entry.status === 'pending'
  const isFailed = entry.status === 'failed'
  const disabled = isPending || isRetranslating
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: entry.id,
    disabled,
  })
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 50 : undefined,
  }
  const label = isPending
    ? `${formatEntryId(entry.id)} (translating...)`
    : isFailed && !entry.filename
      ? `${formatEntryId(entry.id)} (failed)`
      : `${entry.filename!.replace('.json', '')}${isRetranslating ? ' (translating...)' : ''}`
  const path = isPending
    ? `/work/${encodeURIComponent(work)}/translating/${encodeURIComponent(entry.id)}`
    : entry.filename
      ? chapterViewPath(work, entry.filename)
      : ''
  const rowColor = isFailed
    ? active
      ? 'bg-red-900 text-red-100'
      : 'bg-red-950 text-red-300'
    : active
      ? 'bg-blue-900 text-blue-300'
      : 'text-slate-300'
  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={() => { if (path) onNavigate(path) }}
      className={`group flex items-center gap-1 text-left px-2 py-2 rounded-md text-sm truncate ${rowColor} ${
        isFailed ? 'hover:bg-red-900' : 'hover:bg-slate-700'
      } ${
        disabled ? 'cursor-default' : 'cursor-move'
      } ${isDragging ? 'opacity-70' : ''}`}
    >
      {isFailed ? (
        <span className="text-red-400 font-bold shrink-0" title="Translation failed">✕</span>
      ) : isRetranslating || isPending ? (
        <span className="inline-block w-3 h-3 border-2 border-slate-500 border-t-slate-300 rounded-full animate-spin shrink-0" />
      ) : (
        <span className="text-slate-500 group-hover:text-slate-300 shrink-0" title="Drag to reorder">☰</span>
      )}
      <span className="truncate flex-1">{label}</span>
    </div>
  )
}

function ChapterList({ work }: { work: string }) {
  const navigate = useNavigate()
  const location = useLocation()
  const qc = useQueryClient()
  const { data: chapters } = useQuery({
    queryKey: ['chapters', work],
    queryFn: () => apiGetChapters(work),
  })

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const persistOrder = async (newIds: string[]) => {
    try {
      await apiSetChapterOrder(work, newIds)
    } catch {
      // ignore; will retry on next interaction
    }
    qc.invalidateQueries({ queryKey: ['chapters', work] })
  }

  const onDragEnd = (event: DragEndEvent) => {
    const { active: a, over } = event
    if (!over || a.id === over.id || !chapters) return
    const oldIndex = chapters.findIndex((e) => e.id === a.id)
    const newIndex = chapters.findIndex((e) => e.id === over.id)
    if (oldIndex === -1 || newIndex === -1) return
    const next = arrayMove(chapters, oldIndex, newIndex)
    // Optimistically update the cache so the DOM reorders immediately
    // (one smooth animation). The backend refetch just confirms it.
    qc.setQueryData(['chapters', work], next)
    persistOrder(next.map((e) => e.id))
  }

  const empty = !chapters || chapters.length === 0

  if (empty) return (
    <div className="px-3 py-2 text-sm text-slate-500">No chapters yet.</div>
  )
  return (
    <div className="flex flex-col gap-1 mt-2 flex-1 min-h-0">
      <div className="px-3 text-xs uppercase text-slate-500 shrink-0">Chapters</div>
      <div className="flex-1 min-h-0 overflow-y-auto">
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
        <SortableContext
          items={chapters.map((e) => e.id)}
          strategy={verticalListSortingStrategy}
        >
          {chapters.map((e: ChapterEntry) => {
            const path = e.status === 'pending'
              ? `/work/${encodeURIComponent(work)}/translating/${encodeURIComponent(e.id)}`
              : e.filename
                ? chapterViewPath(work, e.filename)
                : ''
            const active = !!path && location.pathname === path
            return (
              <SortableChapterRow
                key={e.id}
                entry={e}
                work={work}
                active={active}
                onNavigate={navigate}
              />
            )
          })}
        </SortableContext>
      </DndContext>
      </div>
    </div>
  )
}
