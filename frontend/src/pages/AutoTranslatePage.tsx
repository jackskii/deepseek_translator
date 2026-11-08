import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Button } from '../components/ui/Button'
import { apiGetAutoProgress } from '../services/api'
import { useAppStore } from '../stores/appStore'
import { useWorkName } from '../hooks/useWorkName'

const SOURCES = [{ id: 'novel18', label: 'novel18 (syosetu)' }]

export function AutoTranslatePage() {
  const { work } = useParams<{ work: string }>()
  const workName = useWorkName(work)
  const autoRun = useAppStore((s) => s.autoRun)
  const activeJobs = useAppStore((s) => s.activeJobs)
  const startAutoRun = useAppStore((s) => s.startAutoRun)
  const stopAutoRun = useAppStore((s) => s.stopAutoRun)

  const [source, setSource] = useState('novel18')
  const [url, setUrl] = useState('')
  const [count, setCount] = useState(1)
  const [all, setAll] = useState(false)

  const { data: saved } = useQuery({
    queryKey: ['auto-progress', work],
    queryFn: () => apiGetAutoProgress(work!),
    enabled: !!work,
  })

  const running = autoRun?.status === 'running'
  const mine = !!(autoRun && work && autoRun.work === work)
  const lastUrl = (mine && autoRun.lastUrl) || saved?.lastUrl || ''
  const nextUrl = (mine && autoRun.started > 0 && autoRun.nextUrl) || saved?.nextUrl || ''

  const start = () => {
    if (!work || !url.trim() || running) return
    const n = Math.max(1, Math.floor(Number(count) || 1))
    startAutoRun({
      work,
      source,
      url: url.trim(),
      limit: all ? null : n,
    })
  }

  return (
    <div className="flex flex-col h-full max-w-3xl">
      <h1 className="text-2xl font-bold mb-1">Auto Translate</h1>
      <p className="text-slate-400 mb-6">Current Work: {workName}</p>

      <label className="text-sm font-medium mb-1 text-slate-300">Source</label>
      <select
        className="mb-4 w-full p-2 bg-slate-800 border border-slate-600 rounded-md"
        value={source}
        disabled={running}
        onChange={(e) => setSource(e.target.value)}
      >
        {SOURCES.map((s) => (
          <option key={s.id} value={s.id}>{s.label}</option>
        ))}
      </select>

      <label className="text-sm font-medium mb-1 text-slate-300">Start URL</label>
      <input
        className="mb-4 w-full p-2 bg-slate-800 border border-slate-600 rounded-md font-mono text-sm"
        placeholder="https://novel18.syosetu.com/n0126gh/18/"
        value={url}
        disabled={running}
        onChange={(e) => setUrl(e.target.value)}
      />

      <label className="text-sm font-medium mb-1 text-slate-300">Chapters</label>
      <div className="flex items-center gap-4 mb-6">
        <input
          type="number"
          min={1}
          className="w-28 p-2 bg-slate-800 border border-slate-600 rounded-md disabled:opacity-50"
          value={count}
          disabled={running || all}
          onChange={(e) => setCount(Number(e.target.value))}
        />
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={all}
            disabled={running}
            onChange={(e) => setAll(e.target.checked)}
          />
          全部
        </label>
      </div>

      <div className="flex items-center gap-3 mb-6">
        <Button onClick={start} disabled={running || !url.trim()}>开始</Button>
        <Button variant="secondary" onClick={stopAutoRun} disabled={!running}>停止</Button>
      </div>

      <div className="text-sm text-slate-300 space-y-1">
        {mine && autoRun.status === 'running' && (
          <p className="flex items-center gap-2">
            <span className="inline-block w-3 h-3 border-2 border-slate-500 border-t-slate-300 rounded-full animate-spin" />
            scraping {autoRun.currentUrl}
          </p>
        )}
        {mine && autoRun && (
          <>
            <p>
              started {autoRun.started}
              {autoRun.limit != null ? ` / ${autoRun.limit}` : ''} jobs
              {autoRun.status === 'running' ? ` · running ${Object.keys(activeJobs).length} / 10` : ''}
            </p>
            {autoRun.message && (
              <p className={autoRun.status === 'error' ? 'text-red-400' : 'text-slate-400'}>
                {autoRun.message}
              </p>
            )}
          </>
        )}
        {lastUrl && (
          <p className="pt-2">
            <span className="text-slate-400">上次翻译 </span>
            <span className="font-mono break-all">{lastUrl}</span>
          </p>
        )}
        {!running && nextUrl && (
          <p>
            <span className="text-slate-400">下一章 </span>
            <span className="font-mono break-all">{nextUrl}</span>
          </p>
        )}
      </div>
    </div>
  )
}
