'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/useAuthStore'
import { DashboardLayout } from '@/components/layouts/DashboardLayout'
import { api } from '@/lib/api'
import { 
  ShoppingCart, 
  Plus, 
  ArrowRight, 
  ChefHat, 
  Calendar, 
  Clock, 
  Edit2, 
  Trash2,
  Check,
  X,
  Package
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface Product {
  product_id: string
  product_name: string
  category_name?: string
}

interface ShoppingListItem {
  shopping_list_item_id: string
  product_id: string | null
  free_text_name: string | null
  recommended_qty: number | null
  unit: string | null
  user_qty_override: number | null
  status: string
  priority: number | null
  products?: Product
}

interface ShoppingList {
  shopping_list_id: string
  title: string | null
  status: string
  created_at: string
  shopping_list_items: ShoppingListItem[]
}

export default function ShoppingPage() {
  const router = useRouter()
  const { user, loading } = useAuthStore()
  const [shoppingLists, setShoppingLists] = useState<ShoppingList[]>([])
  const [pastLists, setPastLists] = useState<ShoppingList[]>([])
  const [activeList, setActiveList] = useState<ShoppingList | null>(null)
  const [showFrequentItems, setShowFrequentItems] = useState(false)
  const [showAllProducts, setShowAllProducts] = useState(false)
  const [loadingLists, setLoadingLists] = useState(true)
  const [allProducts, setAllProducts] = useState<Product[]>([])
  const [newItemText, setNewItemText] = useState('')
  const [editingItem, setEditingItem] = useState<string | null>(null)
  const [editQty, setEditQty] = useState<number>(1)

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  useEffect(() => {
    if (user) {
      loadShoppingLists()
      loadPastLists()
      loadAllProducts()
    }
  }, [user])

  const loadShoppingLists = async () => {
    try {
      setLoadingLists(true)
      const response = await api.get(`/shopping-lists?user_id=${user?.id}&status=ACTIVE`)
      setShoppingLists(response.data)
      if (response.data.length > 0) {
        setActiveList(response.data[0])
      }
    } catch (error) {
      console.error('Error loading shopping lists:', error)
    } finally {
      setLoadingLists(false)
    }
  }

  const loadPastLists = async () => {
    try {
      const response = await api.get(`/shopping-lists?user_id=${user?.id}&status=COMPLETED`)
      setPastLists(response.data)
    } catch (error) {
      console.error('Error loading past lists:', error)
    }
  }

  const loadAllProducts = async () => {
    try {
      const response = await api.get('/products')
      setAllProducts(response.data)
    } catch (error) {
      console.error('Error loading products:', error)
    }
  }

  const createNewList = async (includeFrequent: boolean = false) => {
    try {
      const response = await api.post(`/shopping-lists?user_id=${user?.id}`, {
        title: `Shopping List - ${new Date().toLocaleDateString('en-US')}`,
        status: 'ACTIVE',
      })
      const newList = response.data
      
      if (includeFrequent) {
        setShowFrequentItems(true)
      } else {
        setShowAllProducts(true)
      }
      
      await loadShoppingLists()
      setActiveList(newList)
    } catch (error) {
      console.error('Error creating shopping list:', error)
    }
  }

  const addItemToList = async (productId?: string, productName?: string, qty: number = 1) => {
    if (!activeList) return

    try {
      await api.post(`/shopping-lists/${activeList.shopping_list_id}/items`, {
        product_id: productId || null,
        free_text_name: productName || null,
        recommended_qty: qty,
        status: 'PLANNED',
        added_by: 'USER',
      })
      await loadShoppingLists()
      setNewItemText('')
    } catch (error) {
      console.error('Error adding item:', error)
    }
  }

  const updateItemQty = async (itemId: string, qty: number) => {
    try {
      await api.put(`/shopping-lists/items/${itemId}`, {
        user_qty_override: qty,
      })
      await loadShoppingLists()
      setEditingItem(null)
    } catch (error) {
      console.error('Error updating item:', error)
    }
  }

  const deleteItem = async (itemId: string) => {
    try {
      await api.delete(`/shopping-lists/items/${itemId}`)
      await loadShoppingLists()
    } catch (error) {
      console.error('Error deleting item:', error)
    }
  }

  const handleGoShopping = () => {
    if (activeList) {
      router.push(`/dashboard/shopping-active?list_id=${activeList.shopping_list_id}`)
    }
  }

  const handleSpecialMeal = () => {
    router.push('/dashboard/special-meal')
  }

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <DashboardLayout>
      <div className="px-4 py-6 sm:px-0 max-w-7xl mx-auto">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-bold text-gray-900 mb-3 flex items-center gap-3">
            <ShoppingCart className="h-10 w-10 text-blue-600" />
            Shopping Lists
          </h1>
          <p className="text-gray-600">Create and manage your shopping lists</p>
        </motion.div>

        {/* Create New List Section */}
        {!activeList && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-2xl p-8 mb-6 text-center"
          >
            <ShoppingCart className="h-16 w-16 text-blue-600 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-3">Start a New Shopping List</h2>
            <p className="text-gray-600 mb-6">Choose how you'd like to build your list</p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={() => createNewList(true)}
                className="bg-blue-600 text-white px-8 py-3 rounded-xl hover:bg-blue-700 flex items-center justify-center gap-2 transition-all shadow-lg hover:shadow-xl"
              >
                <Clock className="h-5 w-5" />
                Frequent Items (Weekly)
              </button>
              <button
                onClick={() => createNewList(false)}
                className="bg-white text-blue-600 border-2 border-blue-600 px-8 py-3 rounded-xl hover:bg-blue-50 flex items-center justify-center gap-2 transition-all"
              >
                <Package className="h-5 w-5" />
                All Products
              </button>
            </div>
          </motion.div>
        )}

        {/* Frequent/All Products Selection Modal */}
        <AnimatePresence>
          {(showFrequentItems || showAllProducts) && activeList && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
              onClick={() => {
                setShowFrequentItems(false)
                setShowAllProducts(false)
              }}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-white rounded-2xl p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-2xl font-bold text-gray-900">
                    {showFrequentItems ? 'Frequent Items' : 'All Products'}
                  </h3>
                  <button
                    onClick={() => {
                      setShowFrequentItems(false)
                      setShowAllProducts(false)
                    }}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    <X className="h-6 w-6" />
                  </button>
                </div>

                <div className="space-y-2 mb-4">
                  {allProducts.map((product) => (
                    <div
                      key={product.product_id}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                      <div>
                        <p className="font-medium text-gray-900">{product.product_name}</p>
                        <p className="text-sm text-gray-500">{product.category_name}</p>
                      </div>
                      <button
                        onClick={() => addItemToList(product.product_id, undefined, 1)}
                        className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-2"
                      >
                        <Plus className="h-4 w-4" />
                        Add
                      </button>
                    </div>
                  ))}
                </div>

                <button
                  onClick={() => {
                    setShowFrequentItems(false)
                    setShowAllProducts(false)
                  }}
                  className="w-full bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300"
                >
                  Done
                </button>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Active Shopping List */}
        {activeList && (
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Main List */}
            <div className="lg:col-span-2">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white shadow-xl rounded-2xl p-6 border border-gray-200"
              >
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-2xl font-bold text-gray-900">{activeList.title}</h2>
                  <button
                    onClick={handleGoShopping}
                    className="bg-green-600 text-white px-6 py-3 rounded-xl hover:bg-green-700 flex items-center gap-2 transition-all shadow-lg hover:shadow-xl"
                  >
                    Start Shopping
                    <ArrowRight className="h-5 w-5" />
                  </button>
                </div>

                {/* Add Item Input */}
                <div className="mb-6">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newItemText}
                      onChange={(e) => setNewItemText(e.target.value)}
                      placeholder="Add item to list..."
                      onKeyPress={(e) => {
                        if (e.key === 'Enter' && newItemText.trim()) {
                          addItemToList(undefined, newItemText.trim())
                        }
                      }}
                      className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 placeholder:text-gray-400"
                    />
                    <button
                      onClick={() => {
                        if (newItemText.trim()) {
                          addItemToList(undefined, newItemText.trim())
                        }
                      }}
                      className="bg-blue-600 text-white px-6 py-3 rounded-xl hover:bg-blue-700 flex items-center gap-2"
                    >
                      <Plus className="h-5 w-5" />
                      Add
                    </button>
                  </div>
                </div>

                {/* Special Meal Button */}
                <button
                  onClick={handleSpecialMeal}
                  className="w-full mb-6 bg-gradient-to-r from-purple-500 to-pink-500 text-white px-6 py-4 rounded-xl hover:from-purple-600 hover:to-pink-600 flex items-center justify-center gap-2 transition-all shadow-lg"
                >
                  <ChefHat className="h-5 w-5" />
                  Planning something special this week?
                </button>

                {/* Items List */}
                <div className="space-y-2">
                  {!activeList.shopping_list_items || activeList.shopping_list_items.length === 0 ? (
                    <div className="text-center py-12">
                      <Package className="h-16 w-16 text-gray-300 mx-auto mb-3" />
                      <p className="text-gray-500">Your list is empty</p>
                    </div>
                  ) : (
                    activeList.shopping_list_items.map((item) => (
                      <motion.div
                        key={item.shopping_list_item_id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="flex items-center justify-between p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors"
                      >
                        <div className="flex-1">
                          <p className="font-medium text-gray-900">
                            {item.products?.product_name || item.free_text_name}
                          </p>
                          {item.products?.category_name && (
                            <p className="text-sm text-gray-500">{item.products.category_name}</p>
                          )}
                        </div>

                        <div className="flex items-center gap-3">
                          {editingItem === item.shopping_list_item_id ? (
                            <>
                              <input
                                type="number"
                                value={editQty}
                                onChange={(e) => setEditQty(Number(e.target.value))}
                                className="w-20 px-3 py-2 border-2 border-blue-500 rounded-lg text-center text-gray-900"
                                min="1"
                              />
                              <button
                                onClick={() => updateItemQty(item.shopping_list_item_id, editQty)}
                                className="text-green-600 hover:text-green-700"
                              >
                                <Check className="h-5 w-5" />
                              </button>
                              <button
                                onClick={() => setEditingItem(null)}
                                className="text-red-600 hover:text-red-700"
                              >
                                <X className="h-5 w-5" />
                              </button>
                            </>
                          ) : (
                            <>
                              <span className="text-sm font-medium text-gray-700 min-w-[60px] text-center">
                                {item.user_qty_override || item.recommended_qty || 1} {item.unit || 'unit'}
                              </span>
                              <button
                                onClick={() => {
                                  setEditingItem(item.shopping_list_item_id)
                                  setEditQty(item.user_qty_override || item.recommended_qty || 1)
                                }}
                                className="text-blue-600 hover:text-blue-700"
                              >
                                <Edit2 className="h-5 w-5" />
                              </button>
                              <button
                                onClick={() => deleteItem(item.shopping_list_item_id)}
                                className="text-red-600 hover:text-red-700"
                              >
                                <Trash2 className="h-5 w-5" />
                              </button>
                            </>
                          )}
                        </div>
                      </motion.div>
                    ))
                  )}
                </div>
              </motion.div>
            </div>

            {/* Sidebar - Past Lists */}
            <div className="lg:col-span-1">
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="bg-white shadow-xl rounded-2xl p-6 border border-gray-200"
              >
                <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <Calendar className="h-6 w-6 text-blue-600" />
                  Past Lists
                </h3>

                <div className="space-y-2">
                  {pastLists.length === 0 ? (
                    <p className="text-gray-500 text-sm text-center py-8">No past lists</p>
                  ) : (
                    pastLists.map((list) => (
                      <div
                        key={list.shopping_list_id}
                        className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors"
                      >
                        <p className="font-medium text-gray-900">{list.title}</p>
                        <p className="text-sm text-gray-500">
                          {list.shopping_list_items?.length || 0} items • {new Date(list.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </motion.div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}

