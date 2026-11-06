import { ReactNode } from 'react'
import { Button } from '../ui/Button'

type Props = {
  open: boolean
  title: string
  confirmLabel?: string
  cancelLabel?: string
  onConfirm: () => void
  onCancel: () => void
  children: ReactNode
}

export function ConfirmDialog({
  open,
  title,
  confirmLabel = 'Delete',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
  children,
}: Props) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-slate-800 border border-slate-700 rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
        <h2 className="text-lg font-semibold mb-4 text-slate-100">{title}</h2>
        <div className="mb-6 text-slate-300 whitespace-pre-line">{children}</div>
        <div className="flex gap-3 justify-end">
          <Button variant="secondary" onClick={onCancel}>{cancelLabel}</Button>
          <Button variant="danger" onClick={onConfirm}>{confirmLabel}</Button>
        </div>
      </div>
    </div>
  )
}
