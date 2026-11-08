import { useEffect, useRef } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiGetWorks, apiGetChapters, chapterViewPath } from '../../services/api'
import { getBookmark } from '../bookmark'
import { chapterTitle, readableChapters } from '../readable'

const PAGE_SIZE = 50

export function ChapterListPage() {
  const { work } = useParams<{ work: string }>()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const scrollRef = useRef<HTMLDivElement>(null)

  const { data: works } = useQuery({
    queryKey: ['works'],
    queryFn: apiGetWorks,
  })
  const { data: chapters, isLoading } = useQuery({
    queryKey: ['chapters', work],
    queryFn: () => apiGetChapters(work!),
    enabled: !!work,
  })

  const workName = works?.find((w) => w.id === work)?.name ?? ''
  const list = readableChapters(chapters)
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
        {work && list.length > 0 ? (
          <a
            href={`/api/works/${encodeURIComponent(work)}/export`}
            className="shrink-0 px-2 py-2 text-slate-300 active:text-white"
          >
            下载
          </a>
        ) : (
          <span className="shrink-0 px-2 py-2 text-slate-600">下载</span>
        )}
      </header>

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
                <li key={e.id}>
                  <button
                    className="w-full text-left px-3 py-3.5 active:bg-slate-800"
                    onClick={() => navigate(chapterViewPath(work!, e.filename!))}
                  >
                    <span className="block leading-snug">{chapterTitle(e.filename!)}</span>
                  </button>
                </li>
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
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((n) => (
                  <button
                    key={n}
                    className={`min-w-[2.5rem] px-3 py-2 rounded-md active:bg-slate-700 ${
                      n === currentPage ? 'bg-slate-600' : 'bg-slate-800'
                    }`}
                    onClick={() => goPage(n)}
                  >
                    {n}
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
    </div>
  )
}
