import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  apiGetWorks,
  apiGetChapters,
  apiSetFinished,
  apiStartAuto,
  apiStopAuto,
  apiDeleteWork,
  apiErrorMessage,
  chapterViewPath,
  type ChapterEntry,
} from '../../services/api'
import { getBookmark } from '../bookmark'
import { chapterTitle, readableChapters, translatedCount } from '../readable'
import { useWorkSync } from '../../hooks/useAutoTranslate'
import { isDesktop } from '../../appMode'
import { ConfirmDialog } from '../../components/modals/ConfirmDialog'

const PAGE_SIZE = 50

function ChapterRow({
  entry,
  onOpen,
}: {
  entry: ChapterEntry
  onOpen: () => void
}) {
  return (
    <li>
      <button
        className="w-full text-left px-3 py-3.5 active:bg-slate-800"
        onClick={onOpen}
      >
        <span className="block leading-snug">
          {chapterTitle(entry.filename!)}
          {entry.status === 'pending' || entry.status === 'retranslating' ? (
            <span className="text-slate-500"> 翻译中</span>
          ) : null}
        </span>
      </button>
    </li>
  )
}

export function ChapterListPage() {
  const { work } = useParams<{ work: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const scrollRef = useRef<HTMLDivElement>(null)
  const [dlOpen, setDlOpen] = useState(false)
  const [start, setStart] = useState(1)
  const [end, setEnd] = useState(1)
  const [rangeWork, setRangeWork] = useState<string | null>(null)
  const [nextCount, setNextCount] = useState(1)
  const [pendingDelete, setPendingDelete] = useState(false)
  const { auto } = useWorkSync(work)

  const { data: works } = useQuery({
    queryKey: ['works'],
    queryFn: apiGetWorks,
  })
  const { data: chapters, isLoading } = useQuery({
    queryKey: ['chapters', work],
    queryFn: () => apiGetChapters(work!),
    enabled: !!work,
    refetchInterval: (q) => {
      const rows = q.state.data
      if (rows?.some((e) => e.status === 'pending' || e.status === 'retranslating')) return 2000
      return false
    },
  })

  const currentWork = works?.find((w) => w.id === work)
  const workName = currentWork?.name ?? ''
  const finished = !!currentWork?.finished
  const list = readableChapters(chapters)
  const doneCount = translatedCount(chapters)
  const n = doneCount
  const running = !!auto?.running
  const workUrl = auto?.workUrl || ''
  const nextUrl = auto?.nextUrl || ''
  const showAuto = !!(workUrl || nextUrl || auto?.lastUrl)
  const totalPages = Math.max(1, Math.ceil(list.length / PAGE_SIZE))
  const rawPage = parseInt(searchParams.get('page') || '1', 10)
  const currentPage = Number.isFinite(rawPage)
    ? Math.min(totalPages, Math.max(1, rawPage))
    : 1
  const slice = list.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  const bookmark = work ? getBookmark(work) : null
  const bookmarkOk =
    currentPage === 1 &&
    !!bookmark &&
    list.some((e) => e.filename === bookmark.filename)

  const startClamped = n > 0 ? Math.min(Math.max(1, start), n) : 1
  const endClamped = n > 0 ? Math.min(Math.max(startClamped, end), n) : 1
  const exportHref =
    work && n > 0
      ? `/api/works/${encodeURIComponent(work)}/export?start=${startClamped}&end=${endClamped}`
      : ''

  const finishedMut = useMutation({
    mutationFn: (next: boolean) => apiSetFinished(work!, next),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['works'] })
    },
  })
  const startMut = useMutation({
    mutationFn: () => apiStartAuto(work!, Math.max(1, Math.floor(nextCount) || 1)),
    onSuccess: (data) => {
      qc.setQueryData(['auto-progress', work], data)
      qc.invalidateQueries({ queryKey: ['chapters', work] })
      qc.invalidateQueries({ queryKey: ['jobs', work] })
    },
  })
  const stopMut = useMutation({
    mutationFn: () => apiStopAuto(work!),
    onSuccess: (data) => {
      qc.setQueryData(['auto-progress', work], data)
    },
  })
  const deleteMut = useMutation({
    mutationFn: () => apiDeleteWork(work!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['works'] })
      setPendingDelete(false)
      navigate('/')
    },
  })

  useEffect(() => {
    if (!work || n === 0) return
    if (rangeWork !== work) {
      setStart(1)
      setEnd(n)
      setRangeWork(work)
    }
  }, [work, n, rangeWork])

  useEffect(() => {
    scrollRef.current?.scrollTo(0, 0)
  }, [currentPage])

  function goPage(p: number) {
    const next = Math.min(totalPages, Math.max(1, p))
    if (next <= 1) setSearchParams({})
    else setSearchParams({ page: String(next) })
  }

  return (
    <div ref={scrollRef} className="h-full overflow-y-auto flex flex-col">
      <header
        className="sticky top-0 z-10 bg-slate-900 border-b border-slate-700 px-3 py-3 flex items-center gap-3"
        style={{ paddingTop: 'max(0.75rem, env(safe-area-inset-top))' }}
      >
        <button
          className="shrink-0 px-2 py-2 text-slate-300 active:text-white"
          onClick={() => navigate('/')}
        >
          ← 作品
        </button>
        <h1 className="flex-1 min-w-0 truncate font-medium">{workName}</h1>
        {isDesktop ? (
          <>
            <button
              type="button"
              className="shrink-0 px-2 py-2 text-slate-300 hover:text-white"
              onClick={() => work && navigate(`/work/${encodeURIComponent(work)}/terms`)}
            >
              名词表
            </button>
            <button
              type="button"
              className="shrink-0 text-red-500 hover:text-red-400 text-lg leading-none px-2"
              title="删除作品"
              onClick={() => setPendingDelete(true)}
            >
              🗑
            </button>
          </>
        ) : null}
      </header>

      {showAuto ? (
        <div className="shrink-0 px-3 py-3 border-b border-slate-700 space-y-2">
          {workUrl ? (
            <a
              href={workUrl}
              target="_blank"
              rel="noreferrer"
              className="block text-sm text-blue-400 break-all active:text-blue-300"
            >
              {workUrl}
            </a>
          ) : null}
          <p className="text-sm text-slate-400">已翻译：{doneCount} 章</p>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-slate-300">翻译下</span>
            <input
              type="number"
              min={1}
              className="w-16 px-2 py-2 bg-slate-800 border border-slate-600 rounded-md text-center disabled:opacity-50"
              value={nextCount}
              disabled={running}
              onChange={(e) => setNextCount(Math.max(1, parseInt(e.target.value, 10) || 1))}
            />
            <span className="text-sm text-slate-300">章</span>
            <button
              type="button"
              className="px-3 py-2 rounded-md bg-blue-600 text-white active:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500"
              disabled={running || !nextUrl || !work || startMut.isPending}
              onClick={() => startMut.mutate()}
            >
              开始
            </button>
            <button
              type="button"
              className="px-3 py-2 rounded-md bg-slate-700 text-slate-200 active:bg-slate-600 disabled:opacity-40"
              disabled={!running || stopMut.isPending}
              onClick={() => stopMut.mutate()}
            >
              停止
            </button>
          </div>
          {startMut.isError ? (
            <p className="text-sm text-red-400">{apiErrorMessage(startMut.error)}</p>
          ) : null}
          {running && auto?.currentUrl ? (
            <p className="flex items-center gap-2 text-sm text-slate-400">
              <span className="inline-block w-3 h-3 border-2 border-slate-500 border-t-slate-300 rounded-full animate-spin" />
              scraping {auto.currentUrl}
            </p>
          ) : null}
          {auto?.message ? (
            <p className="text-sm text-slate-400">{auto.message}</p>
          ) : null}
        </div>
      ) : null}

      <div className="shrink-0 flex items-center px-3 py-2 border-b border-slate-700 bg-slate-900">
        <button
          type="button"
          className={`px-2 py-2 ${finished ? 'text-emerald-400' : 'text-slate-300 active:text-white'}`}
          disabled={!work || finishedMut.isPending}
          onClick={() => work && finishedMut.mutate(!finished)}
        >
          已读完
        </button>
        <button
          type="button"
          className="ml-auto px-2 py-2 text-slate-300 active:text-white disabled:text-slate-600"
          disabled={n === 0}
          onClick={() => setDlOpen(true)}
        >
          下载
        </button>
      </div>

      {dlOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
          onClick={() => setDlOpen(false)}
        >
          <div
            className="w-full max-w-sm rounded-lg bg-slate-800 border border-slate-700 p-5"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold mb-4">下载</h2>
            <div className="flex flex-wrap items-center gap-2 mb-6">
              <input
                type="number"
                min={1}
                max={n}
                className="w-16 px-2 py-2 bg-slate-900 border border-slate-600 rounded-md text-center"
                value={start}
                onChange={(e) => setStart(parseInt(e.target.value, 10) || 1)}
              />
              <span className="text-slate-500">-</span>
              <input
                type="number"
                min={1}
                max={n}
                className="w-16 px-2 py-2 bg-slate-900 border border-slate-600 rounded-md text-center"
                value={end}
                onChange={(e) => setEnd(parseInt(e.target.value, 10) || 1)}
              />
              <button
                type="button"
                className="px-3 py-2 rounded-md bg-slate-700 active:bg-slate-600"
                onClick={() => {
                  setStart(1)
                  setEnd(n)
                }}
              >
                全部
              </button>
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className="px-4 py-2 rounded-md bg-slate-700 active:bg-slate-600"
                onClick={() => setDlOpen(false)}
              >
                取消
              </button>
              {exportHref ? (
                <a
                  href={exportHref}
                  className="px-4 py-2 rounded-md bg-blue-600 text-white active:bg-blue-700"
                  onClick={() => {
                    setDlOpen(false)
                    window.setTimeout(() => {
                      qc.invalidateQueries({ queryKey: ['works'] })
                    }, 800)
                  }}
                >
                  下载
                </a>
              ) : (
                <span className="px-4 py-2 rounded-md bg-slate-700 text-slate-500">下载</span>
              )}
            </div>
          </div>
        </div>
      )}

      <div
        className="flex-1 px-4 py-4"
        style={{ paddingBottom: 'max(1.5rem, env(safe-area-inset-bottom))' }}
      >
        {isLoading ? (
          <p className="text-slate-400">加载中…</p>
        ) : list.length === 0 ? (
          <p className="text-slate-400">还没有可阅读的章节。</p>
        ) : (
          <>
            {bookmarkOk && bookmark && (
              <button
                className="w-full text-left px-3 py-3.5 mb-3 rounded-md bg-slate-800 border border-slate-700 active:bg-slate-700"
                onClick={() => navigate(chapterViewPath(work!, bookmark.filename))}
              >
                <span className="block leading-snug">继续 {bookmark.title}</span>
              </button>
            )}
            <ul className="divide-y divide-slate-700 border-y border-slate-700">
              {slice.map((e) => (
                <ChapterRow
                  key={e.id}
                  entry={e}
                  onOpen={() => navigate(chapterViewPath(work!, e.filename!))}
                />
              ))}
            </ul>
            {totalPages > 1 && (
              <nav className="flex flex-wrap items-center justify-center gap-2 mt-6">
                <button
                  className="px-3 py-2 rounded-md bg-slate-800 disabled:opacity-30 active:bg-slate-700"
                  disabled={currentPage <= 1}
                  onClick={() => goPage(currentPage - 1)}
                >
                  上一页
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((nPage) => (
                  <button
                    key={nPage}
                    className={`min-w-[2.5rem] px-3 py-2 rounded-md active:bg-slate-700 ${
                      nPage === currentPage ? 'bg-slate-600' : 'bg-slate-800'
                    }`}
                    onClick={() => goPage(nPage)}
                  >
                    {nPage}
                  </button>
                ))}
                <button
                  className="px-3 py-2 rounded-md bg-slate-800 disabled:opacity-30 active:bg-slate-700"
                  disabled={currentPage >= totalPages}
                  onClick={() => goPage(currentPage + 1)}
                >
                  下一页
                </button>
              </nav>
            )}
          </>
        )}
      </div>

      <ConfirmDialog
        open={pendingDelete}
        title="删除作品"
        confirmLabel="删除"
        cancelLabel="取消"
        onConfirm={() => deleteMut.mutate()}
        onCancel={() => setPendingDelete(false)}
      >
        {'作品会移入已删除，文件先保留。可在已删除里恢复或彻底删除。'}
      </ConfirmDialog>
    </div>
  )
}
