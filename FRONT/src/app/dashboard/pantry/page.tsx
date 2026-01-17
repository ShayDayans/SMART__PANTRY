'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/useAuthStore'
import { DashboardLayout } from '@/components/layouts/DashboardLayout'
import { api } from '@/lib/api'
import { Package, Trash2, RefreshCw, Plus, TrendingUp, Clock, Search, Filter, X, Edit2, Check, AlertCircle, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'

interface InventoryItem {
  product_id: string
  product_name: string
  state: 'EMPTY' | 'LOW' | 'MEDIUM' | 'FULL' | 'UNKNOWN'
  estimated_qty: number | null
  confidence: number
  displayed_name: string | null
  last_updated_at?: string
  products?: {
    product_id?: string
    product_name?: string
    category_id?: string
    product_categories?: {
      category_id: string
      category_name: string
    }
  }
  // Prediction data
  prediction?: {
    expected_days_left: number
    predicted_state: string
    confidence: number
    stock_percentage: number
  }
}

interface Category {
  category_id: string
  category_name: string
}

// Helper function to get category name from item
const getCategoryName = (item: InventoryItem, categories: Category[]): string | null => {
  // Try multiple ways to get category name:
  // 1. From nested product_categories object (can be object or array)
  if (item.products?.product_categories) {
    if (typeof item.products.product_categories === 'object' && !Array.isArray(item.products.product_categories)) {
      // It's an object
      if (item.products.product_categories.category_name) {
        return item.products.product_categories.category_name
      }
    } else if (Array.isArray(item.products.product_categories) && item.products.product_categories.length > 0) {
      // It's an array
      if (item.products.product_categories[0]?.category_name) {
        return item.products.product_categories[0].category_name
      }
    }
  }
  
  // 2. From category_id - look up in categories list
  const categoryId = item.products?.category_id
  if (categoryId) {
    // Try exact match first
    let category = categories.find(c => c.category_id === categoryId)
    if (!category) {
      // Try string comparison (in case of UUID format differences)
      category = categories.find(c => String(c.category_id).toLowerCase() === String(categoryId).toLowerCase())
    }
    if (category) {
      return category.category_name
    }
  }
  
  return null
}

const getStockPercentage = (state: string): number => {
  switch (state) {
    case 'FULL': return 100
    case 'MEDIUM': return 50
    case 'LOW': return 25
    case 'EMPTY': return 0
    default: return 0
  }
}

const getStockLabel = (state: string): string => {
  switch (state) {
    case 'FULL': return 'FULL'
    case 'MEDIUM': return 'MEDIUM'
    case 'LOW': return 'LOW'
    case 'EMPTY': return 'EMPTY'
    case 'UNKNOWN': return 'MEDIUM' // Default UNKNOWN to MEDIUM
    default: return 'MEDIUM'
  }
}

// Updated colors: FULL=green, MEDIUM=yellow, LOW=orange, EMPTY=red
const getColorFromState = (state: string): string => {
  switch (state) {
    case 'FULL': return 'from-green-500 to-emerald-500'
    case 'MEDIUM': return 'from-yellow-500 to-amber-500'
    case 'LOW': return 'from-orange-500 to-orange-600'
    case 'EMPTY': return 'from-red-500 to-rose-500'
    default: return 'from-gray-500 to-gray-600'
  }
}

const getTextColorFromState = (state: string): string => {
  switch (state) {
    case 'FULL': return 'text-green-600'
    case 'MEDIUM': return 'text-yellow-600'
    case 'LOW': return 'text-orange-600'
    case 'EMPTY': return 'text-red-600'
    default: return 'text-gray-600'
  }
}

const getBgColorFromState = (state: string): string => {
  switch (state) {
    case 'FULL': return 'bg-green-100'
    case 'MEDIUM': return 'bg-yellow-100'
    case 'LOW': return 'bg-orange-100'
    case 'EMPTY': return 'bg-red-100'
    default: return 'bg-gray-100'
  }
}

const getBadgeColorFromState = (state: string): string => {
  switch (state) {
    case 'FULL': return 'bg-green-500 text-white'
    case 'MEDIUM': return 'bg-yellow-500 text-white'
    case 'LOW': return 'bg-orange-500 text-white'
    case 'EMPTY': return 'bg-red-500 text-white'
    default: return 'bg-gray-500 text-white'
  }
}

export default function PantryPage() {
  const router = useRouter()
  const { user, loading } = useAuthStore()
  const [inventory, setInventory] = useState<InventoryItem[]>([])
  const [allInventory, setAllInventory] = useState<InventoryItem[]>([])
  const [loadingInventory, setLoadingInventory] = useState(true)
  const [notification, setNotification] = useState<string | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedState, setSelectedState] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [sortBy, setSortBy] = useState<string>('stock_level')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  const [editingCategoryFor, setEditingCategoryFor] = useState<string | null>(null)
  const [selectedCategoryForProduct, setSelectedCategoryForProduct] = useState<{ [key: string]: string }>({})
  
  // Product action modal state
  const [actionModalOpen, setActionModalOpen] = useState(false)
  const [actionProductId, setActionProductId] = useState<string | null>(null)
  const [actionType, setActionType] = useState<'thrown_away' | 'repurchased' | 'ran_out' | null>(null)
  const [actionReason, setActionReason] = useState<string>('')
  const [actionCustomReason, setActionCustomReason] = useState<string>('')

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  useEffect(() => {
    if (user) {
      loadInventory()
      loadCategories()
    }
  }, [user])

  useEffect(() => {
    filterInventory()
  }, [selectedCategory, selectedState, searchQuery, allInventory, sortBy, sortOrder])

  // Debug: log when filters change
  useEffect(() => {
    console.log('[FILTER DEBUG] Filters changed:', {
      selectedCategory,
      selectedState,
      searchQuery,
      allInventoryCount: allInventory.length
    })
  }, [selectedCategory, selectedState, searchQuery, allInventory.length])

  const loadCategories = async () => {
    try {
      const response = await api.get('/products/categories')
      setCategories(response.data || [])
    } catch (error) {
      console.error('Error loading categories:', error)
    }
  }

  const sortInventory = (items: InventoryItem[], sortBy: string, order: 'asc' | 'desc'): InventoryItem[] => {
    const sorted = [...items]
    
    switch (sortBy) {
      case 'estimated_qty':
        sorted.sort((a, b) => {
          const aQty = a.estimated_qty ?? 0
          const bQty = b.estimated_qty ?? 0
          return order === 'asc' ? aQty - bQty : bQty - aQty
        })
        break
      
      case 'last_updated':
        sorted.sort((a, b) => {
          // Handle missing dates - put them at the end
          const aDate = a.last_updated_at ? new Date(a.last_updated_at).getTime() : 0
          const bDate = b.last_updated_at ? new Date(b.last_updated_at).getTime() : 0
          
          // If one has no date, put it at the end
          if (aDate === 0 && bDate !== 0) return 1
          if (aDate !== 0 && bDate === 0) return -1
          
          return order === 'asc' ? aDate - bDate : bDate - aDate
        })
        break
      
      case 'name':
        sorted.sort((a, b) => {
          const aName = (a.displayed_name || a.product_name || '').toLowerCase()
          const bName = (b.displayed_name || b.product_name || '').toLowerCase()
          return order === 'asc' 
            ? aName.localeCompare(bName)
            : bName.localeCompare(aName)
        })
        break
      
      case 'stock_level':
      default:
        // Default sort: items running out first, then by stock percentage
        sorted.sort((a, b) => {
          const aPercentage = a.prediction?.stock_percentage || 0
          const bPercentage = b.prediction?.stock_percentage || 0
          const aDaysLeft = a.prediction?.expected_days_left || 999
          const bDaysLeft = b.prediction?.expected_days_left || 999
          
          // Items running out (< 3 days) should be first
          if (aDaysLeft < 3 && bDaysLeft >= 3) return order === 'asc' ? -1 : 1
          if (aDaysLeft >= 3 && bDaysLeft < 3) return order === 'asc' ? 1 : -1
          
          return order === 'asc' 
            ? aPercentage - bPercentage
            : bPercentage - aPercentage
        })
        break
    }
    
    return sorted
  }

  const filterInventory = () => {
    let filtered = [...allInventory]

    // Filter by category
    if (selectedCategory && selectedCategory !== '') {
      console.log('[FILTER] Filtering by category:', selectedCategory)
      console.log('[FILTER] Total items before filter:', filtered.length)
      
      filtered = filtered.filter((item) => {
        // Get category_id - prioritize direct access from products.category_id
        const categoryId = item.products?.category_id
        
        // Debug logging for first few items
        if (filtered.indexOf(item) < 3) {
          console.log(`[FILTER] Item ${item.product_id}:`, {
            categoryId,
            products: item.products,
            hasProducts: !!item.products
          })
        }
        
        if (!categoryId) {
          // No category means it doesn't match the selected category
          return false
        }
        
        // Convert both to strings for comparison (handles UUID vs string)
        // Use exact match without toLowerCase to preserve UUID format
        const itemCategoryId = String(categoryId).trim()
        const selectedCategoryId = String(selectedCategory).trim()
        
        const matches = itemCategoryId === selectedCategoryId
        
        // Debug logging for first few items
        if (filtered.indexOf(item) < 3) {
          console.log(`[FILTER] Item ${item.product_id}: ${itemCategoryId} === ${selectedCategoryId} = ${matches}`)
        }
        
        return matches
      })
      
      console.log('[FILTER] Total items after filter:', filtered.length)
    }

    // Filter by state
    if (selectedState) {
      filtered = filtered.filter((item) => {
        const currentState = item.prediction?.predicted_state || item.state
        return currentState === selectedState
      })
    }

    // Filter by search query (name filter)
    if (searchQuery) {
      const query = searchQuery.toLowerCase().trim()
      filtered = filtered.filter((item) => {
        // Check displayed_name first, then product_name from nested products object
        const displayedName = (item.displayed_name || '').toLowerCase()
        const productName = (item.products?.product_name || item.product_name || '').toLowerCase()
        return displayedName.includes(query) || productName.includes(query)
      })
    }

    // Apply sorting
    filtered = sortInventory(filtered, sortBy, sortOrder)

    setInventory(filtered)
  }

  const loadInventory = async () => {
    try {
      setLoadingInventory(true)
      const response = await api.get(`/inventory`)
      const inventoryData = response.data || []
      
      // Debug: log inventory structure
      if (inventoryData.length > 0) {
        console.log('[LOAD INVENTORY] Sample inventory item structure:', JSON.stringify(inventoryData[0], null, 2))
        // Check category_id specifically
        const sampleItem = inventoryData[0]
        console.log('[LOAD INVENTORY] Sample item category_id:', sampleItem.products?.category_id)
        console.log('[LOAD INVENTORY] Sample item product_categories:', sampleItem.products?.product_categories)
      }
      
      // Use inventory state directly (it's updated by the predictor model)
      // inventory.state and inventory.estimated_qty are the source of truth
      const inventoryWithPredictions = inventoryData.map((item: InventoryItem) => {
        // Use state from inventory table (updated by predictor)
        const predictedState = item.state !== 'UNKNOWN' ? item.state : 'MEDIUM'
        // In loadInventory function, change line 345:
        // In loadInventory function, change line 345:
        const daysLeft = Math.ceil(item.estimated_qty || 0)
        
        // Debug: log category_id for each item
        if (item.products?.category_id) {
          console.log(`[LOAD INVENTORY] Item ${item.product_id} has category_id:`, item.products.category_id)
        } else {
          console.log(`[LOAD INVENTORY] Item ${item.product_id} has NO category_id`)
        }
        
        return {
          ...item,
          prediction: {
            expected_days_left: daysLeft,
            predicted_state: predictedState,
            confidence: item.confidence || 0,
            stock_percentage: getStockPercentage(predictedState)
          }
        }
      })
      
      console.log('[LOAD INVENTORY] Total items loaded:', inventoryWithPredictions.length)
      console.log('[LOAD INVENTORY] Items with categories:', inventoryWithPredictions.filter((item: InventoryItem) => item.products?.category_id).length)
      
      setAllInventory(inventoryWithPredictions)
      // filterInventory will be called automatically via useEffect
    } catch (error) {
      console.error('Error loading inventory:', error)
    } finally {
      setLoadingInventory(false)
    }
  }

  const handleDecrease = async (item: InventoryItem) => {
    await provideFeedback(item.product_id, 'less', item.displayed_name || item.product_name)
  }

  const handleIncrease = async (item: InventoryItem) => {
    await provideFeedback(item.product_id, 'more', item.displayed_name || item.product_name)
  }

  const provideFeedback = async (productId: string, direction: string, productName: string) => {
    try {
      await api.post(`/inventory/${productId}/feedback?direction=${direction}`)
      
      // Show notification
      setNotification(`✓ Model updated`)
      
      // Auto-hide notification after 2 seconds
      setTimeout(() => {
        setNotification(null)
      }, 2000)
      
      // Wait a bit for the model to update, then reload
      setTimeout(() => {
        loadInventory()
      }, 500)
    } catch (error) {
      console.error('Error providing feedback:', error)
      setNotification(`❌ Failed to update model`)
      setTimeout(() => {
        setNotification(null)
      }, 2000)
    }
  }

  const deleteItem = async (productId: string) => {
    if (!confirm('Are you sure you want to remove this item from your pantry?')) {
      return
    }

    try {
      await api.delete(`/inventory/${productId}`)
      await loadInventory()
    } catch (error) {
      console.error('Error deleting item:', error)
    }
  }

  const updateProductCategory = async (productId: string, categoryId: string | null) => {
    try {
      console.log('[UPDATE CATEGORY] Starting update:', { productId, categoryId })
      // Use the new dedicated endpoint for updating category
      // Send category_id in request body
      const payload: { category_id: string | null } = { category_id: categoryId }
      
      console.log('[UPDATE CATEGORY] Sending payload:', payload)
      const response = await api.patch(`/products/${productId}/category`, payload)
      console.log('[UPDATE CATEGORY] Update response:', response.data)
      
      setNotification(`✓ Category updated`)
      setTimeout(() => {
        setNotification(null)
      }, 2000)
      
      // Reload inventory to show updated category
      // Add a small delay to ensure DB is updated
      await new Promise(resolve => setTimeout(resolve, 300))
      await loadInventory()
      
      // Force filter to re-run with new data
      filterInventory()
      
      setEditingCategoryFor(null)
      // Clear the selected category for this product
      setSelectedCategoryForProduct(prev => {
        const next = { ...prev }
        delete next[productId]
        return next
      })
    } catch (error: any) {
      console.error('[UPDATE CATEGORY] Error:', error)
      console.error('[UPDATE CATEGORY] Error response:', error?.response?.data)
      const errorMessage = error?.response?.data?.detail || 'Failed to update category'
      setNotification(`❌ ${errorMessage}`)
      setTimeout(() => {
        setNotification(null)
      }, 2000)
    }
  }

  const handleCategorySelect = (productId: string, categoryId: string) => {
    console.log('Category selected:', { productId, categoryId })
    setSelectedCategoryForProduct(prev => {
      const updated = { ...prev, [productId]: categoryId }
      console.log('Updated selectedCategoryForProduct:', updated)
      return updated
    })
  }

  const handleCategorySave = (productId: string) => {
    const categoryId = selectedCategoryForProduct[productId]
    // Convert empty string to null
    const finalCategoryId = categoryId && categoryId.trim() !== '' ? categoryId : null
    console.log('Saving category for product:', productId, 'category:', finalCategoryId)
    updateProductCategory(productId, finalCategoryId)
  }

  // Product action handlers
  const openActionModal = (productId: string, type: 'thrown_away' | 'repurchased' | 'ran_out') => {
    setActionProductId(productId)
    setActionType(type)
    setActionReason('')
    setActionCustomReason('')
    setActionModalOpen(true)
  }

  const closeActionModal = () => {
    setActionModalOpen(false)
    setActionProductId(null)
    setActionType(null)
    setActionReason('')
    setActionCustomReason('')
  }

  const handleProductAction = async () => {
    if (!actionProductId || !actionType || !actionReason) {
      setNotification('❌ Please select a reason')
      setTimeout(() => setNotification(null), 2000)
      return
    }

    try {
      const payload: {
        action_type: string
        reason: string
        custom_reason?: string
      } = {
        action_type: actionType,
        reason: actionReason,
      }

      if (actionReason === 'Other' && actionCustomReason.trim()) {
        payload.custom_reason = actionCustomReason.trim()
      }

      await api.post(`/inventory/${actionProductId}/action`, payload)

      setNotification('✓ Action completed successfully')
      setTimeout(() => {
        setNotification(null)
      }, 2000)

      closeActionModal()
      
      // Reload inventory after a short delay
      setTimeout(() => {
        loadInventory()
      }, 500)
    } catch (error: any) {
      console.error('Error performing product action:', error)
      const errorMessage = error?.response?.data?.detail || 'Failed to perform action'
      setNotification(`❌ ${errorMessage}`)
      setTimeout(() => {
        setNotification(null)
      }, 2000)
    }
  }

  // Get reason options based on action type
  const getReasonOptions = (type: string): string[] => {
    if (type === 'thrown_away') {
      return ['Didn\'t taste good', 'Expired', 'Other']
    } else if (type === 'repurchased') {
      return ['Ran out', 'Product was damaged', 'Other']
    } else if (type === 'ran_out') {
      return ['Ran out', 'Other']
    }
    return []
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
      <div className="px-4 py-6 sm:px-0 max-w-7xl mx-auto" dir="ltr">
        {/* Notification Toast */}
        {notification && (
          <div className="fixed top-4 right-4 z-50 animate-fade-in">
            <div className={`${
              notification.startsWith('✓') ? 'bg-green-500' : 'bg-red-500'
            } text-white px-6 py-4 rounded-xl shadow-2xl flex items-center gap-3 max-w-md`}>
              <span className="text-lg font-semibold">{notification}</span>
            </div>
          </div>
        )}

        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 mb-2">My Pantry</h1>
            <p className="text-gray-600">AI-powered predictions for your inventory</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={loadInventory}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors shadow-lg"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
            <button
              onClick={() => router.push('/dashboard/pantry/add')}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-xl hover:bg-green-700 transition-colors shadow-lg"
            >
              <Plus className="h-4 w-4" />
              Add Product
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white shadow-lg rounded-2xl p-6 mb-6 border border-gray-200">
          <div className="flex items-center gap-4 mb-4">
            <Filter className="h-5 w-5 text-gray-600" />
            <h2 className="text-lg font-semibold text-gray-900">Filters</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search products..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border-2 border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            {/* Category Filter */}
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-4 py-2 border-2 border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat.category_id} value={cat.category_id}>
                  {cat.category_name}
                </option>
              ))}
            </select>

            {/* State Filter */}
            <select
              value={selectedState}
              onChange={(e) => setSelectedState(e.target.value)}
              className="px-4 py-2 border-2 border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All States</option>
              <option value="FULL">Full (Green)</option>
              <option value="MEDIUM">Medium (Yellow)</option>
              <option value="LOW">Low (Orange)</option>
              <option value="EMPTY">Empty (Red)</option>
            </select>

            {/* Sort By */}
            <div className="flex gap-2">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="flex-1 px-4 py-2 border-2 border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="stock_level">Stock Level</option>
                <option value="estimated_qty">Estimated Qty</option>
                <option value="last_updated">Last Updated</option>
                <option value="name">Name</option>
              </select>
              <button
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                className="px-3 py-2 border-2 border-gray-300 rounded-xl hover:bg-gray-50 transition-colors flex items-center justify-center"
                title={sortOrder === 'asc' ? 'Ascending' : 'Descending'}
              >
                {sortOrder === 'asc' ? (
                  <ArrowUp className="h-4 w-4 text-gray-600" />
                ) : (
                  <ArrowDown className="h-4 w-4 text-gray-600" />
                )}
              </button>
            </div>
          </div>

          {/* Active Filters Display */}
          {(selectedCategory || selectedState || searchQuery) && (
            <div className="mt-4 flex flex-wrap gap-2">
              {searchQuery && (
                <span className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-800 rounded-lg text-sm">
                  Search: "{searchQuery}"
                  <button onClick={() => setSearchQuery('')} className="hover:text-blue-600">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {selectedCategory && (
                <span className="inline-flex items-center gap-1 px-3 py-1 bg-purple-100 text-purple-800 rounded-lg text-sm">
                  Category: {categories.find(c => c.category_id === selectedCategory)?.category_name}
                  <button onClick={() => setSelectedCategory('')} className="hover:text-purple-600">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
              {selectedState && (
                <span className="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 text-gray-800 rounded-lg text-sm">
                  State: {selectedState}
                  <button onClick={() => setSelectedState('')} className="hover:text-gray-600">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )}
            </div>
          )}
        </div>

        {loadingInventory ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : inventory.length === 0 ? (
          <div className="bg-white shadow rounded-xl p-12 text-center border border-gray-200">
            <Package className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Your pantry is empty</h2>
            <p className="text-gray-500 text-sm mb-6">
              Start by adding products manually or from shopping
            </p>
            <button
              onClick={() => router.push('/dashboard/pantry/add')}
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors"
            >
              <Plus className="h-5 w-5" />
              Add Your First Product
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {inventory.map((item) => {
              const predictedState = item.prediction?.predicted_state || item.state
              const percentage = item.prediction?.stock_percentage || 0
              const daysLeft = item.prediction?.expected_days_left || 0
              const stockLabel = getStockLabel(predictedState)
              
              return (
                <div
                  key={item.product_id}
                  className="bg-white shadow-lg rounded-2xl p-6 hover:shadow-xl transition-all border border-gray-100"
                >
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex-1">
                      <h3 className="text-lg font-bold text-gray-900 mb-2">
                        {item.displayed_name || item.product_name}
                      </h3>
                      
                      {/* Category Name with Edit */}
                      <div className="mb-2">
                        {editingCategoryFor === item.product_id ? (
                          <div className="flex items-center gap-2">
                            <select
                              value={selectedCategoryForProduct[item.product_id] || item.products?.category_id || ''}
                              onChange={(e) => handleCategorySelect(item.product_id, e.target.value)}
                              className="px-3 py-1 rounded-lg text-xs font-semibold border border-purple-300 focus:outline-none focus:ring-2 focus:ring-purple-500"
                            >
                              <option value="">No Category</option>
                              {categories.map((cat) => (
                                <option key={cat.category_id} value={cat.category_id}>
                                  {cat.category_name}
                                </option>
                              ))}
                            </select>
                            <button
                              onClick={() => handleCategorySave(item.product_id)}
                              className="p-1 text-green-600 hover:bg-green-50 rounded transition-colors"
                              title="Save category"
                            >
                              <Check className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => {
                                setEditingCategoryFor(null)
                                setSelectedCategoryForProduct(prev => ({
                                  ...prev,
                                  [item.product_id]: item.products?.category_id || ''
                                }))
                              }}
                              className="p-1 text-gray-400 hover:bg-gray-50 rounded transition-colors"
                              title="Cancel"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            {(() => {
                              const categoryName = getCategoryName(item, categories)
                              return categoryName ? (
                                <span className="inline-flex items-center px-3 py-1 rounded-lg text-xs font-semibold bg-purple-100 text-purple-700 border border-purple-200">
                                  {categoryName}
                                </span>
                              ) : (
                                <span className="inline-flex items-center px-3 py-1 rounded-lg text-xs font-medium bg-gray-100 text-gray-500 border border-gray-200">
                                  No Category
                                </span>
                              )
                            })()}
                            <button
                              onClick={() => {
                                const currentCategoryId = item.products?.category_id || ''
                                console.log('[EDIT CATEGORY] Starting edit for product:', item.product_id, 'current category:', currentCategoryId)
                                setEditingCategoryFor(item.product_id)
                                setSelectedCategoryForProduct(prev => ({ 
                                  ...prev, 
                                  [item.product_id]: currentCategoryId
                                }))
                              }}
                              className="p-1 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded transition-colors"
                              title="Edit category"
                            >
                              <Edit2 className="h-3 w-3" />
                            </button>
                          </div>
                        )}
                      </div>
                      
                      {/* State Badge */}
                      <div className="flex items-center gap-2 mb-3">
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-bold ${getBadgeColorFromState(predictedState)}`}>
                          {stockLabel}
                        </span>
                      </div>
                    </div>
                    
                    <div className="flex gap-2">
                      {/* Product Action Buttons */}
                      <button
                        onClick={() => openActionModal(item.product_id, 'thrown_away')}
                        className="p-2 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded-lg transition-colors"
                        title="Thrown Away"
                      >
                        <Trash2 className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => openActionModal(item.product_id, 'repurchased')}
                        className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Repurchased"
                      >
                        <RefreshCw className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => openActionModal(item.product_id, 'ran_out')}
                        className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Ran Out"
                      >
                        <AlertCircle className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => deleteItem(item.product_id)}
                        className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Delete product"
                      >
                        <X className="h-5 w-5" />
                      </button>
                    </div>
                  </div>

                  {/* Stock Level Display - LOW/MEDIUM/HIGH */}
                  <div className="mb-4">
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-sm font-medium text-gray-600">Stock Level</span>
                      <span className={`text-2xl font-bold px-4 py-1 rounded-xl ${getBgColorFromState(predictedState)} ${getTextColorFromState(predictedState)}`}>
                        {stockLabel}
                      </span>
                    </div>
                    
                    {/* Gradient Progress Bar */}
                    <div className="relative h-3 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full bg-gradient-to-r ${getColorFromState(predictedState)} transition-all duration-500`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>

                  {/* Days Left Prediction */}
                  {daysLeft > 0 && (
                    <div className="mb-4 p-3 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-200">
                      <div className="flex items-center gap-2 text-blue-900">
                        <Clock className="h-4 w-4" />
                        <span className="text-sm font-semibold">
                          {daysLeft < 3 ? (
                            <span className="text-red-600">⚠️ Running out in {daysLeft} days</span>
                          ) : (
                            <span>Will last ~{daysLeft} days</span>
                          )}
                        </span>
                      </div>
                      <div className="mt-1 text-xs text-blue-700">
                        AI Confidence: {Math.round((item.prediction?.confidence || 0) * 100)}%
                      </div>
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div className="flex items-center justify-between pt-4 border-t border-gray-200">
                    <span className="text-xs text-gray-500">Provide Feedback</span>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleDecrease(item)}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                      >
                        Less
                      </button>
                      <button
                        onClick={() => handleIncrease(item)}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                      >
                        More
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Product Action Modal */}
      {actionModalOpen && actionType && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" dir="ltr">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-gray-900">
                {actionType === 'thrown_away' && 'Thrown Away'}
                {actionType === 'repurchased' && 'Repurchased'}
                {actionType === 'ran_out' && 'Ran Out'}
              </h3>
              <button
                onClick={closeActionModal}
                className="p-1 text-gray-400 hover:text-gray-600 rounded transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {actionType === 'thrown_away' && 'Why was the product thrown away?'}
                {actionType === 'repurchased' && 'Why was the product repurchased?'}
                {actionType === 'ran_out' && 'Why did the product run out?'}
              </label>
              <select
                value={actionReason}
                onChange={(e) => setActionReason(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select reason</option>
                {getReasonOptions(actionType).map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>

            {actionReason === 'Other' && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Please specify
                </label>
                <input
                  type="text"
                  value={actionCustomReason}
                  onChange={(e) => setActionCustomReason(e.target.value)}
                  placeholder="Enter custom reason"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            )}

            <div className="flex gap-3 justify-end">
              <button
                onClick={closeActionModal}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleProductAction}
                disabled={!actionReason || (actionReason === 'Other' && !actionCustomReason.trim())}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  )
}
