import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Layout from './components/Layout'
import Intro from './pages/Intro'
import Login from './pages/Login'
import Register from './pages/Register'
import UserProfile from './pages/UserProfile'
import Construction from './pages/Construction'
import ShareReport from './pages/ShareReport'

const router = createBrowserRouter([
  { path: '/', element: <Layout />, children: [
    { index: true, element: <Intro /> },
    { path: 'login', element: <Login /> },
    { path: 'register', element: <Register /> },
    { path: 'user/:id', element: <UserProfile /> },
    { path: 'construction', element: <Construction /> },
    { path: 'share-report', element: <ShareReport /> },
    { path: 'intro', element: <Intro /> },
  ]},
])

export default function App() {
  return <RouterProvider router={router} />
}
