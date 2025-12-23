'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/useAuthStore'
import { DashboardLayout } from '@/components/layouts/DashboardLayout'
import { api } from '@/lib/api'

interface UserProfile {
  household_size: number
  shopping_frequency: string
  dietary_preferences: string[]
  shopping_days: string[]
  notes: string
}

export default function UserProfilePage() {
  const router = useRouter()
  const { user, loading } = useAuthStore()
  const [formData, setFormData] = useState<UserProfile>({
    household_size: 1,
    shopping_frequency: 'weekly',
    dietary_preferences: [],
    shopping_days: [],
    notes: '',
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  const dietaryOptions = [
    'צמחונות',
    'טבעונות',
    'כשר',
    'חלבי',
    'בשרי',
    'ללא גלוטן',
    'ללא לקטוז',
  ]

  const dayOptions = [
    'ראשון',
    'שני',
    'שלישי',
    'רביעי',
    'חמישי',
    'שישי',
    'שבת',
  ]

  const handleDietaryChange = (pref: string) => {
    setFormData((prev) => ({
      ...prev,
      dietary_preferences: prev.dietary_preferences.includes(pref)
        ? prev.dietary_preferences.filter((p) => p !== pref)
        : [...prev.dietary_preferences, pref],
    }))
  }

  const handleDayChange = (day: string) => {
    setFormData((prev) => ({
      ...prev,
      shopping_days: prev.shopping_days.includes(day)
        ? prev.shopping_days.filter((d) => d !== day)
        : [...prev.shopping_days, day],
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)

    try {
      // Save to habits table via API
      if (user) {
        // This will be implemented when we add habits API
        if (typeof window !== 'undefined') {
          console.log('Saving profile:', formData)
        }
        router.push('/dashboard')
      }
    } catch (error) {
      console.error('Error saving profile:', error)
    } finally {
      setSaving(false)
    }
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
        <h1 className="text-3xl font-bold text-gray-900 mb-6">
          הגדרות משתמש
        </h1>

        <form onSubmit={handleSubmit} className="bg-white shadow rounded-lg p-6">
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                כמות אנשים בבית
              </label>
              <input
                type="number"
                min="1"
                value={formData.household_size}
                onChange={(e) =>
                  setFormData({ ...formData, household_size: parseInt(e.target.value) })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 placeholder:text-gray-400"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                תדירות קניות
              </label>
              <select
                value={formData.shopping_frequency}
                onChange={(e) =>
                  setFormData({ ...formData, shopping_frequency: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 placeholder:text-gray-400"
              >
                <option value="daily">יומי</option>
                <option value="weekly">שבועי</option>
                <option value="biweekly">דו-שבועי</option>
                <option value="monthly">חודשי</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                העדפות תזונתיות
              </label>
              <div className="grid grid-cols-2 gap-2">
                {dietaryOptions.map((pref) => (
                  <label key={pref} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.dietary_preferences.includes(pref)}
                      onChange={() => handleDietaryChange(pref)}
                      className="ml-2 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                    />
                    <span className="text-sm text-gray-700">{pref}</span>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                ימי קניות מועדפים
              </label>
              <div className="grid grid-cols-4 gap-2">
                {dayOptions.map((day) => (
                  <label key={day} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.shopping_days.includes(day)}
                      onChange={() => handleDayChange(day)}
                      className="ml-2 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                    />
                    <span className="text-sm text-gray-700">{day}</span>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                הערות נוספות
              </label>
              <textarea
                value={formData.notes}
                onChange={(e) =>
                  setFormData({ ...formData, notes: e.target.value })
                }
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 placeholder:text-gray-400"
                placeholder="מידע נוסף שיכול לעזור למערכת..."
              />
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={saving}
                className="bg-primary-600 text-white px-6 py-2 rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
              >
                {saving ? 'שומר...' : 'שמור והמשך'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </DashboardLayout>
  )
}

