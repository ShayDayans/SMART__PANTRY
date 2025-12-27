'use client'

import { useRouter, usePathname } from 'next/navigation'
import { useAuthStore } from '@/store/useAuthStore'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { 
  Home, 
  ShoppingCart, 
  Package, 
  Receipt, 
  TrendingUp, 
  Settings,
  LogOut,
  ArrowRight,
  Menu,
  X,
  ChefHat
} from 'lucide-react'
import { useState } from 'react'

const navItems = [
  { href: '/dashboard', label: 'Home', icon: Home },
  { href: '/dashboard/pantry', label: 'Pantry', icon: Package },
  { href: '/dashboard/shopping', label: 'Shopping List', icon: ShoppingCart },
  { href: '/dashboard/shopping-active', label: 'Active Shopping', icon: ArrowRight },
  { href: '/dashboard/return-shopping', label: 'Return Shopping', icon: Receipt },
  { href: '/dashboard/recipes', label: 'Recipes', icon: ChefHat },
  { href: '/dashboard/habits', label: 'Habits', icon: Settings },
  { href: '/dashboard/profitability', label: 'Analytics', icon: TrendingUp },
]

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { user, signOut } = useAuthStore()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const handleSignOut = async () => {
    await signOut()
    router.push('/login')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50" dir="ltr">
      <nav className="bg-white/90 backdrop-blur-lg shadow-lg border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-20">
            <div className="flex items-center">
              <Link href="/dashboard" className="flex items-center space-x-3 group">
                <motion.div
                  whileHover={{ scale: 1.1, rotate: 5 }}
                  className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg group-hover:shadow-xl transition-all"
                >
                  <Package className="w-6 h-6 text-white" />
                </motion.div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 bg-clip-text text-transparent">
                  Smart Pantry
                </h1>
              </Link>
            </div>

            <div className="hidden md:flex items-center space-x-2">
              {navItems.map((item) => {
                const Icon = item.icon
                const isActive = pathname === item.href
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`relative flex items-center px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                      isActive
                        ? 'text-blue-600 bg-blue-50'
                        : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                    }`}
                  >
                    {isActive && (
                      <motion.span
                        layoutId="activeTab"
                        className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full"
                      />
                    )}
                    <Icon className="mr-2 h-4 w-4" />
                    {item.label}
                  </Link>
                )
              })}
            </div>

            <div className="flex items-center space-x-4">
              <div className="hidden sm:flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center text-white font-semibold shadow-lg">
                  {user?.email?.charAt(0).toUpperCase() || 'U'}
                </div>
                <div className="text-left">
                  <p className="text-sm font-semibold text-gray-800">
                    {user?.user_metadata?.username || 'User'}
                  </p>
                  <p className="text-xs text-gray-500">{user?.email}</p>
                </div>
              </div>
              <button
                onClick={handleSignOut}
                className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all"
                title="Sign Out"
              >
                <LogOut className="h-5 w-5" />
              </button>
              
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="md:hidden p-2 text-gray-600 hover:bg-gray-100 rounded-xl"
              >
                {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
              </button>
            </div>
          </div>
        </div>

        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden border-t border-gray-200 bg-white/95 backdrop-blur-lg"
          >
            <div className="px-4 py-4 space-y-2">
              {navItems.map((item) => {
                const Icon = item.icon
                const isActive = pathname === item.href
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                      isActive
                        ? 'text-blue-600 bg-blue-50'
                        : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className="mr-3 h-5 w-5" />
                    {item.label}
                  </Link>
                )
              })}
            </div>
          </motion.div>
        )}
      </nav>

      <main className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          {children}
        </motion.div>
      </main>
    </div>
  )
}
