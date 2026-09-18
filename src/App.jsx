import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import AuthPage from './pages/AuthPage'
import Projects from './pages/Projects'
import ProjectDashboard from './pages/ProjectDashboard'

function LoadingScreen() {
  return <div className="center-state"><span className="spinner" /> Restoring your workspace...</div>
}

function ProtectedRoute() {
  const { user, isLoading } = useAuth()
  if (isLoading) return <LoadingScreen />
  return user ? <Outlet /> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/projects" replace />} />
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/register" element={<AuthPage mode="register" />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/:projectId" element={<ProjectDashboard />} />
      </Route>
      <Route path="*" element={<Navigate to="/projects" replace />} />
    </Routes>
  )
}
