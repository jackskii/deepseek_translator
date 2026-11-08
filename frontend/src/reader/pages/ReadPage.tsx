import { useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  apiGetChapter,
  apiGetChapters,
  apiTouchLastRead,
  chapterFilename,
  chapterViewPath,
} from '../../services/api'
import { setBookmark } from '../bookmark'
import { chapterTitle, readableChapters } from '../readable'

export function ReadPage() {
  const { work, chapter: slug } = useParams<{ work: string; chapter: string }>()
  const navigate = useNavigate()
  const filename = slug ? chapterFilename(slug) : ''

  const { data: chapters } = useQuery({
    queryKey: ['chapters', work],
    queryFn: () => apiGetChapters(work!),
    enabled: !!work,
  })
  const { data, isLoading } = useQuery({
    queryKey: ['chapter', work, filename],
    queryFn: () => apiGetChapter(work!, filename),
    enabled: !!work && !!filename,
  })

  const scrollRef = useRef<HTMLElement>(null)
  useEffect(() => {
    scrollRef.current?.scrollTo(0, 0)
  }, [filename])

  useEffect(() => {
    if (!work || !filename) return
    setBookmark(work, filename, chapterTitle(filename))
    apiTouchLastRead(work).catch(() => {})
  }, [work, filename])

  const list = readableChapters(chapters)
  const idx = list.findIndex((e) => e.filename === filename)
  const prev = idx > 0 ? list[idx - 1] : null
  const next = idx >= 0 && idx < list.length - 1 ? list[idx + 1] : null
  const title = filename ? chapterTitle(filename) : ''

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
      </header>

      <main ref={scrollRef} className="flex-1 overflow-y-auto">
        {isLoading ? (
          <p className="px-5 py-8 text-slate-400">加载中…</p>
        ) : !data ? (
          <p className="px-5 py-8 text-slate-400">找不到这一章。</p>
        ) : (
          <article className="px-5 py-5 font-chinese text-[1.15rem] leading-[1.85] whitespace-pre-wrap">
            {data.translated || '（没有译文）'}
          </article>
        )}
      </main>

      <nav
        className="shrink-0 grid grid-cols-2 gap-2 px-3 py-3 border-t border-slate-700 bg-slate-900"
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
          disabled={!next}
          onClick={() => next && navigate(chapterViewPath(work!, next.filename!))}
        >
          下一章
        </button>
      </nav>
    </div>
  )
}
