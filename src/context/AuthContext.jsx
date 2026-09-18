import { createContext, useContext, useEffect, useState } from 'react'
import { api } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const handleUnauthorized = () => {
      window.localStorage.removeItem('darukaa_token')
      setUser(null)
    }
    window.addEventListener('darukaa:unauthorized', handleUnauthorized)
    const token = window.localStorage.getItem('darukaa_token')
    if (!token) {
      setIsLoading(false)
      return () => window.removeEventListener('darukaa:unauthorized', handleUnauthorized)
    }
    api.me().then(setUser).catch(() => handleUnauthorized()).finally(() => setIsLoading(false))
    return () => window.removeEventListener('darukaa:unauthorized', handleUnauthorized)
  }, [])

  async function login(credentials) {
    const tokenResponse = await api.login(credentials)
    window.localStorage.setItem('darukaa_token', tokenResponse.access_token)
    const currentUser = await api.me()
    setUser(currentUser)
  }

  async function register(credentials) {
    await api.register(credentials)
    await login(credentials)
  }

  function logout() {
    window.localStorage.removeItem('darukaa_token')
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
