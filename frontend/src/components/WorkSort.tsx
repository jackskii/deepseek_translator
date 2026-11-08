import type { Work } from '../services/api'

export type WorkSort = 'added' | 'lastTranslated' | 'lastRead'

const STORAGE_KEY = 'works-sort'

const OPTIONS: { id: WorkSort; label: string }[] = [
  { id: 'added', label: '添加' },
  { id: 'lastTranslated', label: '上次翻译' },
  { id: 'lastRead', label: '上次阅读' },
]

export function loadWorkSort(): WorkSort {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === 'added' || v === 'lastTranslated' || v === 'lastRead') return v
  } catch {
    /* ignore */
  }
  return 'lastTranslated'
}

export function saveWorkSort(v: WorkSort): void {
  localStorage.setItem(STORAGE_KEY, v)
}

export function sortWorks(works: Work[], key: WorkSort): Work[] {
  return [...works].sort((a, b) => {
    const av = a[key] || ''
    const bv = b[key] || ''
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
