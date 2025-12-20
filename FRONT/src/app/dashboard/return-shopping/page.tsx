'use client'

import { useState } from 'react'
import { DashboardLayout } from '@/components/layouts/DashboardLayout'
import { Camera, Upload, CheckCircle, XCircle, Loader2, Package, Plus, Minus } from 'lucide-react'
import axios from 'axios'
import { api } from '@/lib/api'
import { useAuthStore } from '@/store/useAuthStore'

interface ScannedItem {
  product_id: string
  product_name: string
  detected_name: string
  quantity: number
  unit_price?: number
  total_price?: number
  category?: string
  confidence: number
  match_score: number
  is_new_product: boolean
  isSelected: boolean // For UI checkbox
}

interface ScanResult {
  receipt_id: string
  matched_items: ScannedItem[]
  image_url: string
  stats: {
    total_items: number
    new_products: number
    matched_products: number
  }
}

export default function ReturnShoppingPage() {
  const user = useAuthStore((state) => state.user)
  const [isScanning, setIsScanning] = useState(false)
  const [scanResult, setScanResult] = useState<ScanResult | null>(null)
  const [selectedItems, setSelectedItems] = useState<ScannedItem[]>([])
  const [isConfirming, setIsConfirming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [showAddProduct, setShowAddProduct] = useState(false)
  const [allProducts, setAllProducts] = useState<any[]>([])
  const [searchQuery, setSearchQuery] = useState('')

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !user) return

    setIsScanning(true)
    setError(null)
    setScanResult(null)
    setSuccess(false)

    try {
      // Upload and scan receipt
      const formData = new FormData()
      formData.append('file', file)
      formData.append('user_id', user.id)

      const response = await api.post<ScanResult>(
        '/receipts/scan',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      )

      // Initialize all items as selected
      const itemsWithSelection = response.data.matched_items.map(item => ({
        ...item,
        isSelected: true
      }))
      
      setScanResult({
        ...response.data,
        matched_items: itemsWithSelection
      })
      setSelectedItems(itemsWithSelection)
    } catch (err: any) {
      console.error('Error scanning receipt:', err)
      setError(err.response?.data?.detail || 'Failed to scan receipt. Please try again.')
    } finally {
      setIsScanning(false)
    }
  }

  const toggleItemSelection = (productId: string) => {
    if (!scanResult) return

    const updatedItems = scanResult.matched_items.map(item =>
      item.product_id === productId ? { ...item, isSelected: !item.isSelected } : item
    )

    setScanResult({
      ...scanResult,
      matched_items: updatedItems
    })
    setSelectedItems(updatedItems.filter(item => item.isSelected))
  }

  const updateItemQuantity = (productId: string, delta: number) => {
    if (!scanResult) return

    const updatedItems = scanResult.matched_items.map(item =>
      item.product_id === productId
        ? { ...item, quantity: Math.max(0.1, item.quantity + delta) }
        : item
    )

    setScanResult({
      ...scanResult,
      matched_items: updatedItems
    })
    setSelectedItems(updatedItems.filter(item => item.isSelected))
  }

  const removeItem = (productId: string) => {
    if (!scanResult) return

    const updatedItems = scanResult.matched_items.filter(item => item.product_id !== productId)
    
    setScanResult({
      ...scanResult,
      matched_items: updatedItems,
      stats: {
        ...scanResult.stats,
        total_items: updatedItems.length
      }
    })
    setSelectedItems(updatedItems.filter(item => item.isSelected))
  }

  const loadProducts = async () => {
    try {
      const response = await api.get('/products')
      setAllProducts(response.data)
    } catch (error) {
      console.error('Error loading products:', error)
    }
  }

  const addProductToList = (product: any) => {
    if (!scanResult) return

    const newItem: ScannedItem = {
      product_id: product.product_id,
      product_name: product.product_name,
      detected_name: product.product_name,
      quantity: 1,
      category: product.category_name,
      confidence: 1.0,
      match_score: 1.0,
      is_new_product: false,
      isSelected: true
    }

    const updatedItems = [...scanResult.matched_items, newItem]
    
    setScanResult({
      ...scanResult,
      matched_items: updatedItems,
      stats: {
        ...scanResult.stats,
        total_items: updatedItems.length
      }
    })
    setSelectedItems([...selectedItems, newItem])
    setShowAddProduct(false)
    setSearchQuery('')
  }

  const handleConfirm = async () => {
    if (!scanResult || !user || selectedItems.length === 0) return

    setIsConfirming(true)
    setError(null)

    try {
      const confirmed_items = selectedItems.map(item => ({
        product_id: item.product_id,
        quantity: item.quantity,
        unit_price: item.unit_price,
        total_price: item.total_price,
        detected_name: item.detected_name,
        confidence: item.confidence
      }))

      await api.post(
        `/receipts/${scanResult.receipt_id}/confirm?user_id=${user.id}`,
        confirmed_items
      )

      setSuccess(true)
      setTimeout(() => {
        // Reset after success
        setScanResult(null)
        setSelectedItems([])
        setSuccess(false)
      }, 3000)
    } catch (err: any) {
      console.error('Error confirming receipt:', err)
      setError(err.response?.data?.detail || 'Failed to add items to pantry. Please try again.')
    } finally {
      setIsConfirming(false)
    }
  }

  return (
    <DashboardLayout>
      <div className="px-4 py-6 sm:px-0">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Return from Shopping</h1>
          <p className="text-gray-600">Scan your receipt to automatically add items to your pantry</p>
        </div>

        {/* Upload Section */}
        {!scanResult && (
          <div className="bg-white rounded-2xl shadow-md p-8 mb-6">
            <div className="text-center">
              <div className="mb-6">
                <Camera className="w-20 h-20 text-blue-500 mx-auto mb-4" />
                <h2 className="text-2xl font-semibold text-gray-800 mb-2">Scan Receipt</h2>
                <p className="text-gray-600">Upload a photo of your receipt to get started</p>
              </div>

              <label
                htmlFor="receipt-upload"
                className={`inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg text-white transition-all duration-200 ${
                  isScanning
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 shadow-lg hover:shadow-xl cursor-pointer'
                }`}
              >
                {isScanning ? (
                  <>
                    <Loader2 className="animate-spin -ml-1 mr-3 h-5 w-5" />
                    Scanning Receipt...
                  </>
                ) : (
                  <>
                    <Upload className="mr-2 h-5 w-5" />
                    Upload Receipt
                  </>
                )}
              </label>
              <input
                id="receipt-upload"
                type="file"
                accept="image/*"
                onChange={handleFileUpload}
                disabled={isScanning}
                className="hidden"
              />
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6 rounded-lg">
            <div className="flex items-center">
              <XCircle className="h-5 w-5 text-red-500 mr-2" />
              <p className="text-red-700">{error}</p>
            </div>
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="bg-green-50 border-l-4 border-green-500 p-4 mb-6 rounded-lg animate-fade-in">
            <div className="flex items-center">
              <CheckCircle className="h-5 w-5 text-green-500 mr-2" />
              <p className="text-green-700 font-medium">Items successfully added to your pantry!</p>
            </div>
          </div>
        )}

        {/* Scan Results */}
        {scanResult && !success && (
          <div className="space-y-6">
            {/* Receipt Info Card */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-2xl p-6 shadow-md">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold text-gray-900">Receipt Scanned Successfully! 🎉</h2>
                <button
                  onClick={() => setScanResult(null)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  <XCircle className="h-6 w-6" />
                </button>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <p className="text-sm text-gray-600 mb-1">Total Items</p>
                  <p className="text-2xl font-bold text-gray-900">{scanResult.stats.total_items}</p>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <p className="text-sm text-gray-600 mb-1">Matched</p>
                  <p className="text-2xl font-bold text-green-600">{scanResult.stats.matched_products}</p>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <p className="text-sm text-gray-600 mb-1">New Products</p>
                  <p className="text-2xl font-bold text-blue-600">{scanResult.stats.new_products}</p>
                </div>
              </div>
            </div>

            {/* Items List */}
            <div className="bg-white rounded-2xl shadow-md p-6">
              <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                <Package className="mr-2 h-6 w-6 text-blue-600" />
                Review Items ({selectedItems.length} selected)
              </h3>
              <p className="text-sm text-gray-600 mb-6">
                Review and adjust items before adding to your pantry. Uncheck items you don't want to add.
              </p>

              <div className="space-y-3 max-h-[500px] overflow-y-auto">
                {scanResult.matched_items.map((item) => (
                  <div
                    key={item.product_id}
                    className={`border rounded-xl p-4 transition-all duration-200 ${
                      item.isSelected
                        ? 'border-blue-300 bg-blue-50'
                        : 'border-gray-200 bg-gray-50 opacity-60'
                    }`}
                  >
                    <div className="flex items-start">
                      {/* Checkbox */}
                      <input
                        type="checkbox"
                        checked={item.isSelected}
                        onChange={() => toggleItemSelection(item.product_id)}
                        className="mt-1 mr-4 h-5 w-5 text-blue-600 rounded cursor-pointer"
                      />

                      {/* Item Details */}
                      <div className="flex-1">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <h4 className="font-semibold text-gray-900">{item.product_name}</h4>
                            {item.detected_name !== item.product_name && (
                              <p className="text-sm text-gray-500 italic">Detected as: {item.detected_name}</p>
                            )}
                          </div>
                          {item.is_new_product && (
                            <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
                              New
                            </span>
                          )}
                        </div>

                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-4">
                            {/* Quantity Controls - More Visible */}
                            <div className="flex items-center space-x-2 bg-gradient-to-r from-blue-50 to-indigo-50 px-4 py-2 rounded-xl border-2 border-blue-200">
                              <span className="text-sm font-semibold text-gray-700">Quantity:</span>
                              <button
                                onClick={() => updateItemQuantity(item.product_id, -0.5)}
                                disabled={!item.isSelected}
                                className="p-1.5 rounded-lg bg-blue-200 hover:bg-blue-300 disabled:opacity-30 disabled:cursor-not-allowed text-blue-800 font-bold"
                              >
                                <Minus className="h-4 w-4" />
                              </button>
                              <span className="font-medium text-gray-900 min-w-[50px] text-center">
                                {item.quantity.toFixed(1)}x
                              </span>
                              <button
                                onClick={() => updateItemQuantity(item.product_id, 0.5)}
                                disabled={!item.isSelected}
                                className="p-1.5 rounded-lg bg-blue-200 hover:bg-blue-300 disabled:opacity-30 disabled:cursor-not-allowed text-blue-800 font-bold"
                              >
                                <Plus className="h-4 w-4" />
                              </button>
                            </div>

                            {/* Price */}
                            {item.total_price && (
                              <span className="text-sm text-gray-600">
                                ${item.total_price.toFixed(2)}
                              </span>
                            )}
                          </div>

                          {/* Remove Button */}
                          <button
                            onClick={() => removeItem(item.product_id)}
                            className="p-2 rounded-lg bg-red-100 hover:bg-red-200 text-red-600 transition-colors"
                            title="Remove item"
                          >
                            <XCircle className="h-5 w-5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Add Product Button */}
              <div className="mt-6">
                {!showAddProduct ? (
                  <button
                    onClick={() => {
                      setShowAddProduct(true)
                      loadProducts()
                    }}
                    className="w-full py-3 border-2 border-dashed border-gray-300 rounded-xl text-gray-600 hover:border-blue-500 hover:text-blue-600 hover:bg-blue-50 transition-all flex items-center justify-center gap-2 font-medium"
                  >
                    <Plus className="h-5 w-5" />
                    Add More Products
                  </button>
                ) : (
                  <div className="border-2 border-blue-300 rounded-xl p-4 bg-blue-50">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-semibold text-gray-900">Add Product</h4>
                      <button
                        onClick={() => {
                          setShowAddProduct(false)
                          setSearchQuery('')
                        }}
                        className="text-gray-500 hover:text-gray-700"
                      >
                        <XCircle className="h-5 w-5" />
                      </button>
                    </div>
                    
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search products..."
                      className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 text-gray-900 mb-3"
                    />

                    <div className="max-h-60 overflow-y-auto space-y-2">
                      {allProducts
                        .filter((product) =>
                          product.product_name.toLowerCase().includes(searchQuery.toLowerCase())
                        )
                        .map((product) => (
                          <button
                            key={product.product_id}
                            onClick={() => addProductToList(product)}
                            className="w-full text-left px-4 py-3 bg-white hover:bg-blue-100 rounded-lg border border-gray-200 hover:border-blue-300 transition-colors"
                          >
                            <p className="font-medium text-gray-900">{product.product_name}</p>
                            <p className="text-sm text-gray-500">{product.category_name}</p>
                          </button>
                        ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Confirm Button */}
              <div className="mt-6 flex gap-4">
                <button
                  onClick={() => setScanResult(null)}
                  className="flex-1 py-3 px-6 bg-gray-200 text-gray-700 rounded-xl hover:bg-gray-300 font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirm}
                  disabled={selectedItems.length === 0 || isConfirming}
                  className="flex-1 py-3 px-6 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-xl hover:from-green-700 hover:to-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-all shadow-lg flex items-center justify-center gap-2"
                >
                  {isConfirming ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      Adding to Pantry...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="h-5 w-5" />
                      Add {selectedItems.length} Items to Pantry
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
