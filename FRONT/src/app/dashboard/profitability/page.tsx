'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/useAuthStore'
import { DashboardLayout } from '@/components/layouts/DashboardLayout'
import { api } from '@/lib/api'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { TrendingUp, DollarSign, ShoppingBag, Calendar } from 'lucide-react'

export default function ProfitabilityPage() {
  const router = useRouter()
  const { user, loading } = useAuthStore()
  const [timeRange, setTimeRange] = useState<'week' | 'month' | 'quarter' | 'half-year'>('week')
  const [chartType, setChartType] = useState<'line' | 'bar'>('line')
  const [data, setData] = useState<any[]>([])

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  useEffect(() => {
    if (user) {
      loadData()
    }
  }, [user, timeRange])

  const loadData = async () => {
    try {
      // Load receipts data for analysis
      const response = await api.get(`/receipts?limit=100`)
      const receipts = response.data

      // Process data for charts
      const processedData = processReceiptData(receipts)
      setData(processedData)
    } catch (error) {
      console.error('Error loading data:', error)
    }
  }

  const processReceiptData = (receipts: any[]) => {
    // Group by week/month and calculate totals
    const grouped: { [key: string]: { total: number; count: number } } = {}

    receipts.forEach((receipt) => {
      const date = new Date(receipt.purchased_at || receipt.created_at)
      let key = ''

      if (timeRange === 'week') {
        const weekStart = new Date(date)
        weekStart.setDate(date.getDate() - date.getDay())
        key = weekStart.toLocaleDateString('he-IL', { month: 'short', day: 'numeric' })
      } else if (timeRange === 'month') {
        key = date.toLocaleDateString('he-IL', { month: 'long', year: 'numeric' })
      } else {
        key = date.toLocaleDateString('he-IL', { month: 'short', year: 'numeric' })
      }

      if (!grouped[key]) {
        grouped[key] = { total: 0, count: 0 }
      }

      grouped[key].total += receipt.total_amount || 0
      grouped[key].count += 1
    })

    return Object.entries(grouped)
      .map(([name, values]) => ({
        name,
        סכום: values.total.toFixed(2),
        כמות_קניות: values.count,
      }))
      .sort((a, b) => a.name.localeCompare(b.name))
  }

  const stats = {
    totalSpent: data.reduce((sum, item) => sum + parseFloat(item.סכום), 0),
    avgPerTrip: data.length > 0
      ? data.reduce((sum, item) => sum + parseFloat(item.סכום), 0) / data.length
      : 0,
    totalTrips: data.reduce((sum, item) => sum + item.כמות_קניות, 0),
  }

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <DashboardLayout>
      <div className="px-4 py-6 sm:px-0">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">רווחיות וניתוחים</h1>
          <div className="flex space-x-2 space-x-reverse">
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as any)}
              className="px-4 py-2 border border-gray-300 rounded-md"
            >
              <option value="week">שבוע</option>
              <option value="month">חודש</option>
              <option value="quarter">רבעון</option>
              <option value="half-year">חצי שנה</option>
            </select>
            <select
              value={chartType}
              onChange={(e) => setChartType(e.target.value as any)}
              className="px-4 py-2 border border-gray-300 rounded-md"
            >
              <option value="line">קו</option>
              <option value="bar">עמודות</option>
            </select>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">סה"כ הוצאות</p>
                <p className="text-2xl font-bold text-gray-900">
                  ₪{stats.totalSpent.toFixed(2)}
                </p>
              </div>
              <DollarSign className="h-8 w-8 text-primary-600" />
            </div>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">ממוצע לקנייה</p>
                <p className="text-2xl font-bold text-gray-900">
                  ₪{stats.avgPerTrip.toFixed(2)}
                </p>
              </div>
              <ShoppingBag className="h-8 w-8 text-primary-600" />
            </div>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">סה"כ קניות</p>
                <p className="text-2xl font-bold text-gray-900">{stats.totalTrips}</p>
              </div>
              <Calendar className="h-8 w-8 text-primary-600" />
            </div>
          </div>
        </div>

        {/* Charts */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">גרף הוצאות</h2>
          <ResponsiveContainer width="100%" height={300}>
            {chartType === 'line' ? (
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="סכום" stroke="#0ea5e9" />
              </LineChart>
            ) : (
              <BarChart data={data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="סכום" fill="#0ea5e9" />
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>

        {/* Recommendations */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center mb-4">
            <TrendingUp className="h-5 w-5 text-primary-600 ml-2" />
            <h2 className="text-xl font-semibold">המלצות</h2>
          </div>
          <div className="space-y-2">
            <p className="text-gray-700">
              • הוצאות השבוע נמוכות ב-15% מהממוצע - מעולה!
            </p>
            <p className="text-gray-700">
              • מומלץ לקנות בימי ראשון-שלישי להנחות טובות יותר
            </p>
            <p className="text-gray-700">
              • חנויות מומלצות: סופר פארם, שופרסל
            </p>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}

