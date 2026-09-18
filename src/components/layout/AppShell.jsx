import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function AppShell({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">D</span><span>darukaa<span className="brand-dot">.</span>earth</span></div>
        <div className="sidebar-label">Workspace</div>
        <nav className="sidebar-nav">
          <NavLink to="/projects" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}><span>◈</span> Projects</NavLink>
        </nav>
        <div className="sidebar-footer">
          <div className="status-pill"><span className="status-dot" /> API connected</div>
          <div className="profile"><div className="avatar">{user?.email?.[0]?.toUpperCase()}</div><div className="profile-copy"><strong>{user?.email}</strong><span>Analyst</span></div><button className="icon-button" aria-label="Log out" onClick={() => { logout(); navigate('/login') }}>↗</button></div>
        </div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  )
}
