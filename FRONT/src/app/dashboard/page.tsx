'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/useAuthStore'
import { DashboardLayout } from '@/components/layouts/DashboardLayout'
import Link from 'next/link'
import { 
  Package, 
  ShoppingCart, 
  Receipt, 
  TrendingUp, 
  AlertCircle,
  CheckCircle,
  Clock,
  DollarSign,
  Activity,
  Users,
  Calendar
} from 'lucide-react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'

interface Stats {
  inventory: {
    total_products: number
    empty: number
    low: number
    medium: number
    full: number
    stock_health: number
  }
  shopping: {
    active_lists: number
    total_items: number
    bought_items: number
    pending_items: number
    completion_rate: number
  }
  activity: {
    purchases_this_week: number
    adjustments_this_week: number
    total_receipts: number
    total_spent: number
    total_activities: number
  }
  predictions: {
    items_running_out: number
    avg_confidence: number
    total_forecasts: number
  }
}

export default function DashboardPage() {
  const router = useRouter()
  const { user, loading } = useAuthStore()
  const [stats, setStats] = useState<Stats | null>(null)
  const [loadingStats, setLoadingStats] = useState(true)

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  useEffect(() => {
    if (user) {
      loadStats()
    }
  }, [user])

  const loadStats = async () => {
    try {
      setLoadingStats(true)
      const response = await api.get(`/stats/${user?.user_id}`)
      setStats(response.data)
    } catch (error) {
      console.error('Error loading statistics:', error)
    } finally {
      setLoadingStats(false)
    }
  }

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  const quickActions = [
    {
      title: 'Pantry',
      description: 'Manage your inventory',
      icon: Package,
      href: '/dashboard/pantry',
      color: 'from-blue-500 to-cyan-500',
      bgColor: 'bg-blue-50',
      iconColor: 'text-blue-600',
    },
    {
      title: 'Shopping',
      description: 'Create shopping lists',
      icon: ShoppingCart,
      href: '/dashboard/shopping',
      color: 'from-green-500 to-emerald-500',
      bgColor: 'bg-green-50',
      iconColor: 'text-green-600',
    },
    {
      title: 'Scan Receipt',
      description: 'Add items from receipt',
      icon: Receipt,
      href: '/dashboard/return-shopping',
      color: 'from-purple-500 to-pink-500',
      bgColor: 'bg-purple-50',
      iconColor: 'text-purple-600',
    },
    {
      title: 'Analytics',
      description: 'View insights',
      icon: TrendingUp,
      href: '/dashboard/profitability',
      color: 'from-orange-500 to-red-500',
      bgColor: 'bg-orange-50',
      iconColor: 'text-orange-600',
    },
  ]

  return (
    <DashboardLayout>
      <div className="px-4 py-6 sm:px-0 max-w-7xl mx-auto">
        {/* Welcome Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-3xl p-8 text-white shadow-2xl">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-4xl font-bold mb-2">Welcome back! 👋</h1>
                <p className="text-blue-100 text-lg">{user.email}</p>
                <p className="text-blue-200 text-sm mt-2">
                  {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                </p>
              </div>
              <div className="hidden md:block">
                <div className="w-24 h-24 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-sm">
                  <Users className="h-12 w-12" />
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Statistics Cards */}
        {loadingStats ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : stats && (
          <>
            {/* Main Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {/* Inventory Health */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-white rounded-2xl shadow-lg p-6 border-2 border-blue-100 hover:shadow-xl transition-all"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="p-3 bg-blue-100 rounded-xl">
                    <Package className="h-6 w-6 text-blue-600" />
                  </div>
                  <span className={`text-2xl font-bold ${
                    stats.inventory.stock_health >= 70 ? 'text-green-600' :
                    stats.inventory.stock_health >= 40 ? 'text-yellow-600' :
                    'text-red-600'
                  }`}>
                    {stats.inventory.stock_health}%
                  </span>
                </div>
                <h3 className="text-gray-600 text-sm font-medium mb-1">Stock Health</h3>
                <p className="text-3xl font-bold text-gray-900">{stats.inventory.total_products}</p>
                <p className="text-sm text-gray-500 mt-2">Products in pantry</p>
                <div className="mt-4 grid grid-cols-4 gap-1 text-xs">
                  <div className="text-center">
                    <div className="font-bold text-green-600">{stats.inventory.full}</div>
                    <div className="text-gray-500">Full</div>
                  </div>
                  <div className="text-center">
                    <div className="font-bold text-blue-600">{stats.inventory.medium}</div>
                    <div className="text-gray-500">Med</div>
                  </div>
                  <div className="text-center">
                    <div className="font-bold text-orange-600">{stats.inventory.low}</div>
                    <div className="text-gray-500">Low</div>
                  </div>
                  <div className="text-center">
                    <div className="font-bold text-red-600">{stats.inventory.empty}</div>
                    <div className="text-gray-500">Empty</div>
                  </div>
                </div>
              </motion.div>

              {/* Shopping Progress */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-white rounded-2xl shadow-lg p-6 border-2 border-green-100 hover:shadow-xl transition-all"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="p-3 bg-green-100 rounded-xl">
                    <ShoppingCart className="h-6 w-6 text-green-600" />
                  </div>
                  <span className="text-2xl font-bold text-green-600">
                    {stats.shopping.completion_rate}%
                  </span>
                </div>
                <h3 className="text-gray-600 text-sm font-medium mb-1">Shopping Progress</h3>
                <p className="text-3xl font-bold text-gray-900">{stats.shopping.bought_items}/{stats.shopping.total_items}</p>
                <p className="text-sm text-gray-500 mt-2">Items completed</p>
                <div className="mt-4">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-gradient-to-r from-green-500 to-emerald-500 h-2 rounded-full transition-all"
                      style={{ width: `${stats.shopping.completion_rate}%` }}
                    />
                  </div>
                </div>
              </motion.div>

              {/* Weekly Spending */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-white rounded-2xl shadow-lg p-6 border-2 border-purple-100 hover:shadow-xl transition-all"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="p-3 bg-purple-100 rounded-xl">
                    <DollarSign className="h-6 w-6 text-purple-600" />
                  </div>
                  <span className="text-sm font-medium text-purple-600 bg-purple-50 px-2 py-1 rounded-full">
                    This Week
                  </span>
                </div>
                <h3 className="text-gray-600 text-sm font-medium mb-1">Total Spent</h3>
                <p className="text-3xl font-bold text-gray-900">${stats.activity.total_spent}</p>
                <p className="text-sm text-gray-500 mt-2">{stats.activity.total_receipts} receipts scanned</p>
                <div className="mt-4 flex items-center gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Purchases: </span>
                    <span className="font-semibold text-gray-900">{stats.activity.purchases_this_week}</span>
                  </div>
                </div>
              </motion.div>

              {/* Predictions */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="bg-white rounded-2xl shadow-lg p-6 border-2 border-orange-100 hover:shadow-xl transition-all"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="p-3 bg-orange-100 rounded-xl">
                    <AlertCircle className="h-6 w-6 text-orange-600" />
                  </div>
                  <span className={`text-2xl font-bold ${
                    stats.predictions.items_running_out === 0 ? 'text-green-600' :
                    stats.predictions.items_running_out < 5 ? 'text-yellow-600' :
                    'text-red-600'
                  }`}>
                    {stats.predictions.items_running_out}
                  </span>
                </div>
                <h3 className="text-gray-600 text-sm font-medium mb-1">Running Out Soon</h3>
                <p className="text-3xl font-bold text-gray-900">{stats.predictions.total_forecasts}</p>
                <p className="text-sm text-gray-500 mt-2">Items tracked</p>
                <div className="mt-4">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">AI Confidence</span>
                    <span className="font-semibold text-gray-900">{stats.predictions.avg_confidence}%</span>
                  </div>
                </div>
              </motion.div>
            </div>

            {/* Activity Summary */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="bg-white rounded-2xl shadow-lg p-6 mb-8 border border-gray-200"
            >
              <div className="flex items-center gap-3 mb-6">
                <Activity className="h-6 w-6 text-blue-600" />
                <h2 className="text-2xl font-bold text-gray-900">Recent Activity</h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-blue-50 rounded-xl">
                    <Calendar className="h-6 w-6 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900">{stats.activity.total_activities}</p>
                    <p className="text-sm text-gray-500">Total Actions</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-green-50 rounded-xl">
                    <CheckCircle className="h-6 w-6 text-green-600" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900">{stats.activity.purchases_this_week}</p>
                    <p className="text-sm text-gray-500">Purchases This Week</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-purple-50 rounded-xl">
                    <Clock className="h-6 w-6 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900">{stats.activity.adjustments_this_week}</p>
                    <p className="text-sm text-gray-500">Manual Adjustments</p>
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {quickActions.map((action, index) => {
              const Icon = action.icon
              return (
                <Link key={action.href} href={action.href}>
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.1 * index }}
                    whileHover={{ scale: 1.05, y: -5 }}
                    className={`${action.bgColor} rounded-2xl p-6 cursor-pointer transition-all shadow-md hover:shadow-xl border border-gray-100`}
                  >
                    <div className={`p-4 bg-gradient-to-br ${action.color} rounded-xl inline-block mb-4 shadow-lg`}>
                      <Icon className="h-8 w-8 text-white" />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">{action.title}</h3>
                    <p className="text-gray-600 text-sm">{action.description}</p>
                  </motion.div>
                </Link>
              )
            })}
          </div>
        </motion.div>
      </div>
    </DashboardLayout>
  )
}
