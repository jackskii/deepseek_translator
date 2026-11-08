import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { apiGetDeletedWorks, apiRestoreWork, apiPurgeWork, apiErrorMessage } from '../services/api'
import { ConfirmDialog } from '../components/modals/ConfirmDialog'
import { Button } from '../components/ui/Button'

export function DeletedWorkPage() {
  const { work } = useParams<{ work: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [purgeOpen, setPurgeOpen] = useState(false)
  const { data: deleted = [], isLoading } = useQuery({
    queryKey: ['works', 'deleted'],
    queryFn: apiGetDeletedWorks,
  })
  const item = deleted.find((w) => w.id === work)

  const restoreMut = useMutation({
    mutationFn: () => apiRestoreWork(work!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['works'] })
      navigate(`/work/${encodeURIComponent(work!)}`)
    },
  })
  const purgeMut = useMutation({
    mutationFn: () => apiPurgeWork(work!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['works'] })
      setPurgeOpen(false)
      navigate('/')
    },
  })

  return (
    <div className="h-full overflow-y-auto flex flex-col">
      <header
        className="sticky top-0 z-10 bg-slate-900 border-b border-slate-700 px-3 py-3 flex items-center gap-3"
        style={{ paddingTop: 'max(0.75rem, env(safe-area-inset-top))' }}
      >
        <button
          className="shrink-0 px-2 py-2 text-slate-300 hover:text-white"
          onClick={() => navigate('/')}
        >
          ← 作品
        </button>
        <h1 className="flex-1 min-w-0 truncate font-medium">{item?.name || '已删除'}</h1>
      </header>
      <div className="flex-1 px-4 py-10 flex flex-col items-center gap-4">
        {isLoading ? (
          <p className="text-slate-400">加载中…</p>
        ) : !item ? (
          <p className="text-slate-400">找不到这部已删除作品。</p>
        ) : (
          <>
            <p className="text-slate-500 text-sm">{item.chapterCount} 章 · 文件仍保留</p>
            {restoreMut.isError ? (
              <p className="text-sm text-red-400">{apiErrorMessage(restoreMut.error)}</p>
            ) : null}
            {purgeMut.isError ? (
              <p className="text-sm text-red-400">{apiErrorMessage(purgeMut.error)}</p>
            ) : null}
            <div className="flex gap-3">
              <Button
                onClick={() => restoreMut.mutate()}
                disabled={restoreMut.isPending}
              >
                恢复
              </Button>
              <Button
                variant="danger"
                onClick={() => setPurgeOpen(true)}
                disabled={purgeMut.isPending}
              >
                彻底删除
              </Button>
            </div>
          </>
        )}
      </div>
      <ConfirmDialog
        open={purgeOpen}
        title="彻底删除"
        confirmLabel="彻底删除"
        cancelLabel="取消"
        onConfirm={() => purgeMut.mutate()}
        onCancel={() => setPurgeOpen(false)}
      >
        {`将从磁盘删除「${item?.name ?? ''}」的全部章节和名词。无法恢复。`}
      </ConfirmDialog>
    </div>
  )
}
