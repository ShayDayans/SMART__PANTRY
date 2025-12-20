'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/useAuthStore'
import { DashboardLayout } from '@/components/layouts/DashboardLayout'
import { api } from '@/lib/api'
import { Search, Save, ArrowRight, Package } from 'lucide-react'

interface Product {
  product_id: string
  product_name: string
  category_id?: string
  default_unit?: string
}

type InventoryState = 'EMPTY' | 'LOW' | 'MEDIUM' | 'FULL'

const stateConfig = {
  FULL: { label: 'Full (¾+)', color: 'bg-green-500', value: 12 },
  MEDIUM: { label: 'Medium (½)', color: 'bg-yellow-500', value: 37 },
  LOW: { label: 'Low (¼)', color: 'bg-orange-500', value: 62 },
  EMPTY: { label: 'Empty', color: 'bg-red-500', value: 87 },
}

export default function AddToPantryPage() {
  const router = useRouter()
  const { user, loading } = useAuthStore()
  
  const [products, setProducts] = useState<Product[]>([])
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)
  const [showDropdown, setShowDropdown] = useState(false)
  
  const [inventoryState, setInventoryState] = useState<InventoryState>('MEDIUM')
  const [quantity, setQuantity] = useState<number>(1)
  const [unit, setUnit] = useState<string>('units')
  const [displayName, setDisplayName] = useState('')
  
  const [saving, setSaving] = useState(false)
  const [loadingProducts, setLoadingProducts] = useState(true)

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  useEffect(() => {
    if (user) {
      loadProducts()
    }
  }, [user])

  useEffect(() => {
    if (searchQuery.trim()) {
      const filtered = products.filter((p) =>
        p.product_name.toLowerCase().includes(searchQuery.toLowerCase())
      )
      setFilteredProducts(filtered.slice(0, 10))
      setShowDropdown(true)
    } else {
      setFilteredProducts([])
      setShowDropdown(false)
    }
  }, [searchQuery, products])

  const loadProducts = async () => {
    try {
      setLoadingProducts(true)
      const response = await api.get('/products')
      setProducts(response.data)
    } catch (error) {
      console.error('Error loading products:', error)
    } finally {
      setLoadingProducts(false)
    }
  }

  const selectProduct = (product: Product) => {
    setSelectedProduct(product)
    setSearchQuery(product.product_name)
    setDisplayName(product.product_name)
    setUnit(product.default_unit || 'units')
    setShowDropdown(false)
  }

  const getStateFromSlider = (value: number): InventoryState => {
    if (value < 25) return 'FULL'
    if (value < 50) return 'MEDIUM'
    if (value < 75) return 'LOW'
    return 'EMPTY'
  }

  const handleStateSliderChange = (value: number) => {
    const newState = getStateFromSlider(value)
    setInventoryState(newState)
  }

  const handleSave = async () => {
    if (!selectedProduct) {
      alert('Please select a product')
      return
    }

    try {
      setSaving(true)
      
      const inventoryData = {
        product_id: selectedProduct.product_id,
        state: inventoryState,
        estimated_qty: quantity,
        qty_unit: unit,
        confidence: 1.0,
        last_source: 'MANUAL',
        displayed_name: displayName || selectedProduct.product_name,
      }

      await api.post(`/inventory?user_id=${user?.id}`, inventoryData)
      
      alert('Item added to pantry successfully!')
      router.push('/dashboard/pantry')
    } catch (error) {
      console.error('Error saving to pantry:', error)
      alert('Failed to add item to pantry')
    } finally {
      setSaving(false)
    }
  }

  if (loadingProducts) {
    return (
      <DashboardLayout>
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="px-4 py-6 sm:px-0 max-w-2xl mx-auto">
        <div className="flex items-center mb-6">
          <Package className="w-8 h-8 text-blue-600 mr-3" />
          <h1 className="text-3xl font-bold text-gray-900">Add to Pantry</h1>
        </div>

        <div className="bg-white shadow-lg rounded-lg p-6 space-y-6">
          {/* Product Search */}
          <div className="relative">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search Product *
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => searchQuery && setShowDropdown(true)}
                placeholder="Type to search products..."
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Dropdown */}
            {showDropdown && filteredProducts.length > 0 && (
              <div className="absolute z-10 mt-1 w-full bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                {filteredProducts.map((product) => (
                  <button
                    key={product.product_id}
                    onClick={() => selectProduct(product)}
                    className="w-full text-left px-4 py-3 hover:bg-blue-50 border-b border-gray-100 last:border-b-0 transition-colors"
                  >
                    <div className="font-medium text-gray-900">{product.product_name}</div>
                    {product.default_unit && (
                      <div className="text-sm text-gray-500">Default unit: {product.default_unit}</div>
                    )}
                  </button>
                ))}
              </div>
            )}

            {selectedProduct && (
              <div className="mt-2 flex items-center text-sm text-green-600">
                <span className="mr-2">✓</span>
                Selected: {selectedProduct.product_name}
              </div>
            )}
          </div>

          {/* Display Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Display Name (Optional)
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Custom name for this item"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder:text-gray-400"
            />
          </div>

          {/* State Slider with Visual Indicator */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Stock Level *
            </label>
            
            {/* Visual State Bar */}
            <div className="relative mb-4">
              <div className="flex h-12 rounded-lg overflow-hidden border-2 border-gray-300">
                {['FULL', 'MEDIUM', 'LOW', 'EMPTY'].map((key) => (
                  <div
                    key={key}
                    className={`flex-1 ${stateConfig[key as InventoryState].color} ${
                      inventoryState === key ? 'ring-4 ring-blue-500 ring-inset' : 'opacity-50'
                    } transition-all duration-200`}
                  />
                ))}
              </div>
              <div className="flex justify-between mt-2 text-xs text-gray-600">
                <span>Full</span>
                <span>Medium</span>
                <span>Low</span>
                <span>Empty</span>
              </div>
            </div>

            {/* Slider */}
            <input
              type="range"
              min="0"
              max="100"
              value={stateConfig[inventoryState].value}
              onChange={(e) => handleStateSliderChange(parseInt(e.target.value))}
              className="w-full h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
              style={{
                background: `linear-gradient(to right, 
                  rgb(34, 197, 94) 0%, 
                  rgb(34, 197, 94) 24%, 
                  rgb(234, 179, 8) 25%, 
                  rgb(234, 179, 8) 49%, 
                  rgb(249, 115, 22) 50%, 
                  rgb(249, 115, 22) 74%, 
                  rgb(239, 68, 68) 75%, 
                  rgb(239, 68, 68) 100%)`
              }}
            />

            {/* Selected State Display */}
            <div className="mt-3 text-center">
              <span className={`inline-block px-4 py-2 rounded-full text-white font-semibold ${stateConfig[inventoryState].color}`}>
                {stateConfig[inventoryState].label}
              </span>
            </div>
          </div>

          {/* Quantity Slider */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Quantity: <span className="text-blue-600 font-bold">{quantity}</span>
            </label>
            <input
              type="range"
              min="0"
              max="100"
              step="0.5"
              value={quantity}
              onChange={(e) => setQuantity(parseFloat(e.target.value))}
              className="w-full h-2 bg-blue-200 rounded-lg appearance-none cursor-pointer"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0</span>
              <span>50</span>
              <span>100</span>
            </div>
          </div>

          {/* Unit */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Unit
            </label>
            <select
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900"
            >
              <option value="units">Units</option>
              <option value="kg">Kilograms (kg)</option>
              <option value="g">Grams (g)</option>
              <option value="liters">Liters</option>
              <option value="ml">Milliliters (ml)</option>
              <option value="pieces">Pieces</option>
              <option value="packages">Packages</option>
              <option value="days">Days</option>
            </select>
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-3 pt-4">
            <button
              onClick={handleSave}
              disabled={!selectedProduct || saving}
              className="flex-1 bg-blue-600 text-white px-6 py-3 rounded-lg flex items-center justify-center hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-semibold"
            >
              {saving ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-5 h-5 mr-2" />
                  Add to Pantry
                </>
              )}
            </button>
            <button
              onClick={() => router.push('/dashboard/pantry')}
              className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>

        {/* Help Text */}
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h3 className="font-semibold text-blue-900 mb-2">Tips:</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• Use the state slider to indicate how full the item is</li>
            <li>• Quantity represents the exact amount you have</li>
            <li>• Display name is optional - useful for custom labeling</li>
          </ul>
        </div>
      </div>

      <style jsx>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background: white;
          border: 3px solid #2563eb;
          cursor: pointer;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }

        .slider::-moz-range-thumb {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background: white;
          border: 3px solid #2563eb;
          cursor: pointer;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
      `}</style>
    </DashboardLayout>
  )
}

