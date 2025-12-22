import axios from 'axios'

// Get API URL - ensure it includes /api/v1
const envApiUrl = process.env.NEXT_PUBLIC_API_URL
const baseUrl = envApiUrl || 'http://localhost:8000/api/v1'
const API_URL = baseUrl.endsWith('/api/v1') ? baseUrl : `${baseUrl.replace(/\/$/, '')}/api/v1`

// Credentials storage keys
const EMAIL_KEY = 'smart_pantry_email'
const PASSWORD_KEY = 'smart_pantry_password'

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add Basic Auth interceptor - get email and password from localStorage
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const email = localStorage.getItem(EMAIL_KEY)
    const password = localStorage.getItem(PASSWORD_KEY)
    if (email && password) {
      // Create Basic Auth header
      const credentials = btoa(`${email}:${password}`)
      config.headers.Authorization = `Basic ${credentials}`
    }
  }
  return config
})

// Handle 401 errors - clear credentials and redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      // Clear credentials and redirect to login
      removeAuthCredentials()
      // Only redirect if we're not already on the login page
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Helper functions for credentials management
export const setAuthCredentials = (email: string, password: string) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(EMAIL_KEY, email)
    localStorage.setItem(PASSWORD_KEY, password)
  }
}

export const getAuthCredentials = (): { email: string | null; password: string | null } => {
  if (typeof window !== 'undefined') {
    return {
      email: localStorage.getItem(EMAIL_KEY),
      password: localStorage.getItem(PASSWORD_KEY),
    }
  }
  return { email: null, password: null }
}

export const removeAuthCredentials = () => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(EMAIL_KEY)
    localStorage.removeItem(PASSWORD_KEY)
  }
}

