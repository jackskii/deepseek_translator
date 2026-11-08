import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  apiGetWorks,
  apiGetDeletedWorks,
  apiCreateWorkFromUrl,
  apiStartAuto,
  apiDeleteWork,
  apiErrorMessage,
  lastActivityLine,
  lastDownloadLine,
  formatTimestamp,
  type Work,
} from '../services/api'
import { WorkSortButtons, loadWorkSort, saveWorkSort, sortWorks } from '../components/WorkSort'
import { Button } from '../components/ui/Button'
import { ConfirmDialog } from '../components/modals/ConfirmDialog'
import { isDesktop } from '../appMode'

const SOURCES = [{ id: 'novel18', label: 'novel18 (syosetu)' }]

export function WorksPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [sort, setSort] = useState(loadWorkSort)
  const [source, setSource] = useState('novel18')
  const [url, setUrl] = useState('')
  const [pendingDelete, setPendingDelete] = useState<Work | null>(null)
  const { data: works, isLoading } = useQuery({
    queryKey: ['works'],
    queryFn: apiGetWorks,
    refetchInterval: 4000,
  })
  const { data: deleted = [] } = useQuery({
    queryKey: ['works', 'deleted'],
    queryFn: apiGetDeletedWorks,
    enabled: isDesktop,
  })

  const createMut = useMutation({
    mutationFn: () => apiCreateWorkFromUrl(source, url.trim()),
    onSuccess: async (res) => {
      qc.invalidateQueries({ queryKey: ['works'] })
      if (res.nextUrl) {
        try {
          await apiStartAuto(res.id, 1)
        } catch {
          // work exists; user can start auto on the chapter list
        }
        qc.invalidateQueries({ queryKey: ['auto-progress', res.id] })
      }
      navigate(`/work/${encodeURIComponent(res.id)}`)
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => apiDeleteWork(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['works'] })
      setPendingDelete(null)
    },
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
      <h1 className="text-xl font-semibold pt-2 mb-1">{isDesktop ? 'Translator' : 'Reader'}</h1>
      <p className="text-sm text-slate-400 mb-3">从网址创建作品，或选择一部开始阅读</p>

      <label className="text-sm text-slate-400">来源</label>
      <select
        className="mt-1 mb-3 w-full p-2 bg-slate-800 border border-slate-600 rounded-md"
        value={source}
        disabled={createMut.isPending}
        onChange={(e) => {
          setSource(e.target.value)
          createMut.reset()
        }}
      >
        {SOURCES.map((s) => (
          <option key={s.id} value={s.id}>{s.label}</option>
        ))}
      </select>
      <label className="text-sm text-slate-400">作品网址</label>
      <div className="mt-1 mb-2 flex gap-2">
        <input
          className="flex-1 min-w-0 px-3 py-2 bg-slate-800 border border-slate-600 rounded-md font-mono text-sm"
          placeholder="https://novel18.syosetu.com/n6320go/"
          value={url}
          disabled={createMut.isPending}
          onChange={(e) => {
            setUrl(e.target.value)
            createMut.reset()
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && url.trim() && !createMut.isPending) createMut.mutate()
          }}
        />
        <Button
          onClick={() => createMut.mutate()}
          disabled={!url.trim() || createMut.isPending}
        >
          创建
        </Button>
      </div>
      {createMut.isError ? (
        <p className="text-sm text-red-400 mb-4">{apiErrorMessage(createMut.error)}</p>
      ) : (
        <div className="mb-4" />
      )}

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
              <div
                className={`rounded-lg border px-4 py-5 flex flex-col cursor-pointer active:bg-black/10 ${
                  w.finished
                    ? 'bg-emerald-950/50 border-emerald-700'
                    : 'bg-slate-800 border-slate-700'
                }`}
                onClick={() => navigate(`/work/${encodeURIComponent(w.id)}`)}
              >
                <p className="font-medium leading-snug">{w.name}</p>
                <div className="flex items-center justify-between gap-2 mt-3">
                  <span className="text-sm text-slate-400">
                    {w.chapterCount ?? 0} 章 · {(w.wordCount ?? 0).toLocaleString('zh-CN')} 字
                    {(w.runningCount ?? 0) > 0 ? ` · 翻译中 ${w.runningCount}` : ''}
                  </span>
                  {!isDesktop ? (
                    <button
                      type="button"
                      className="shrink-0 text-red-500 text-lg leading-none px-1"
                      onClick={(e) => {
                        e.stopPropagation()
                        setPendingDelete(w)
                      }}
                    >
                      🗑
                    </button>
                  ) : null}
                </div>
                <p className="mt-1 text-sm text-slate-500">{lastActivityLine(w)}</p>
                <div className="flex items-center justify-between gap-2 mt-1">
                  <span className="min-w-0 truncate text-sm text-slate-500">
                    {lastDownloadLine(w)}
                  </span>
                  {w.finished ? (
                    <span className="shrink-0 text-sm text-emerald-400">已读完</span>
                  ) : null}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={!!pendingDelete}
        title="删除作品"
        confirmLabel="删除"
        cancelLabel="取消"
        onConfirm={() => pendingDelete && deleteMut.mutate(pendingDelete.id)}
        onCancel={() => setPendingDelete(null)}
      >
        {'作品会移入已删除，文件先保留。'}
      </ConfirmDialog>

      {isDesktop && deleted.length > 0 ? (
        <>
          <h2 className="text-lg font-semibold mt-10 mb-3">已删除</h2>
          <ul className="flex flex-col gap-3">
            {deleted.map((w) => (
              <li key={w.id || w.name}>
                <div
                  className="rounded-lg border border-slate-800 bg-slate-900/70 px-4 py-5 cursor-pointer"
                  onClick={() => navigate(`/work/${encodeURIComponent(w.id)}/deleted`)}
                >
                  <p className="font-medium text-slate-400 leading-snug">{w.name}</p>
                  <p className="mt-3 text-sm text-slate-500">{w.chapterCount} 章</p>
                  {w.deletedAt ? (
                    <p className="mt-1 text-sm text-slate-600">
                      上次删除：{formatTimestamp(w.deletedAt)}
                    </p>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  )
}
