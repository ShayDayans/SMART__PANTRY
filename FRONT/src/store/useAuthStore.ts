import { create } from 'zustand'
import { setAuthCredentials, removeAuthCredentials, getAuthCredentials } from '@/lib/api'

interface User {
  user_id: string
  email: string
  username?: string | null
  created_at: string
  updated_at: string
}

interface AuthState {
  user: User | null
  email: string | null
  password: string | null
  loading: boolean
  setUser: (user: User | null) => void
  setCredentials: (email: string, password: string) => void
  setLoading: (loading: boolean) => void
  signOut: () => Promise<void>
  initialize: () => void
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  email: null,
  password: null,
  loading: true,
  setUser: (user) => set({ user }),
  setCredentials: (email, password) => {
    setAuthCredentials(email, password)
    set({ email, password })
  },
  setLoading: (loading) => set({ loading }),
  signOut: async () => {
    removeAuthCredentials()
    set({ user: null, email: null, password: null })
  },
  initialize: () => {
    // Load credentials from localStorage on initialization
    if (typeof window !== 'undefined') {
      const { email, password } = getAuthCredentials()
      if (email && password) {
        set({ email, password, loading: false })
      } else {
        set({ loading: false })
      }
    }
  },
}))
