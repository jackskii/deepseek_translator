import { Route, Routes } from 'react-router-dom'
import { WorksPage } from './pages/WorksPage'
import { ChapterListPage } from './reader/pages/ChapterListPage'
import { ChapterPage } from './pages/ChapterPage'
import { DeletedWorkPage } from './pages/DeletedWorkPage'
import { TermsPage } from './pages/TermsPage'
import { isDesktop } from './appMode'

export default function App() {
  return (
    <div className="h-full overflow-hidden bg-slate-900 text-slate-200">
      <Routes>
        <Route path="/" element={<WorksPage />} />
        <Route path="/work/:work" element={<ChapterListPage />} />
        <Route path="/work/:work/chapters/:chapter" element={<ChapterPage />} />
        {isDesktop ? <Route path="/work/:work/terms" element={<TermsPage />} /> : null}
        {isDesktop ? <Route path="/work/:work/deleted" element={<DeletedWorkPage />} /> : null}
      </Routes>
    </div>
  )
}
