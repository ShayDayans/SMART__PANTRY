import axios from 'axios'
import { supabase } from './supabase'

// Get API URL - ensure it includes /api/v1
const envApiUrl = process.env.NEXT_PUBLIC_API_URL
const baseUrl = envApiUrl || 'http://localhost:8000/api/v1'
const API_URL = baseUrl.endsWith('/api/v1') ? baseUrl : `${baseUrl.replace(/\/$/, '')}/api/v1`

// Debug: Log API URL
console.log('🔍 [API] Configuration:')
console.log('  NEXT_PUBLIC_API_URL:', envApiUrl || '❌ NOT SET')
console.log('  Final API_URL:', API_URL)

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token interceptor
api.interceptors.request.use(async (config) => {
  try {
    const { data: { session } } = await supabase.auth.getSession()
    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`
    }
  } catch (error) {
    console.error('Error getting session:', error)
  }
  return config
})

