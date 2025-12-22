'use client'

import { useEffect } from 'react'
import { useAuthStore } from '@/store/useAuthStore'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { setLoading, initialize, email, password } = useAuthStore()

  useEffect(() => {
    // Initialize auth state from localStorage
    initialize()

    // Credentials are already in localStorage, they'll be sent automatically with API requests
    setLoading(false)
  }, [initialize, setLoading, email, password])

  return <>{children}</>
}

