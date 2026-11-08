import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiGetWorks, workDateLabel } from '../../services/api'
import { WorkSortButtons, loadWorkSort, saveWorkSort, sortWorks } from '../../components/WorkSort'

export function WorksPage() {
  const navigate = useNavigate()
  const [sort, setSort] = useState(loadWorkSort)
  const { data: works, isLoading } = useQuery({
    queryKey: ['works'],
    queryFn: apiGetWorks,
  })

  const listed = works ? sortWorks(works, sort) : []

  return (
    <div
      className="h-full overflow-y-auto px-4"
      style={{
        paddingTop: 'max(1rem, env(safe-area-inset-top))',
        paddingBottom: 'max(1.5rem, env(safe-area-inset-bottom))',
      }}
    >
      <h1 className="text-xl font-semibold pt-2 mb-1">Reader</h1>
      <p className="text-sm text-slate-400 mb-3">选择一部作品开始阅读</p>
      <div className="mb-6">
        <WorkSortButtons
          value={sort}
          onChange={(v) => {
            setSort(v)
            saveWorkSort(v)
          }}
        />
      </div>

      {isLoading ? (
        <p className="text-slate-400">加载中…</p>
      ) : listed.length === 0 ? (
        <p className="text-slate-400">还没有作品。</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {listed.map((w) => (
            <li key={w.id}>
              <button
                className="w-full text-left px-4 py-5 rounded-lg bg-slate-800 border border-slate-700 active:bg-slate-700"
                onClick={() => navigate(`/work/${encodeURIComponent(w.id)}`)}
              >
                <span className="block font-medium leading-snug">{w.name}</span>
                <span className="block mt-3 text-sm text-slate-400">
                  {w.chapterCount ?? 0} 章 · {(w.wordCount ?? 0).toLocaleString('zh-CN')} 字
                </span>
                <span className="block mt-1 text-sm text-slate-500">
                  上次阅读 {workDateLabel(w.lastRead)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
