import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function AuthPage({ mode }) {
  const isRegister = mode === 'register'
  const { login, register } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault(); setError(''); setIsSubmitting(true)
    try { await (isRegister ? register(form) : login(form)); navigate(location.state?.from || '/projects', { replace: true }) }
    catch (requestError) { setError(requestError.message) }
    finally { setIsSubmitting(false) }
  }

  return <div className="auth-page"><div className="auth-art"><div className="brand brand-light"><span className="brand-mark">D</span><span>darukaa<span className="brand-dot">.</span>earth</span></div><div className="art-copy"><span className="eyebrow">Environmental intelligence</span><h1>See the living systems behind every project.</h1><p>Map your impact, understand your sites, and make climate data actionable.</p></div><div className="art-coordinate">18° 31' 42.0" N &nbsp; 73° 51' 11.9" E</div></div><div className="auth-panel"><div className="auth-card"><span className="eyebrow">{isRegister ? 'Start a workspace' : 'Welcome back'}</span><h2>{isRegister ? 'Create your account' : 'Sign in to Darukaa'}</h2><p className="auth-subtitle">{isRegister ? 'Build a clearer picture of your environmental projects.' : 'Your project intelligence, in one place.'}</p><form onSubmit={handleSubmit}><label>Email address<input type="email" required autoComplete="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} placeholder="you@company.com" /></label><label>Password<input type="password" required minLength={8} autoComplete={isRegister ? 'new-password' : 'current-password'} value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} placeholder="8 characters minimum" /></label>{error && <div className="form-error">{error}</div>}<button className="primary-button full-width" disabled={isSubmitting}>{isSubmitting ? 'Working...' : isRegister ? 'Create workspace' : 'Enter workspace'}<span>→</span></button></form><p className="auth-switch">{isRegister ? 'Already have an account?' : 'New to Darukaa?'} <Link to={isRegister ? '/login' : '/register'}>{isRegister ? 'Sign in' : 'Create an account'}</Link></p></div></div></div>
}
