import { Routes, Route } from 'react-router-dom'
import { WorksPage } from './pages/WorksPage'
import { ChapterListPage } from './pages/ChapterListPage'
import { ReadPage } from './pages/ReadPage'

export function ReaderApp() {
  return (
    <div className="h-full overflow-hidden bg-slate-900 text-slate-200">
      <Routes>
        <Route path="/" element={<WorksPage />} />
        <Route path="/work/:work" element={<ChapterListPage />} />
        <Route path="/work/:work/chapters/:chapter" element={<ReadPage />} />
      </Routes>
    </div>
  )
}
