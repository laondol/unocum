import { BrowserRouter, Routes, Route } from 'react-router-dom'
import ShareList from './pages/ShareList'
import ShareDetail from './pages/ShareDetail'
import ShareReport from './pages/ShareReport'
import ShareEdit from './pages/ShareEdit'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/share" element={<ShareList />} />
        <Route path="/share/detail/:id" element={<ShareDetail />} />
        <Route path="/share/report" element={<ShareReport />} />
        <Route path="/share/edit/:id" element={<ShareEdit />} />
        <Route path="*" element={<ShareList />} />
      </Routes>
    </BrowserRouter>
  )
}