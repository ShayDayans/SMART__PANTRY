import { createClient } from '@supabase/supabase-js'

// Get environment variables
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

// Always log in development to help debug
console.log('🔍 [Supabase] Environment Check:')
console.log('  NEXT_PUBLIC_SUPABASE_URL:', supabaseUrl || '❌ NOT SET - using fallback')
console.log('  NEXT_PUBLIC_SUPABASE_ANON_KEY:', supabaseAnonKey ? '✅ Set (' + supabaseAnonKey.substring(0, 20) + '...)' : '❌ NOT SET - using fallback')

// Fallback values (same as in config.py)
const finalUrl = supabaseUrl || 'https://ceyynxrnsuggncjmpwhv.supabase.co'
const finalKey = supabaseAnonKey || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNleXlueHJuc3VnZ25jam1wd2h2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5NjExNzgsImV4cCI6MjA4MTUzNzE3OH0.ZyftH-9apfSUhGD0Ou_dQaUmhzhTJGsq1iL9BHQcY4k'
console.log('🔍 [Supabase] Using URL:', finalUrl)
console.log('🔍 [Supabase] Using Key:', finalKey ? (finalKey.substring(0, 30) + '...') : 'MISSING!')

// Create client
export const supabase = createClient(finalUrl, finalKey)

// Test connection on client side
if (typeof window !== 'undefined') {
  supabase.auth.getSession().then(({ data, error }) => {
    if (error) {
      console.error('❌ [Supabase] Connection Error:', error.message)
      if (error.message.includes('Invalid API key') || error.message.includes('JWT')) {
        console.error('❌ [Supabase] API Key is invalid or expired!')
        console.error('   Please check your Supabase dashboard and update the key in:')
        console.error('   1. FRONT/.env.local (NEXT_PUBLIC_SUPABASE_ANON_KEY)')
        console.error('   2. app/core/config.py (supabase_anon_key)')
      }
    } else {
      console.log('✅ [Supabase] Connection successful')
    }
  }).catch(err => {
    console.error('❌ [Supabase] Failed to connect:', err)
  })
}

