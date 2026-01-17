'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuthStore } from '@/store/useAuthStore'
import { DashboardLayout } from '@/components/layouts/DashboardLayout'
import { api } from '@/lib/api'
import { 
  Check, 
  X, 
  Plus, 
  ShoppingBag, 
  Clock, 
  ChevronUp, 
  ChevronDown,
  Edit2,
  Trash2,
  TrendingUp
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface Product {
  product_id: string
  product_name: string
  category_name?: string
}

interface ShoppingItem {
  shopping_list_item_id: string
  product_id: string | null
  free_text_name: string | null
  recommended_qty: number | null
  unit: string | null
  user_qty_override: number | null
  status: string
  products?: Product
  durationDays?: number
  sufficiency_marked?: boolean
  actual_qty_purchased?: number | null
  qty_feedback?: string | null
  prediction?: {
    predicted_days_left: number
    predicted_state: string
    confidence: number
    recommended_qty?: number
    will_sufficient?: boolean
    will_last_days?: number
  }
}

export default function ShoppingActivePage() {
  // Toggle for prediction UI messages - set to false to hide, true to show
  const SHOW_PREDICTION_UI = false

  const router = useRouter()
  const searchParams = useSearchParams()
  const { user, loading } = useAuthStore()
  const listId = searchParams.get('list_id')
  const [items, setItems] = useState<ShoppingItem[]>([])
  const [loadingItems, setLoadingItems] = useState(true)
  const [showFinishDialog, setShowFinishDialog] = useState(false)
  const [unboughtItems, setUnboughtItems] = useState<ShoppingItem[]>([])
  const [selectedUnboughtIds, setSelectedUnboughtIds] = useState<Set<string>>(new Set())
  const [showAddItem, setShowAddItem] = useState(false)
  const [newItemText, setNewItemText] = useState('')
  const [shoppingFrequency, setShoppingFrequency] = useState(7) // Default 7 days
  const [sufficiencyMarked, setSufficiencyMarked] = useState<{ [key: string]: boolean }>({})
  const [actualQtyPurchased, setActualQtyPurchased] = useState<{ [key: string]: number | null }>({})
  const [qtyFeedback, setQtyFeedback] = useState<{ [key: string]: string }>({})

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  useEffect(() => {
    if (user && listId) {
      loadItems()
      loadUserPreferences()
    }
  }, [user, listId])

  const loadUserPreferences = async () => {
    try {
      const response = await api.get(`/habits/preferences`)
      if (response.data?.shopping_frequency) {
        // Parse shopping frequency (e.g., "WEEKLY" -> 7 days)
        const freq = response.data.shopping_frequency
        if (freq === 'WEEKLY') setShoppingFrequency(7)
        else if (freq === 'BI_WEEKLY') setShoppingFrequency(14)
        else if (freq === 'MONTHLY') setShoppingFrequency(30)
      }
    } catch (error) {
      console.error('Error loading user preferences:', error)
    }
  }

  const loadItems = async () => {
    try {
      setLoadingItems(true)
      const response = await api.get(`/shopping-lists/${listId}/items`)
      // Restore feedback state from loaded items
      const itemsWithState = response.data.map((item: ShoppingItem) => {
        // Restore feedback state from loaded item
        if (item.sufficiency_marked !== undefined) {
          setSufficiencyMarked(prev => ({ ...prev, [item.shopping_list_item_id]: item.sufficiency_marked! }))
        }
        if (item.actual_qty_purchased !== undefined && item.actual_qty_purchased !== null) {
          setActualQtyPurchased(prev => ({ ...prev, [item.shopping_list_item_id]: item.actual_qty_purchased! }))
        }
        if (item.qty_feedback) {
          setQtyFeedback(prev => ({ ...prev, [item.shopping_list_item_id]: item.qty_feedback! }))
        }
        return item
      })
      setItems(itemsWithState)
    } catch (error) {
      console.error('Error loading items:', error)
    } finally {
      setLoadingItems(false)
    }
  }

  const toggleItem = async (item: ShoppingItem) => {
    const newStatus = item.status === 'BOUGHT' ? 'PLANNED' : 'BOUGHT'
    try {
      const updateData: any = { status: newStatus }
      
      // If marking as BOUGHT, include feedback if available
      if (newStatus === 'BOUGHT') {
        const itemId = item.shopping_list_item_id
        if (sufficiencyMarked[itemId] !== undefined) {
          updateData.sufficiency_marked = sufficiencyMarked[itemId]
        }
        if (actualQtyPurchased[itemId] !== undefined) {
          updateData.actual_qty_purchased = actualQtyPurchased[itemId]
        }
        if (qtyFeedback[itemId]) {
          updateData.qty_feedback = qtyFeedback[itemId]
        }
      }
      
      await api.put(`/shopping-lists/items/${item.shopping_list_item_id}`, updateData)
      await loadItems()
    } catch (error) {
      console.error('Error updating item:', error)
    }
  }
  
  const handleSufficiencyToggle = (itemId: string, isSufficient: boolean) => {
    setSufficiencyMarked(prev => ({ ...prev, [itemId]: isSufficient }))
    if (!isSufficient) {
      // If not sufficient, clear feedback (user will set it)
      setQtyFeedback(prev => {
        const next = { ...prev }
        delete next[itemId]
        return next
      })
    }
  }
  
  const handleQtyFeedback = (itemId: string, feedback: string) => {
    setQtyFeedback(prev => ({ ...prev, [itemId]: feedback }))
  }
  
  const handleActualQtyChange = (itemId: string, qty: number | null) => {
    setActualQtyPurchased(prev => ({ ...prev, [itemId]: qty }))
  }

  const updateQuantity = async (itemId: string, quantity: number) => {
    try {
      await api.put(`/shopping-lists/items/${itemId}`, {
        user_qty_override: quantity,
      })
      await loadItems()
    } catch (error) {
      console.error('Error updating quantity:', error)
    }
  }

  const adjustDuration = async (itemId: string, productId: string | null, increase: boolean) => {
    if (!productId) {
      // If no product_id, can't update days_left
      return
    }
    
    try {
      // Update days_left through feedback API (similar to MORE/LESS)
      const feedback = increase ? 'MORE' : 'LESS'
      
      // First update the shopping list item
      await api.put(`/shopping-lists/items/${itemId}`, {
        qty_feedback: feedback,
      })
      
      // Then update the model
      await api.post(`/predictor/learn-from-shopping-feedback`, {
        shopping_list_item_id: itemId,
        product_id: productId,
        feedback: feedback
      })
      
      // Reload items to get updated prediction
      await loadItems()
    } catch (error) {
      console.error('Error adjusting days_left:', error)
    }
  }

  const addNewItem = async () => {
    if (!newItemText.trim()) return
    
    try {
      await api.post(`/shopping-lists/${listId}/items`, {
        free_text_name: newItemText.trim(),
        status: 'PLANNED',
        added_by: 'USER',
      })
      setNewItemText('')
      setShowAddItem(false)
      await loadItems()
    } catch (error) {
      console.error('Error adding item:', error)
    }
  }

  const handleFinishShopping = () => {
    const unbought = items.filter((item) => item.status !== 'BOUGHT')
    setUnboughtItems(unbought)
    setSelectedUnboughtIds(new Set(unbought.map((item) => item.shopping_list_item_id)))
    setShowFinishDialog(true)
  }

  const toggleUnboughtSelection = (itemId: string) => {
    setSelectedUnboughtIds((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(itemId)) {
        newSet.delete(itemId)
      } else {
        newSet.add(itemId)
      }
      return newSet
    })
  }

  const handleCompleteShopping = async () => {
    try {
      // Complete shopping list - this will update inventory to FULL and update predictor model
      const response = await api.post(`/shopping-lists/${listId}/complete`)
      
      // Show success message with details
      const inventoryUpdates = response.data?.inventory_updates || []
      if (inventoryUpdates.length > 0) {
        const productNames = inventoryUpdates.map((item: any) => item.product_name).join(', ')
        alert(`✅ Successfully added ${inventoryUpdates.length} item(s) to pantry: ${productNames}`)
      } else {
        alert('⚠️ No items were added to pantry. Make sure you marked items as "BOUGHT" before completing shopping.')
      }

      // If there are selected unbought items, create a new list for next time
      if (selectedUnboughtIds.size > 0) {
        const nextListResponse = await api.post(`/shopping-lists`, {
          title: `Next Shopping List - ${new Date().toLocaleDateString('en-US')}`,
          status: 'ACTIVE',
        })

        const nextListId = nextListResponse.data.shopping_list_id

        // Add selected items to the next list
        const selectedItems = Array.from(selectedUnboughtIds)
        for (const itemId of selectedItems) {
          const item = unboughtItems.find((i) => i.shopping_list_item_id === itemId)
          if (item) {
            await api.post(`/shopping-lists/${nextListId}/items`, {
              product_id: item.product_id || null,
              free_text_name: item.free_text_name || null,
              recommended_qty: item.recommended_qty,
              unit: item.unit,
              status: 'PLANNED',
              added_by: 'SYSTEM',
            })
          }
        }
      }

      // Redirect to pantry page to see the updated inventory
      router.push('/dashboard/pantry')
    } catch (error) {
      console.error('Error completing shopping:', error)
      alert('Error completing shopping. Please try again.')
    }
  }

  const boughtCount = items.filter((item) => item.status === 'BOUGHT').length
  const totalCount = items.length
  const progress = totalCount > 0 ? (boughtCount / totalCount) * 100 : 0

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <DashboardLayout>
      <div className="px-4 py-6 sm:px-0 max-w-5xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-bold text-gray-900 mb-3 flex items-center gap-3">
            <ShoppingBag className="h-10 w-10 text-green-600" />
            Active Shopping
          </h1>
          <p className="text-gray-600">Check off items as you shop</p>
        </motion.div>

        {/* Progress Bar */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-white shadow-xl rounded-2xl p-6 mb-6 border border-gray-200"
        >
          <div className="flex justify-between items-center mb-3">
            <span className="text-lg font-semibold text-gray-900">Shopping Progress</span>
            <span className="text-sm font-medium text-gray-600">
              {boughtCount} / {totalCount} items
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5 }}
              className="bg-gradient-to-r from-green-500 to-emerald-500 h-full rounded-full"
            />
          </div>
        </motion.div>

        {loadingItems ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <>
            {/* Items List */}
            <div className="bg-white shadow-xl rounded-2xl p-6 mb-6 border border-gray-200">
              <div className="space-y-3">
                {items.length === 0 ? (
                  <div className="text-center py-12">
                    <ShoppingBag className="h-16 w-16 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500">No items in your list</p>
                  </div>
                ) : (
                  items.map((item) => (
                    <motion.div
                      key={item.shopping_list_item_id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      className={`p-4 rounded-xl border-2 transition-all ${
                        item.status === 'BOUGHT'
                          ? 'bg-green-50 border-green-300'
                          : 'bg-white border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-start gap-4">
                        {/* Checkbox */}
                        <button
                          onClick={() => toggleItem(item)}
                          className={`mt-1 w-7 h-7 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all ${
                            item.status === 'BOUGHT'
                              ? 'bg-green-500 border-green-500 scale-110'
                              : 'border-gray-400 hover:border-green-500'
                          }`}
                        >
                          {item.status === 'BOUGHT' && (
                            <Check className="h-5 w-5 text-white font-bold" />
                          )}
                        </button>

                        {/* Item Info */}
                        <div className="flex-1">
                          <div className="flex justify-between items-start mb-2">
                            <div>
                              <p
                                className={`font-semibold text-lg ${
                                  item.status === 'BOUGHT'
                                    ? 'line-through text-gray-500'
                                    : 'text-gray-900'
                                }`}
                              >
                                {item.products?.product_name || item.free_text_name}
                              </p>
                              {item.products?.category_name && (
                                <p className="text-sm text-gray-500">{item.products.category_name}</p>
                              )}
                            </div>

                          </div>

                          {/* Model Prediction - Simple Display */}
                          {SHOW_PREDICTION_UI && item.prediction && item.product_id && item.prediction.will_last_days && (
                            <div className="mt-3 p-3 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
                              <div className="flex items-center justify-between">
                                <span className="text-sm font-semibold text-gray-700">
                                  It's for {Math.round(item.prediction.will_last_days)} days
                                </span>
                              </div>
                            </div>
                          )}

                          {/* Days Prediction Feedback (for items with product_id) */}
                          {SHOW_PREDICTION_UI && item.product_id && item.status !== 'BOUGHT' && item.prediction?.will_last_days && (
                            <div className="mt-3 p-3 bg-purple-50 rounded-lg border border-purple-200">
                              <div className="flex items-center justify-between gap-3">
                                <span className="text-sm font-medium text-gray-700">
                                  Will this last:
                                </span>
                                <div className="flex gap-2">
                                  <button
                                    onClick={async () => {
                                      // "Will last more" = consumption is slower, cycle_mean_days should increase
                                      handleQtyFeedback(item.shopping_list_item_id, 'MORE')
                                      handleSufficiencyToggle(item.shopping_list_item_id, true)
                                      // Update immediately to save feedback
                                      try {
                                        await api.put(`/shopping-lists/items/${item.shopping_list_item_id}`, {
                                          qty_feedback: 'MORE',
                                          sufficiency_marked: true
                                        })
                                        // Trigger model update immediately
                                        await api.post(`/predictor/learn-from-shopping-feedback`, {
                                          shopping_list_item_id: item.shopping_list_item_id,
                                          feedback: 'MORE'
                                        })
                                      } catch (error) {
                                        console.error('Error saving feedback:', error)
                                      }
                                    }}
                                    className={`px-4 py-2 text-sm rounded-lg transition-colors font-medium ${
                                      qtyFeedback[item.shopping_list_item_id] === 'MORE' || sufficiencyMarked[item.shopping_list_item_id]
                                        ? 'bg-green-500 text-white'
                                        : 'bg-green-100 text-green-700 hover:bg-green-200'
                                    }`}
                                  >
                                    Will Last More
                                  </button>
                                  <button
                                    onClick={async () => {
                                      // "Will last less" = consumption is faster, cycle_mean_days should decrease
                                      handleQtyFeedback(item.shopping_list_item_id, 'LESS')
                                      handleSufficiencyToggle(item.shopping_list_item_id, false)
                                      // Update immediately to save feedback
                                      try {
                                        await api.put(`/shopping-lists/items/${item.shopping_list_item_id}`, {
                                          qty_feedback: 'LESS',
                                          sufficiency_marked: false
                                        })
                                        // Trigger model update immediately
                                        await api.post(`/predictor/learn-from-shopping-feedback`, {
                                          shopping_list_item_id: item.shopping_list_item_id,
                                          feedback: 'LESS'
                                        })
                                      } catch (error) {
                                        console.error('Error saving feedback:', error)
                                      }
                                    }}
                                    className={`px-4 py-2 text-sm rounded-lg transition-colors font-medium ${
                                      qtyFeedback[item.shopping_list_item_id] === 'LESS' || (!sufficiencyMarked[item.shopping_list_item_id] && qtyFeedback[item.shopping_list_item_id])
                                        ? 'bg-red-500 text-white'
                                        : 'bg-red-100 text-red-700 hover:bg-red-200'
                                    }`}
                                  >
                                    Will Last Less
                                  </button>
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Days Left Indicator (for items with product_id and prediction) */}
                          {SHOW_PREDICTION_UI && item.status === 'BOUGHT' && item.product_id && item.prediction?.predicted_days_left !== undefined && (
                            <div className="flex items-center gap-3 mt-3 p-3 bg-blue-50 rounded-lg">
                              <Clock className="h-5 w-5 text-blue-600" />
                              <div className="flex-1">
                                <p className="text-sm font-medium text-gray-700">
                                  Estimated days left: {Math.round(item.prediction.predicted_days_left * 10) / 10} days
                                </p>
                              </div>
                              <div className="flex gap-2">
                                <button
                                  onClick={() => adjustDuration(item.shopping_list_item_id, item.product_id, false)}
                                  className="p-1 rounded-lg bg-orange-100 hover:bg-orange-200 text-orange-600"
                                  title="Decrease days left"
                                >
                                  <ChevronDown className="h-5 w-5" />
                                </button>
                                <button
                                  onClick={() => adjustDuration(item.shopping_list_item_id, item.product_id, true)}
                                  className="p-1 rounded-lg bg-green-100 hover:bg-green-200 text-green-600"
                                  title="Increase days left"
                                >
                                  <ChevronUp className="h-5 w-5" />
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  ))
                )}
              </div>

              {/* Add Item Button */}
              {!showAddItem ? (
                <button
                  onClick={() => setShowAddItem(true)}
                  className="w-full mt-4 py-3 border-2 border-dashed border-gray-300 rounded-xl text-gray-600 hover:border-blue-500 hover:text-blue-600 transition-all flex items-center justify-center gap-2"
                >
                  <Plus className="h-5 w-5" />
                  Add Item
                </button>
              ) : (
                <div className="mt-4 flex gap-2">
                  <input
                    type="text"
                    value={newItemText}
                    onChange={(e) => setNewItemText(e.target.value)}
                    placeholder="Item name..."
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        addNewItem()
                      }
                    }}
                    className="flex-1 px-4 py-3 border-2 border-blue-500 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                    autoFocus
                  />
                  <button
                    onClick={addNewItem}
                    className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700"
                  >
                    <Check className="h-5 w-5" />
                  </button>
                  <button
                    onClick={() => {
                      setShowAddItem(false)
                      setNewItemText('')
                    }}
                    className="px-6 py-3 bg-gray-200 text-gray-700 rounded-xl hover:bg-gray-300"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              )}
            </div>

            {/* Finish Shopping Button */}
            <div className="flex justify-end">
              <button
                onClick={handleFinishShopping}
                className="bg-gradient-to-r from-green-600 to-emerald-600 text-white px-8 py-4 rounded-xl hover:from-green-700 hover:to-emerald-700 flex items-center gap-3 text-lg font-semibold shadow-xl hover:shadow-2xl transition-all"
              >
                <ShoppingBag className="h-6 w-6" />
                Finish Shopping
              </button>
            </div>
          </>
        )}

        {/* Finish Dialog */}
        <AnimatePresence>
          {showFinishDialog && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
              onClick={() => setShowFinishDialog(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl"
                onClick={(e) => e.stopPropagation()}
              >
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  Items You Didn't Buy
                </h2>
                
                {unboughtItems.length === 0 ? (
                  <div className="text-center py-8">
                    <Check className="h-16 w-16 text-green-500 mx-auto mb-3" />
                    <p className="text-gray-600">You bought everything!</p>
                  </div>
                ) : (
                  <>
                    <p className="text-gray-600 mb-4">
                      Would you like to add these items to your next shopping list?
                    </p>
                    <div className="space-y-2 max-h-60 overflow-y-auto mb-6">
                      {unboughtItems.map((item) => (
                        <label
                          key={item.shopping_list_item_id}
                          className="flex items-center p-3 hover:bg-gray-50 rounded-lg cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={selectedUnboughtIds.has(item.shopping_list_item_id)}
                            onChange={() => toggleUnboughtSelection(item.shopping_list_item_id)}
                            className="w-5 h-5 text-blue-600 rounded"
                          />
                          <span className="ml-3 text-gray-900">
                            {item.products?.product_name || item.free_text_name}
                          </span>
                        </label>
                      ))}
                    </div>
                  </>
                )}

                <div className="flex gap-3">
                  <button
                    onClick={() => setShowFinishDialog(false)}
                    className="flex-1 px-4 py-3 border-2 border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleCompleteShopping}
                    className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 font-medium"
                  >
                    Complete
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </DashboardLayout>
  )
}
