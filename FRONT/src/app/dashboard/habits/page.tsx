'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/useAuthStore'
import { DashboardLayout } from '@/components/layouts/DashboardLayout'
import { api } from '@/lib/api'
import { Users, ShoppingCart, Calendar, MessageSquare, Send, ChefHat, Sparkles, TrendingUp, Target, Trash2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface UserPreferences {
  household_size: number | null
  preferred_shopping_day: string | null
  shopping_frequency: string | null
  cooking_frequency: string | null
  dietary_preferences: string[]
  excluded_categories: string[]
  notes: string | null
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  extracted_data?: any
}

interface Habit {
  habit_id: string
  name: string | null
  explanation: string | null
  type: string
  status: string
  created_at: string
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: "easeOut"
    }
  }
}

export default function HabitsPage() {
  const router = useRouter()
  const { user, loading } = useAuthStore()
  const [preferences, setPreferences] = useState<UserPreferences>({
    household_size: null,
    preferred_shopping_day: null,
    shopping_frequency: null,
    cooking_frequency: null,
    dietary_preferences: [],
    excluded_categories: [],
    notes: null,
  })
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [chatLoading, setChatLoading] = useState(false)
  const [habits, setHabits] = useState<Habit[]>([])
  const [deletingHabitId, setDeletingHabitId] = useState<string | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  const dietaryOptions = [
    'Vegetarian',
    'Vegan',
    'Kosher',
    'Dairy',
    'Meat',
    'Gluten-Free',
    'Lactose-Free',
  ]

  const dayOptions = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

  const frequencyOptions = [
    { value: 'daily', label: 'Daily' },
    { value: 'weekly', label: 'Weekly' },
    { value: 'biweekly', label: 'Bi-weekly' },
    { value: 'monthly', label: 'Monthly' },
  ]

  const [foodCategories, setFoodCategories] = useState<string[]>([])

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  useEffect(() => {
    if (user) {
      loadPreferences()
      loadChatHistory()
      loadCategories()
      loadHabits()
    }
  }, [user])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  const loadCategories = async () => {
    try {
      const response = await api.get('/products/categories')
      if (response.data) {
        const categoryNames = response.data.map((cat: any) => cat.category_name)
        setFoodCategories(categoryNames)
      }
    } catch (error) {
      console.error('Error loading categories:', error)
      setFoodCategories([
        'Meat',
        'Poultry',
        'Fish',
        'Dairy',
        'Eggs',
        'Bread',
        'Pasta',
        'Rice',
        'Vegetables',
        'Fruits',
        'Sweets',
        'Beverages',
        'Nuts',
        'Legumes',
      ])
    }
  }

  const loadPreferences = async () => {
    try {
      const response = await api.get(`/habits/preferences`)
      if (response.data) {
        setPreferences({
          household_size: response.data.household_size || null,
          preferred_shopping_day: response.data.preferred_shopping_day || null,
          shopping_frequency: response.data.shopping_frequency || null,
          cooking_frequency: response.data.cooking_frequency || null,
          dietary_preferences: response.data.dietary_preferences || [],
          excluded_categories: response.data.excluded_categories || [],
          notes: response.data.notes || null,
        })
      }
    } catch (error: any) {
      // Silently fail if endpoint doesn't exist yet - backend might not be running
      if (error?.response?.status !== 404) {
        console.error('Error loading preferences:', error)
      }
    }
  }

  const loadChatHistory = async () => {
    try {
      const response = await api.get(`/habits/inputs`)
      if (response.data) {
        const messages: ChatMessage[] = []
        response.data.forEach((input: any) => {
          messages.push({
            id: input.habit_input_id,
            role: 'user',
            content: input.raw_text,
            timestamp: new Date(input.created_at),
            extracted_data: input.extracted_json,
          })
          if (input.extracted_json) {
            messages.push({
              id: `${input.habit_input_id}-response`,
              role: 'assistant',
              content: 'I\'ve updated your preferences based on the information you provided.',
              timestamp: new Date(input.created_at),
            })
          }
        })
        setChatMessages(messages)
      }
    } catch (error: any) {
      // Silently fail if endpoint doesn't exist yet - backend might not be running
      if (error?.response?.status !== 404) {
        console.error('Error loading chat history:', error)
      }
    }
  }

  const loadHabits = async () => {
    try {
      const response = await api.get('/habits')
      if (response.data) {
        // Filter to only show habits with names (created via AI assistant)
        const habitsWithNames = response.data.filter((habit: Habit) => habit.name)
        setHabits(habitsWithNames)
      }
    } catch (error: any) {
      if (error?.response?.status !== 404) {
        console.error('Error loading habits:', error)
      }
    }
  }

  const deleteHabit = async (habitId: string) => {
    if (!confirm('Are you sure you want to delete this habit? This will recalculate predictions for affected products.')) {
      return
    }

    setDeletingHabitId(habitId)
    try {
      await api.delete(`/habits/${habitId}`)
      // Reload habits after deletion
      await loadHabits()
    } catch (error: any) {
      console.error('Error deleting habit:', error)
      alert('Failed to delete habit. Please try again.')
    } finally {
      setDeletingHabitId(null)
    }
  }

  const savePreferences = async () => {
    if (!user) return
    setSaving(true)

    try {
      const habitData = {
        type: 'HOUSEHOLD',
        status: 'ACTIVE',
        params: {
          household_size: preferences.household_size,
          preferred_shopping_day: preferences.preferred_shopping_day,
          shopping_frequency: preferences.shopping_frequency,
          cooking_frequency: preferences.cooking_frequency,
          dietary_preferences: preferences.dietary_preferences,
          excluded_categories: preferences.excluded_categories,
          notes: preferences.notes,
        },
      }

      // Try to get existing habits, but if it fails, assume there are none
      let existingHabits = null
      try {
        const response = await api.get(`/habits?type=HOUSEHOLD`)
        existingHabits = response.data
      } catch (getError: any) {
        // If GET fails (404 or other), assume no existing habits and proceed with POST
        if (typeof window !== 'undefined') {
          console.log('No existing habits found, will create new one')
        }
        existingHabits = null
      }

      // If we have existing habits, update; otherwise create new
      if (existingHabits && existingHabits.length > 0) {
        await api.put(`/habits/${existingHabits[0].habit_id}`, habitData)
      } else {
        await api.post(`/habits`, habitData)
      }
      alert('Preferences saved successfully!')
    } catch (error: any) {
      console.error('Error saving preferences:', error)
      if (error?.response?.status === 404) {
        alert('Backend API endpoint not found. Please make sure the backend server is running and the habits router is loaded.')
      } else {
        alert(`Error saving preferences: ${error?.response?.data?.detail || error?.message || 'Unknown error'}`)
      }
    } finally {
      setSaving(false)
    }
  }

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!chatInput.trim() || !user) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: chatInput,
      timestamp: new Date(),
    }

    setChatMessages((prev) => [...prev, userMessage])
    setChatInput('')
    setChatLoading(true)

    try {
      const response = await api.post(`/habits/chat`, {
        message: chatInput,
      })

      const assistantMessage: ChatMessage = {
        id: `${Date.now()}-response`,
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date(),
        extracted_data: response.data.extracted_data,
      }

      setChatMessages((prev) => [...prev, assistantMessage])

      // Reload habits in case new ones were created
      await loadHabits()

      if (response.data.extracted_data) {
        const extracted = response.data.extracted_data
        setPreferences((prev) => ({
          ...prev,
          household_size: extracted.household_size ?? prev.household_size,
          preferred_shopping_day: extracted.preferred_shopping_day ?? prev.preferred_shopping_day,
          shopping_frequency: extracted.shopping_frequency ?? prev.shopping_frequency,
          cooking_frequency: extracted.cooking_frequency ?? prev.cooking_frequency,
          dietary_preferences: extracted.dietary_preferences
            ? [...new Set([...prev.dietary_preferences, ...extracted.dietary_preferences])]
            : prev.dietary_preferences,
          excluded_categories: extracted.excluded_categories
            ? [...new Set([...prev.excluded_categories, ...extracted.excluded_categories])]
            : prev.excluded_categories,
        }))
      }
    } catch (error) {
      console.error('Error sending chat message:', error)
      const errorMessage: ChatMessage = {
        id: `${Date.now()}-error`,
        role: 'assistant',
        content: 'Sorry, an error occurred. Please try again.',
        timestamp: new Date(),
      }
      setChatMessages((prev) => [...prev, errorMessage])
    } finally {
      setChatLoading(false)
    }
  }

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="relative"
        >
          <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
          <div className="absolute inset-0 flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-blue-600 animate-pulse" />
          </div>
        </motion.div>
      </div>
    )
  }

  return (
    <DashboardLayout>
      <motion.div
        initial="hidden"
        animate="visible"
        variants={containerVariants}
        className="px-4 py-6 sm:px-0"
      >
        <motion.div variants={itemVariants} className="mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 bg-clip-text text-transparent mb-2">
            Habits & Preferences
          </h1>
          <p className="text-gray-600">Customize your consumption patterns and dietary preferences</p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Household Info */}
          <motion.div
            variants={itemVariants}
            className="bg-white/90 backdrop-blur-lg rounded-2xl shadow-xl p-6 border border-white/20 hover:shadow-2xl transition-all duration-300"
          >
            <div className="flex items-center mb-6">
              <div className="p-3 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-xl shadow-lg">
                <Users className="h-6 w-6 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-gray-800 ml-3">Household Info</h2>
            </div>
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Number of People
                </label>
                <input
                  type="number"
                  min="1"
                  value={preferences.household_size || ''}
                  onChange={(e) =>
                    setPreferences({
                      ...preferences,
                      household_size: e.target.value ? parseInt(e.target.value) : null,
                    })
                  }
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all text-gray-900 placeholder:text-gray-400"
                  placeholder="Enter number"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Preferred Shopping Day
                </label>
                <select
                  value={preferences.preferred_shopping_day || ''}
                  onChange={(e) =>
                    setPreferences({ ...preferences, preferred_shopping_day: e.target.value || null })
                  }
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all text-gray-900"
                >
                  <option value="">Select day</option>
                  {dayOptions.map((day) => (
                    <option key={day} value={day}>
                      {day}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Shopping Frequency
                </label>
                <select
                  value={preferences.shopping_frequency || ''}
                  onChange={(e) =>
                    setPreferences({ ...preferences, shopping_frequency: e.target.value || null })
                  }
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all text-gray-900"
                >
                  <option value="">Select frequency</option>
                  {frequencyOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Cooking Frequency
                </label>
                <select
                  value={preferences.cooking_frequency || ''}
                  onChange={(e) =>
                    setPreferences({ ...preferences, cooking_frequency: e.target.value || null })
                  }
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all text-gray-900"
                >
                  <option value="">Select frequency</option>
                  {frequencyOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </motion.div>

          {/* Dietary Preferences */}
          <motion.div
            variants={itemVariants}
            className="bg-white/90 backdrop-blur-lg rounded-2xl shadow-xl p-6 border border-white/20 hover:shadow-2xl transition-all duration-300"
          >
            <div className="flex items-center mb-6">
              <div className="p-3 bg-gradient-to-br from-green-500 to-emerald-500 rounded-xl shadow-lg">
                <ShoppingCart className="h-6 w-6 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-gray-800 ml-3">Dietary Preferences</h2>
            </div>
            <div className="space-y-3 mb-6">
              {dietaryOptions.map((pref) => (
                <motion.label
                  key={pref}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="flex items-center cursor-pointer group"
                >
                  <input
                    type="checkbox"
                    checked={preferences.dietary_preferences.includes(pref)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setPreferences({
                          ...preferences,
                          dietary_preferences: [...preferences.dietary_preferences, pref],
                        })
                      } else {
                        setPreferences({
                          ...preferences,
                          dietary_preferences: preferences.dietary_preferences.filter((p) => p !== pref),
                        })
                      }
                    }}
                    className="ml-3 h-5 w-5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded cursor-pointer"
                  />
                  <span className="text-sm font-medium text-gray-700 group-hover:text-blue-600 transition-colors">{pref}</span>
                </motion.label>
              ))}
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-3">
                Excluded Food Categories
              </label>
              <div className="space-y-2 max-h-48 overflow-y-auto custom-scrollbar">
                {foodCategories.map((category) => (
                  <motion.label
                    key={category}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="flex items-center cursor-pointer group"
                  >
                    <input
                      type="checkbox"
                      checked={preferences.excluded_categories.includes(category)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setPreferences({
                            ...preferences,
                            excluded_categories: [...preferences.excluded_categories, category],
                          })
                        } else {
                          setPreferences({
                            ...preferences,
                            excluded_categories: preferences.excluded_categories.filter((c) => c !== category),
                          })
                        }
                      }}
                      className="ml-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded cursor-pointer"
                    />
                    <span className="text-sm text-gray-700 group-hover:text-blue-600 transition-colors">{category}</span>
                  </motion.label>
                ))}
              </div>
            </div>
          </motion.div>

          {/* AI-Created Habits List */}
          <motion.div
            variants={itemVariants}
            className="bg-white/90 backdrop-blur-lg rounded-2xl shadow-xl p-6 lg:col-span-2 border border-white/20 hover:shadow-2xl transition-all duration-300"
          >
            <div className="flex items-center mb-4">
              <div className="p-3 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-xl shadow-lg">
                <Target className="h-6 w-6 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-gray-800 ml-3">AI-Created Habits</h2>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Habits created via the AI Assistant. Deleting a habit will recalculate predictions for affected products.
            </p>

            {habits.length === 0 ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-center text-gray-500 py-8"
              >
                <Target className="h-12 w-12 mx-auto mb-2 text-gray-400" />
                <p>No habits added yet. Use the AI Assistant below to create habits!</p>
              </motion.div>
            ) : (
              <div className="space-y-3">
                <AnimatePresence>
                  {habits.map((habit) => (
                    <motion.div
                      key={habit.habit_id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      className="flex items-center justify-between p-4 bg-gradient-to-r from-gray-50 to-white rounded-xl border-2 border-gray-200 hover:border-indigo-300 hover:shadow-md transition-all duration-200"
                    >
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-gray-800 mb-1">
                          {habit.name || 'Unnamed Habit'}
                        </h3>
                        {habit.explanation && (
                          <p className="text-sm text-gray-600 line-clamp-2">
                            {habit.explanation}
                          </p>
                        )}
                      </div>
                      <motion.button
                        onClick={() => deleteHabit(habit.habit_id)}
                        disabled={deletingHabitId === habit.habit_id}
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        className="ml-4 p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Delete habit"
                      >
                        {deletingHabitId === habit.habit_id ? (
                          <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                            className="w-5 h-5 border-2 border-red-500 border-t-transparent rounded-full"
                          />
                        ) : (
                          <Trash2 className="h-5 w-5" />
                        )}
                      </motion.button>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            )}
          </motion.div>

          {/* Chat with LLM */}
          <motion.div
            variants={itemVariants}
            className="bg-white/90 backdrop-blur-lg rounded-2xl shadow-xl p-6 lg:col-span-2 border border-white/20 hover:shadow-2xl transition-all duration-300"
          >
            <div className="flex items-center mb-4">
              <div className="p-3 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl shadow-lg">
                <MessageSquare className="h-6 w-6 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-gray-800 ml-3">AI Assistant</h2>
              <div className="ml-auto flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-purple-500 animate-pulse" />
                <span className="text-sm text-gray-500">Powered by AI</span>
              </div>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Tell me about your habits and preferences, and I'll update the information automatically
            </p>

            {/* Chat Messages */}
            <div className="border-2 border-gray-200 rounded-xl p-4 mb-4 h-64 overflow-y-auto bg-gradient-to-b from-gray-50 to-white custom-scrollbar">
              <AnimatePresence>
                {chatMessages.length === 0 ? (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="text-center text-gray-500 py-8"
                  >
                    <MessageSquare className="h-12 w-12 mx-auto mb-2 text-gray-400" />
                    <p>No messages yet. Start a conversation!</p>
                  </motion.div>
                ) : (
                  <div className="space-y-4">
                    {chatMessages.map((message, index) => (
                      <motion.div
                        key={message.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[80%] rounded-2xl p-4 shadow-lg ${
                            message.role === 'user'
                              ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white'
                              : 'bg-white text-gray-800 border-2 border-gray-200'
                          }`}
                        >
                          <p className="text-sm">{message.content}</p>
                          {message.extracted_data && (
                            <div className="mt-2 pt-2 border-t border-gray-300 text-xs opacity-75">
                              Detected: {JSON.stringify(message.extracted_data)}
                            </div>
                          )}
                        </div>
                      </motion.div>
                    ))}
                    {chatLoading && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="flex justify-start"
                      >
                        <div className="bg-white border-2 border-gray-200 rounded-2xl p-4 shadow-lg">
                          <div className="flex space-x-2">
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                          </div>
                        </div>
                      </motion.div>
                    )}
                    <div ref={chatEndRef} />
                  </div>
                )}
              </AnimatePresence>
            </div>

            {/* Chat Input */}
            <form onSubmit={handleChatSubmit} className="flex gap-3">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Type here... e.g., 'We are 4 people at home, eat kosher, don't eat meat'"
                className="flex-1 px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all text-gray-900 placeholder:text-gray-400"
                disabled={chatLoading}
              />
              <motion.button
                type="submit"
                disabled={chatLoading || !chatInput.trim()}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-6 py-3 rounded-xl hover:from-blue-600 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center shadow-lg"
              >
                <Send className="h-5 w-5 ml-2" />
                Send
              </motion.button>
            </form>
          </motion.div>

          {/* Save Button */}
          <motion.div
            variants={itemVariants}
            className="lg:col-span-2 flex justify-end"
          >
            <motion.button
              onClick={savePreferences}
              disabled={saving}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-10 py-4 rounded-xl hover:from-blue-600 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 flex items-center text-lg font-semibold shadow-xl"
            >
              {saving ? (
                <>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    className="w-5 h-5 border-2 border-white border-t-transparent rounded-full ml-2"
                  />
                  Saving...
                </>
              ) : (
                <>
                  <TrendingUp className="h-5 w-5 ml-2" />
                  Save Preferences
                </>
              )}
            </motion.button>
          </motion.div>
        </div>
      </motion.div>
    </DashboardLayout>
  )
}
