import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiGetWorks } from '../../services/api'

export function WorksPage() {
  const navigate = useNavigate()
  const { data: works, isLoading } = useQuery({
    queryKey: ['works'],
    queryFn: apiGetWorks,
  })

  return (
    <div
      className="h-full overflow-y-auto px-4"
      style={{
        paddingTop: 'max(1rem, env(safe-area-inset-top))',
        paddingBottom: 'max(1.5rem, env(safe-area-inset-bottom))',
      }}
    >
      <h1 className="text-xl font-semibold pt-2 mb-1">Reader</h1>
      <p className="text-sm text-slate-400 mb-6">选择一部作品开始阅读</p>

      {isLoading ? (
        <p className="text-slate-400">加载中…</p>
      ) : !works || works.length === 0 ? (
        <p className="text-slate-400">还没有作品。</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {works.map((w) => (
            <li key={w.id}>
              <button
                className="w-full text-left px-4 py-4 rounded-lg bg-slate-800 border border-slate-700 active:bg-slate-700"
                onClick={() => navigate(`/work/${encodeURIComponent(w.id)}`)}
              >
                <span className="block font-medium leading-snug">{w.name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
