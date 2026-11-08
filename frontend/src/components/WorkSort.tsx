import type { Work } from '../services/api'
import { lastActivityISO } from '../services/api'

export type WorkSort = 'added' | 'lastActivity'

const STORAGE_KEY = 'works-sort'

const OPTIONS: { id: WorkSort; label: string }[] = [
  { id: 'added', label: '添加' },
  { id: 'lastActivity', label: '上次阅读/翻译' },
]

export function loadWorkSort(): WorkSort {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === 'added' || v === 'lastActivity') return v
    if (v === 'lastRead') return 'lastActivity'
  } catch {
    /* ignore */
  }
  return 'added'
}

export function saveWorkSort(v: WorkSort): void {
  localStorage.setItem(STORAGE_KEY, v)
}

function sortValue(w: Work, key: WorkSort): string {
  if (key === 'lastActivity') return lastActivityISO(w)
  return w.added || ''
}

export function sortWorks(works: Work[], key: WorkSort): Work[] {
  return [...works].sort((a, b) => {
    const af = a.finished ? 1 : 0
    const bf = b.finished ? 1 : 0
    if (af !== bf) return af - bf
    const av = sortValue(a, key)
    const bv = sortValue(b, key)
    if (av === bv) return 0
    if (!av) return 1
    if (!bv) return -1
    return bv.localeCompare(av)
  })
}

export function WorkSortButtons({
  value,
  onChange,
}: {
  value: WorkSort
  onChange: (v: WorkSort) => void
}) {
  return (
    <div className="flex flex-wrap gap-3 text-sm">
      {OPTIONS.map((o) => (
        <button
          key={o.id}
          type="button"
          className={value === o.id ? 'text-slate-100' : 'text-slate-500 hover:text-slate-300'}
          onClick={() => onChange(o.id)}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
