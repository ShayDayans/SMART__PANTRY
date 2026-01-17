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
  Trash2,
  X,
  Package
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface Product {
  product_id: string
  product_name: string
  category_name?: string
  category_id?: string
}

interface Category {
  category_id: string
  category_name: string
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
  created_at?: string
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
  const [showAllProducts, setShowAllProducts] = useState(false)
  const [loadingLists, setLoadingLists] = useState(true)
  const [allProducts, setAllProducts] = useState<Product[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [newItemText, setNewItemText] = useState('')
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([])
  const [showProductSuggestions, setShowProductSuggestions] = useState(false)
  const [showCreateProductModal, setShowCreateProductModal] = useState(false)
  const [newProductName, setNewProductName] = useState('')
  const [newProductCategory, setNewProductCategory] = useState<string>('')
  const [creatingProduct, setCreatingProduct] = useState(false)
  const [notification, setNotification] = useState<string | null>(null)
  const [recentlyAddedItemId, setRecentlyAddedItemId] = useState<string | null>(null)
  const [selectedPastList, setSelectedPastList] = useState<ShoppingList | null>(null)

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
      loadCategories()
    }
  }, [user])

  const loadShoppingLists = async (reloadActiveListItems: boolean = false) => {
    try {
      setLoadingLists(true)
      const response = await api.get(`/shopping-lists?status=ACTIVE`)
      const lists = response.data || []
      setShoppingLists(lists)
      
      // Update activeList if it exists and matches current activeList
      if (lists.length > 0) {
        if (activeList) {
          // Find the updated version of the current active list
          const updatedActiveList = lists.find(
            (list: ShoppingList) => list.shopping_list_id === activeList.shopping_list_id
          )
          if (updatedActiveList) {
            // If we need to reload items, fetch the full list with items
            if (reloadActiveListItems) {
              try {
                const fullListResponse = await api.get(`/shopping-lists/${updatedActiveList.shopping_list_id}`)
                const fullList = fullListResponse.data
                // Also load items separately to get prediction data
                const itemsResponse = await api.get(`/shopping-lists/${updatedActiveList.shopping_list_id}/items`)
                if (fullList) {
                  fullList.shopping_list_items = itemsResponse.data || []
                  setActiveList(fullList)
                } else {
                  setActiveList(updatedActiveList)
                }
              } catch (error) {
                console.error('Error loading full list with items:', error)
                setActiveList(updatedActiveList)
              }
            } else {
              // Preserve existing items if they exist, otherwise update
              if (activeList.shopping_list_items && activeList.shopping_list_items.length > 0) {
                // Keep the existing activeList with its items
                setActiveList({
                  ...updatedActiveList,
                  shopping_list_items: activeList.shopping_list_items
                })
              } else {
                // No items in current activeList, update it
                setActiveList(updatedActiveList)
              }
            }
          } else {
            // If current active list not found, use first one
            setActiveList(lists[0])
          }
        } else {
          // No active list, set first one
          setActiveList(lists[0])
        }
      } else {
        setActiveList(null)
      }
    } catch (error) {
      console.error('Error loading shopping lists:', error)
    } finally {
      setLoadingLists(false)
    }
  }

  const loadPastLists = async () => {
    try {
      const response = await api.get(`/shopping-lists?status=COMPLETED`)
      const lists = response.data || []
      
      // Load items for each past list
      const listsWithItems = await Promise.all(
        lists.map(async (list: ShoppingList) => {
          try {
            const itemsResponse = await api.get(`/shopping-lists/${list.shopping_list_id}/items`)
            return {
              ...list,
              shopping_list_items: itemsResponse.data || []
            }
          } catch (error) {
            console.error(`Error loading items for list ${list.shopping_list_id}:`, error)
            return {
              ...list,
              shopping_list_items: []
            }
          }
        })
      )
      
      setPastLists(listsWithItems)
    } catch (error) {
      console.error('Error loading past lists:', error)
    }
  }

  const loadAllProducts = async () => {
    try {
      // Load ALL products from products table (not just from inventory)
      const response = await api.get('/products')
      console.log('Products API response:', response.data)
      
      const products = Array.isArray(response.data) ? response.data : []
      const productsList: Product[] = products.map((product: any) => ({
        product_id: product.product_id,
        product_name: product.product_name,
        category_id: product.category_id,
        category_name: product.category?.category_name || undefined
      }))
      
      setAllProducts(productsList)
      console.log(`✅ Loaded ${productsList.length} products from products table`)
    } catch (error) {
      console.error('❌ Error loading products:', error)
      setAllProducts([])
    }
  }

  const loadCategories = async () => {
    try {
      const response = await api.get('/products/categories')
      const categoriesList: Category[] = Array.isArray(response.data) ? response.data : []
      setCategories(categoriesList)
      console.log(`✅ Loaded ${categoriesList.length} categories`)
    } catch (error) {
      console.error('❌ Error loading categories:', error)
      setCategories([])
    }
  }

  const createNewList = async (includeFrequent: boolean = false) => {
    try {
      const response = await api.post(`/shopping-lists`, {
        title: `Shopping List - ${new Date().toLocaleDateString('en-US')}`,
        status: 'ACTIVE',
      })
      const newList = response.data
      
      if (includeFrequent) {
        // Load products with LOW/EMPTY states from inventory
        try {
          console.log('Loading frequent items (LOW/EMPTY)...')
          
          // Fetch LOW state items
          const lowResponse = await api.get('/inventory?state=LOW')
          const lowItems = lowResponse.data || []
          console.log(`Found ${lowItems.length} LOW items:`, lowItems)
          
          // Fetch EMPTY state items
          const emptyResponse = await api.get('/inventory?state=EMPTY')
          const emptyItems = emptyResponse.data || []
          console.log(`Found ${emptyItems.length} EMPTY items:`, emptyItems)
          
          // Combine and add to list
          const frequentProducts = [...lowItems, ...emptyItems]
          console.log(`Total frequent products to add: ${frequentProducts.length}`)
          
          let addedCount = 0
          for (const item of frequentProducts) {
            // Check both direct product_id and nested products.product_id
            const productId = item.product_id || (item.products && item.products.product_id)
            
            if (productId) {
              try {
                console.log(`Adding product ${productId} to shopping list...`)
                await api.post(`/shopping-lists/${newList.shopping_list_id}/items`, {
                  product_id: productId,
                  status: 'PLANNED',
                  added_by: 'SYSTEM',
                })
                addedCount++
                console.log(`✓ Added product ${productId}`)
              } catch (error: any) {
                console.error(`Error adding frequent item ${productId}:`, error)
                console.error('Error details:', error.response?.data)
              }
            } else {
              console.warn('Item missing product_id:', item)
            }
          }
          
          console.log(`Successfully added ${addedCount} items to shopping list`)
          
          // Set activeList first with the new list (before items are added)
          setActiveList(newList)
          
          // Explicitly reload the active list with items after adding
          if (newList.shopping_list_id) {
            try {
              // Load items separately to get prediction data
              const itemsResponse = await api.get(`/shopping-lists/${newList.shopping_list_id}/items`)
              const items = itemsResponse.data || []
              
              // Update activeList with items
              setActiveList((prevList) => {
                if (prevList && prevList.shopping_list_id === newList.shopping_list_id) {
                  return {
                    ...prevList,
                    shopping_list_items: items
                  }
                }
                return {
                  ...newList,
                  shopping_list_items: items
                }
              })
              
              console.log(`✓ Reloaded active list with ${items.length} items`)
            } catch (error) {
              console.error('Error reloading active list:', error)
            }
          }
          
          // Also reload shopping lists to update the sidebar (but don't overwrite activeList)
          // We'll reload without updating activeList since we just set it above
          try {
            const response = await api.get(`/shopping-lists?status=ACTIVE`)
            const lists = response.data || []
            setShoppingLists(lists)
            // Don't update activeList here - we already have it with items
          } catch (error) {
            console.error('Error reloading shopping lists:', error)
          }
          
          if (addedCount > 0) {
            setNotification(`✓ Added ${addedCount} frequent items to your list`)
            setTimeout(() => setNotification(null), 3000)
          } else {
            setNotification('⚠️ No frequent items found (no LOW/EMPTY products in pantry)')
            setTimeout(() => setNotification(null), 5000)
          }
        } catch (error: any) {
          console.error('Error loading frequent items:', error)
          console.error('Error details:', error.response?.data)
          setNotification(`✗ Error loading frequent items: ${error.message || 'Unknown error'}`)
          setTimeout(() => setNotification(null), 5000)
          // Still set the active list even if adding items failed
          setActiveList(newList)
          await loadShoppingLists()
        }
      } else {
        // Show all products modal for manual selection
        setActiveList(newList)
        await loadShoppingLists()
        setShowAllProducts(true)
      }
    } catch (error) {
      console.error('Error creating shopping list:', error)
    }
  }

  const addItemToList = async (productId?: string, productName?: string, qty: number = 1) => {
    if (!activeList) {
      alert('Please create or select a shopping list first')
      return
    }

    try {
      const response = await api.post(`/shopping-lists/${activeList.shopping_list_id}/items`, {
        product_id: productId || null,
        free_text_name: productName || null,
        recommended_qty: qty,
        status: 'PLANNED',
        added_by: 'USER',
      })
      
      console.log('Item added successfully:', response.data)
      
      const addedItemId = response.data?.shopping_list_item_id
      
      // Show success notification
      const productNameToShow = productName || allProducts.find(p => p.product_id === productId)?.product_name || 'Item'
      setNotification(`✓ Added "${productNameToShow}" to your list`)
      setTimeout(() => setNotification(null), 3000)
      
      // Reload the active list with items to get the updated data
      // Pass true to reload items immediately
      await loadShoppingLists(true)
      
      // Highlight the newly added item after list reloads
      if (addedItemId) {
        // Wait for DOM to update with new item
        setTimeout(() => {
          setRecentlyAddedItemId(addedItemId)
          // Scroll to the item
          setTimeout(() => {
            const itemElement = document.getElementById(`item-${addedItemId}`)
            if (itemElement) {
              itemElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
              // Remove highlight after animation
              setTimeout(() => setRecentlyAddedItemId(null), 3000)
            } else {
              // If element not found, try again after a bit more time
              setTimeout(() => {
                const retryElement = document.getElementById(`item-${addedItemId}`)
                if (retryElement) {
                  retryElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
                  setTimeout(() => setRecentlyAddedItemId(null), 3000)
                }
              }, 500)
            }
          }, 100)
        }, 200)
      }
      
      // Don't close modal automatically - let user close it explicitly
      setNewItemText('')
    } catch (error: any) {
      console.error('Error adding item:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to add item. Please try again.'
      setNotification(`✗ ${errorMessage}`)
      setTimeout(() => setNotification(null), 3000)
    }
  }


  const deleteItem = async (itemId: string) => {
    // Store original items for potential revert
    let originalItems: ShoppingListItem[] = []
    let listId: string | null = null

    // Optimistic update: immediately remove item from UI using functional update
    setActiveList((prevList) => {
      if (!prevList) {
        console.log('[DELETE] No active list')
        return prevList
      }

      originalItems = [...(prevList.shopping_list_items || [])]
      listId = prevList.shopping_list_id
      const updatedItems = originalItems.filter(item => item.shopping_list_item_id !== itemId)
      
      console.log('[DELETE] Removing item:', itemId)
      console.log('[DELETE] Original items count:', originalItems.length)
      console.log('[DELETE] Updated items count:', updatedItems.length)

      // Create a completely new object to ensure React detects the change
      return {
        ...prevList,
        shopping_list_items: [...updatedItems] // Ensure new array reference
      }
    })

    try {
      await api.delete(`/shopping-lists/items/${itemId}`)
      console.log('[DELETE] Successfully deleted item from server')
      // Success - item is already removed from UI
    } catch (error) {
      console.error('Error deleting item:', error)
      // Revert optimistic update on failure using functional update
      setActiveList((currentList) => {
        if (!currentList || !listId || currentList.shopping_list_id !== listId) {
          return currentList
        }
        console.log('[DELETE] Reverting - restoring original items')
        return {
          ...currentList,
          shopping_list_items: [...originalItems] // Ensure new array reference
        }
      })
      setNotification('❌ Failed to delete item')
      setTimeout(() => setNotification(null), 2000)
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

  const handleCreateProduct = async () => {
    if (!newProductName.trim()) {
      alert('Please enter a product name')
      return
    }
    if (!newProductCategory) {
      alert('Please select a category (required)')
      return
    }

    try {
      setCreatingProduct(true)
      const response = await api.post('/products', {
        product_name: newProductName.trim(),
        category_id: newProductCategory,
        default_unit: 'units'
      })
      
      console.log('Product created:', response.data)
      
      // Reload products
      await loadAllProducts()
      
      // Add the new product to the shopping list
      const newProduct = response.data
      if (activeList) {
        await addItemToList(newProduct.product_id, undefined, 1)
      }
      
      // Reset form
      setNewProductName('')
      setNewProductCategory('')
      setShowCreateProductModal(false)
      setNewItemText('')
    } catch (error: any) {
      console.error('Error creating product:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to create product. Please try again.'
      alert(errorMessage)
    } finally {
      setCreatingProduct(false)
    }
  }

  const handleSearchChange = (value: string) => {
    setNewItemText(value)
    
    if (!value.trim()) {
      setFilteredProducts([])
      setShowProductSuggestions(false)
      return
    }

    // Filter products by name (case-insensitive)
    const searchTerm = value.toLowerCase().trim()
    const filtered = allProducts.filter(product =>
      product.product_name.toLowerCase().includes(searchTerm)
    )
    
    setFilteredProducts(filtered)
    setShowProductSuggestions(true)
  }

  const handleSelectProduct = async (product: Product) => {
    // Close suggestions immediately for better UX
    setNewItemText('')
    setFilteredProducts([])
    setShowProductSuggestions(false)
    
    // Add product to list
    await addItemToList(product.product_id, undefined, 1)
  }

  const handleFreeTextAdd = async () => {
    if (!newItemText.trim()) {
      return
    }

    // Check if the text exactly matches an existing product name (case-insensitive)
    const exactMatch = allProducts.find(
      p => p.product_name.toLowerCase() === newItemText.trim().toLowerCase()
    )
    
    if (exactMatch) {
      // It's an existing product - add it to the list
      await handleSelectProduct(exactMatch)
      return
    }

    // It's a new product name - open create product modal
    setNewProductName(newItemText.trim())
    setShowCreateProductModal(true)
    setShowProductSuggestions(false)
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
        {/* Notification Toast */}
        <AnimatePresence>
          {notification && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="fixed top-4 right-4 z-50"
            >
              <div className={`${
                notification.startsWith('✓') ? 'bg-green-500' : 'bg-red-500'
              } text-white px-6 py-4 rounded-xl shadow-2xl flex items-center gap-3 max-w-md`}>
                <span className="text-lg font-semibold">{notification}</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

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
                Low Stock Items
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

        {/* All Products Selection Modal */}
        <AnimatePresence>
          {showAllProducts && activeList && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
              // Removed onClick handler - modal only closes via explicit button clicks
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
                    All Products
                  </h3>
                  <button
                    onClick={() => {
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
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer"
                      onClick={async (e) => {
                        e.stopPropagation()
                        await addItemToList(product.product_id, undefined, 1)
                        // Keep modal open so user can add more items
                      }}
                    >
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{product.product_name}</p>
                        <p className="text-sm text-gray-500">{product.category_name}</p>
                      </div>
                      <button
                        onClick={async (e) => {
                          e.stopPropagation()
                          await addItemToList(product.product_id, undefined, 1)
                          // Keep modal open so user can add more items
                        }}
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

        {/* Create Product Modal */}
        <AnimatePresence>
          {showCreateProductModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
              onClick={() => {
                setShowCreateProductModal(false)
                setNewProductName('')
                setNewProductCategory('')
              }}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-white rounded-2xl p-6 max-w-md w-full"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-2xl font-bold text-gray-900">Create New Product</h3>
                  <button
                    onClick={() => {
                      setShowCreateProductModal(false)
                      setNewProductName('')
                      setNewProductCategory('')
                    }}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    <X className="h-6 w-6" />
                  </button>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Product Name <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={newProductName}
                      onChange={(e) => setNewProductName(e.target.value)}
                      placeholder="Enter product name"
                      className="w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900"
                      autoFocus
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Category <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={newProductCategory}
                      onChange={(e) => setNewProductCategory(e.target.value)}
                      className="w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900"
                    >
                      <option value="">Select a category (required)</option>
                      {categories.map((category) => (
                        <option key={category.category_id} value={category.category_id}>
                          {category.category_name}
                        </option>
                      ))}
                    </select>
                    {categories.length === 0 && (
                      <p className="text-xs text-yellow-600 mt-1">
                        No categories available. Please create a category first.
                      </p>
                    )}
                  </div>

                  <div className="flex gap-3 pt-4">
                    <button
                      onClick={() => {
                        setShowCreateProductModal(false)
                        setNewProductName('')
                        setNewProductCategory('')
                      }}
                      className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-xl hover:bg-gray-50 text-gray-700 font-medium transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleCreateProduct}
                      disabled={!newProductName.trim() || !newProductCategory || creatingProduct}
                      className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-medium transition-colors"
                    >
                      {creatingProduct ? 'Creating...' : 'Create & Add'}
                    </button>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Past List View Modal */}
        <AnimatePresence>
          {selectedPastList && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
              onClick={() => setSelectedPastList(null)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-white rounded-2xl p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-2xl font-bold text-gray-900">{selectedPastList.title}</h3>
                  <button
                    onClick={() => setSelectedPastList(null)}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    <X className="h-6 w-6" />
                  </button>
                </div>
                
                <p className="text-sm text-gray-500 mb-4">
                  {new Date(selectedPastList.created_at).toLocaleDateString()}
                </p>
                
                <div className="space-y-2">
                  {selectedPastList.shopping_list_items?.filter(item => item.status === 'BOUGHT').length === 0 ? (
                    <p className="text-gray-500 text-center py-8">No items were bought in this list</p>
                  ) : (
                    selectedPastList.shopping_list_items
                      ?.filter(item => item.status === 'BOUGHT')
                      .map((item) => (
                        <div
                          key={item.shopping_list_item_id}
                          className="p-3 bg-gray-50 rounded-lg"
                        >
                          <p className="font-medium text-gray-900">
                            {item.products?.product_name || item.free_text_name}
                          </p>
                          {item.products?.category_name && (
                            <p className="text-sm text-gray-500">{item.products.category_name}</p>
                          )}
                        </div>
                      ))
                  )}
                </div>
                
                <button
                  onClick={() => setSelectedPastList(null)}
                  className="w-full mt-4 bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300"
                >
                  Close
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

                {/* Add Item Input - Search with Autocomplete */}
                <div className="mb-6">
                  <div className="flex gap-2 relative">
                    <div className="flex-1 relative">
                      <input
                        type="text"
                        value={newItemText}
                        onChange={(e) => handleSearchChange(e.target.value)}
                        onFocus={() => {
                          if (newItemText.trim()) {
                            handleSearchChange(newItemText)
                          } else {
                            // Show all products when focused and empty
                            setFilteredProducts(allProducts)
                            setShowProductSuggestions(true)
                          }
                        }}
                        onBlur={(e) => {
                          // Only hide if focus is moving outside the input and suggestions area
                          // Check if the related target is not within the suggestions dropdown
                          const relatedTarget = e.relatedTarget as HTMLElement
                          if (relatedTarget && !relatedTarget.closest('.product-suggestions-container')) {
                            setTimeout(() => setShowProductSuggestions(false), 200)
                          }
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault()
                            if (filteredProducts.length > 0) {
                              // If there are suggestions, select the first one
                              handleSelectProduct(filteredProducts[0])
                            } else {
                              // No match - try to add or create
                              handleFreeTextAdd()
                            }
                          } else if (e.key === 'Escape') {
                            setShowProductSuggestions(false)
                          }
                        }}
                        placeholder="Search products or type new product name..."
                        className="w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 bg-white"
                      />
                      
                      {/* Product Suggestions Dropdown */}
                      {showProductSuggestions && filteredProducts.length > 0 && (
                        <div className="product-suggestions-container absolute z-10 w-full mt-1 bg-white border-2 border-gray-200 rounded-xl shadow-lg max-h-60 overflow-y-auto">
                          {filteredProducts.map((product) => (
                            <div
                              key={product.product_id}
                              onClick={() => handleSelectProduct(product)}
                              className="px-4 py-3 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0 transition-colors"
                            >
                              <div className="font-medium text-gray-900">{product.product_name}</div>
                              {product.category_name && (
                                <div className="text-sm text-gray-500">{product.category_name}</div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                      
                      {/* Create New Product Option */}
                      {showProductSuggestions && newItemText.trim() && filteredProducts.length === 0 && (
                        <div className="product-suggestions-container absolute z-10 w-full mt-1 bg-white border-2 border-gray-200 rounded-xl shadow-lg">
                          <div
                            onClick={() => {
                              setNewProductName(newItemText.trim())
                              setShowCreateProductModal(true)
                              setShowProductSuggestions(false)
                            }}
                            className="px-4 py-3 hover:bg-green-50 cursor-pointer transition-colors border-b border-gray-100"
                          >
                            <div className="font-medium text-gray-900 flex items-center gap-2">
                              <Plus className="h-4 w-4 text-green-600" />
                              Create new product: "{newItemText.trim()}"
                            </div>
                            <div className="text-sm text-gray-500 mt-1">Click to create and add to list</div>
                          </div>
                        </div>
                      )}
                    </div>
                    <button
                      onClick={handleFreeTextAdd}
                      disabled={!newItemText.trim()}
                      className="bg-blue-600 text-white px-6 py-3 rounded-xl hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2 transition-all"
                    >
                      <Plus className="h-5 w-5" />
                      Add
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    {allProducts.length > 0 
                      ? `${allProducts.length} products available. Search or create a new product.`
                      : 'Type a product name to create a new product (category required).'}
                  </p>
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
                    <AnimatePresence mode="popLayout">
                      {/* Sort items: by priority (desc) then created_at (asc) */}
                      {[...activeList.shopping_list_items]
                        .sort((a, b) => {
                          // Sort by priority (higher first, nulls last)
                          const priorityA = a.priority ?? -1
                          const priorityB = b.priority ?? -1
                          if (priorityA !== priorityB) {
                            return priorityB - priorityA
                          }
                          // Then by created_at (older first)
                          const dateA = new Date(a.created_at || 0).getTime()
                          const dateB = new Date(b.created_at || 0).getTime()
                          return dateA - dateB
                        })
                        .map((item) => (
                        <motion.div
                          key={item.shopping_list_item_id}
                          id={`item-${item.shopping_list_item_id}`}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ 
                            opacity: 1, 
                            x: 0,
                            backgroundColor: recentlyAddedItemId === item.shopping_list_item_id 
                              ? 'rgb(220 252 231)' // green-100
                              : 'rgb(249 250 251)' // gray-50
                          }}
                          exit={{ opacity: 0, x: 20, height: 0 }}
                          transition={{
                            backgroundColor: { duration: 0.3 }
                          }}
                        className={`flex items-center justify-between p-4 rounded-xl hover:bg-gray-100 transition-colors ${
                          recentlyAddedItemId === item.shopping_list_item_id 
                            ? 'ring-2 ring-green-500 shadow-lg' 
                            : ''
                        }`}
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
                          <button
                            onClick={() => deleteItem(item.shopping_list_item_id)}
                            className="text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="h-5 w-5" />
                          </button>
                        </div>
                      </motion.div>
                    ))}
                    </AnimatePresence>
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
                    pastLists.map((list) => {
                      // Count only BOUGHT items
                      const boughtItems = list.shopping_list_items?.filter(item => item.status === 'BOUGHT') || []
                      return (
                        <div
                          key={list.shopping_list_id}
                          onClick={() => setSelectedPastList(list)}
                          className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors"
                        >
                          <p className="font-medium text-gray-900">{list.title}</p>
                          <p className="text-sm text-gray-500">
                            {boughtItems.length} items • {new Date(list.created_at).toLocaleDateString()}
                          </p>
                        </div>
                      )
                    })
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

