'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/useAuthStore'
import { DashboardLayout } from '@/components/layouts/DashboardLayout'
import { api } from '@/lib/api'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  ChefHat, 
  Users, 
  Clock, 
  UtensilsCrossed, 
  Sparkles,
  Loader2,
  CheckCircle,
  X,
  ArrowRight,
  ArrowLeft,
  Play,
  Check,
  ChefHat as CookingIcon
} from 'lucide-react'

interface Recipe {
  title: string
  description: string
  servings: number
  prep_time: string
  cook_time: string
  total_time: string
  difficulty: string
  ingredients: Array<{
    name: string
    amount: string
    notes?: string
  }>
  instructions: string[]
  tips?: string[]
  nutrition_info?: {
    calories_per_serving: number
    protein: string
    carbs: string
    fat: string
  }
  meal_type?: string
  cuisine_style?: string
  suggested_additional_ingredients?: string[]
}

export default function RecipesPage() {
  const router = useRouter()
  const { user, loading } = useAuthStore()
  
  const [step, setStep] = useState<'meal-type' | 'preferences' | 'recipe'>('meal-type')
  const [mealType, setMealType] = useState('')
  const [cuisineStyle, setCuisineStyle] = useState('')
  const [servings, setServings] = useState(4)
  const [dietaryPreferences, setDietaryPreferences] = useState<string[]>([])
  const [cookingTime, setCookingTime] = useState('')
  const [difficulty, setDifficulty] = useState('')
  const [recipe, setRecipe] = useState<Recipe | null>(null)
  const [loadingRecipe, setLoadingRecipe] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Cooking mode state
  const [isCooking, setIsCooking] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set())
  const [inventoryItems, setInventoryItems] = useState<any[]>([])

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  const mealTypes = [
    { value: 'breakfast', label: 'Breakfast', icon: '🌅' },
    { value: 'lunch', label: 'Lunch', icon: '🌞' },
    { value: 'dinner', label: 'Dinner', icon: '🌙' },
    { value: 'snack', label: 'Snack', icon: '🍪' },
    { value: 'dessert', label: 'Dessert', icon: '🍰' },
  ]

  const cuisineStyles = [
    'Italian', 'Asian', 'Mediterranean', 'Mexican', 'Indian',
    'American', 'French', 'Japanese', 'Thai', 'Middle Eastern',
    'Greek', 'Spanish', 'Chinese', 'Korean', 'Vietnamese'
  ]

  const dietaryOptions = [
    'Vegetarian', 'Vegan', 'Gluten-Free', 'Dairy-Free', 
    'Keto', 'Paleo', 'Low-Carb', 'High-Protein', 'Nut-Free'
  ]

  const cookingTimes = [
    '15 minutes', '30 minutes', '45 minutes', '1 hour', '1.5 hours', '2+ hours'
  ]

  const difficultyLevels = ['Easy', 'Medium', 'Hard']

  const toggleDietaryPreference = (pref: string) => {
    setDietaryPreferences(prev => 
      prev.includes(pref) 
        ? prev.filter(p => p !== pref)
        : [...prev, pref]
    )
  }

  const handleGenerateRecipe = async () => {
    if (!mealType) {
      setError('Please select a meal type')
      return
    }

    setLoadingRecipe(true)
    setError(null)
    setStep('recipe')

    try {
      const response = await api.post('/recipes/generate', {
        meal_type: mealType,
        cuisine_style: cuisineStyle || undefined,
        servings: servings,
        dietary_preferences: dietaryPreferences.length > 0 ? dietaryPreferences : undefined,
        cooking_time: cookingTime || undefined,
        difficulty: difficulty || undefined,
      })

      // Ensure ingredients is an array and each ingredient has the correct structure
      const recipeData = response.data
      console.log('Raw recipe data from API:', JSON.stringify(recipeData, null, 2))
      
      if (recipeData.ingredients && Array.isArray(recipeData.ingredients)) {
        recipeData.ingredients = recipeData.ingredients.map((ing: any, idx: number) => {
          console.log(`Processing ingredient ${idx}:`, ing, typeof ing)
          
          // Handle case where ingredient might be a string or object
          if (typeof ing === 'string') {
            return { name: ing, amount: '', notes: '' }
          }
          if (typeof ing === 'object' && ing !== null) {
            // Ensure all values are strings - handle nested objects too
            const nameValue = ing.name || ing.ingredient || ing.title || ''
            const amountValue = ing.amount || ing.quantity || ''
            const notesValue = ing.notes || ing.note || ''
            
            // Convert to strings, handling nested objects
            let nameStr = 'Unknown ingredient'
            if (nameValue) {
              if (typeof nameValue === 'string') {
                nameStr = nameValue
              } else if (typeof nameValue === 'object') {
                nameStr = String(nameValue.name || nameValue.ingredient || nameValue || 'Unknown ingredient')
              } else {
                nameStr = String(nameValue)
              }
            }
            
            let amountStr = ''
            if (amountValue) {
              if (typeof amountValue === 'string') {
                amountStr = amountValue
              } else if (typeof amountValue === 'object') {
                amountStr = String(amountValue.value || amountValue.amount || amountValue || '')
              } else {
                amountStr = String(amountValue)
              }
            }
            
            let notesStr = ''
            if (notesValue) {
              if (typeof notesValue === 'string') {
                notesStr = notesValue
              } else if (typeof notesValue === 'object') {
                notesStr = String(notesValue.note || notesValue.notes || notesValue || '')
              } else {
                notesStr = String(notesValue)
              }
            }
            
            const result = {
              name: nameStr,
              amount: amountStr,
              notes: notesStr
            }
            console.log(`Processed ingredient ${idx}:`, result)
            return result
          }
          return { name: String(ing || 'Unknown ingredient'), amount: '', notes: '' }
        })
      } else {
        recipeData.ingredients = []
      }
      
      console.log('Final processed ingredients:', recipeData.ingredients)

      // Ensure instructions is an array of strings
      if (Array.isArray(recipeData.instructions)) {
        recipeData.instructions = recipeData.instructions.map((inst: any) => 
          typeof inst === 'string' ? inst : String(inst || '')
        )
      } else {
        recipeData.instructions = []
      }

      // Ensure tips is an array of strings
      if (Array.isArray(recipeData.tips)) {
        recipeData.tips = recipeData.tips.map((tip: any) => 
          typeof tip === 'string' ? tip : String(tip || '')
        )
      } else if (recipeData.tips) {
        recipeData.tips = []
      }

      // Ensure all string fields are strings
      recipeData.title = String(recipeData.title || 'Untitled Recipe')
      recipeData.description = String(recipeData.description || '')
      recipeData.prep_time = String(recipeData.prep_time || '')
      recipeData.cook_time = String(recipeData.cook_time || '')
      recipeData.total_time = String(recipeData.total_time || '')
      recipeData.difficulty = String(recipeData.difficulty || 'medium')

      // Ensure suggested_additional_ingredients is an array of strings
      if (Array.isArray(recipeData.suggested_additional_ingredients)) {
        recipeData.suggested_additional_ingredients = recipeData.suggested_additional_ingredients.map((ing: any) => {
          if (typeof ing === 'string') {
            return ing
          }
          if (typeof ing === 'object' && ing !== null) {
            return String(ing.name || ing.ingredient || ing || 'Unknown')
          }
          return String(ing || 'Unknown')
        })
      } else if (recipeData.suggested_additional_ingredients) {
        recipeData.suggested_additional_ingredients = []
      }

      setRecipe(recipeData)
    } catch (err: any) {
      console.error('Error generating recipe:', err)
      setError(err.response?.data?.detail || 'Failed to generate recipe. Please try again.')
      setStep('preferences')
    } finally {
      setLoadingRecipe(false)
    }
  }

  const handleReset = () => {
    setStep('meal-type')
    setMealType('')
    setCuisineStyle('')
    setServings(4)
    setDietaryPreferences([])
    setCookingTime('')
    setDifficulty('')
    setRecipe(null)
    setError(null)
    setIsCooking(false)
    setCurrentStep(0)
    setCompletedSteps(new Set())
  }

  const loadInventory = async () => {
    try {
      const response = await api.get('/inventory')
      setInventoryItems(response.data || [])
    } catch (error) {
      console.error('Error loading inventory:', error)
      setInventoryItems([])
    }
  }

  const findProductInInventory = (ingredientName: string): any | null => {
    // Try to find product by name (fuzzy match)
    const nameLower = ingredientName.toLowerCase().trim()
    
    for (const item of inventoryItems) {
      const productName = item.products?.product_name?.toLowerCase() || ''
      const displayedName = item.displayed_name?.toLowerCase() || ''
      
      // Exact match or contains
      if (productName.includes(nameLower) || nameLower.includes(productName) ||
          displayedName.includes(nameLower) || nameLower.includes(displayedName)) {
        return item
      }
    }
    
    return null
  }

  const updateInventoryAfterStep = async (stepIndex: number) => {
    if (!recipe || !recipe.ingredients) return

    try {
      // Prepare ingredients used in this step
      const ingredientsUsed = recipe.ingredients.map((ingredient: any) => {
        const ingredientName = typeof ingredient === 'string' 
          ? ingredient 
          : (typeof ingredient === 'object' && ingredient !== null ? (ingredient.name || '') : '')
        
        if (!ingredientName) return null
        
        const inventoryItem = findProductInInventory(ingredientName)
        if (!inventoryItem || !inventoryItem.product_id) return null
        
        // Calculate amount used (simplified: 10% per step)
        const currentQty = inventoryItem.estimated_qty || 0
        const totalSteps = recipe.instructions.length
        const amountUsed = currentQty / totalSteps
        
        return {
          ingredient_name: ingredientName,
          amount_used: amountUsed,
          step_index: stepIndex
        }
      }).filter((item: any) => item !== null)
      
      // Call backend endpoint to update inventory and model
      try {
        const response = await api.post('/recipes/step-complete', {
          step_index: stepIndex,
          ingredients_used: ingredientsUsed
        })
        
        console.log('Step completed, inventory updated:', response.data)
        
        // Reload inventory to get updated quantities
        await loadInventory()
      } catch (err) {
        console.error('Error updating inventory via API:', err)
        // Fallback: try direct update (without model update)
        for (const ingredient of recipe.ingredients) {
          const ingredientName = typeof ingredient === 'string' 
            ? ingredient 
            : (typeof ingredient === 'object' && ingredient !== null ? (ingredient.name || '') : '')
          
          if (!ingredientName) continue
          
          const inventoryItem = findProductInInventory(ingredientName)
          if (!inventoryItem || !inventoryItem.product_id) continue
          
          const currentQty = inventoryItem.estimated_qty || 0
          const totalSteps = recipe.instructions.length
          const newQty = Math.max(0, currentQty - (currentQty / totalSteps))
          
          try {
            await api.put(`/inventory/${inventoryItem.product_id}`, {
              estimated_qty: newQty,
              state: newQty <= 0 ? 'EMPTY' : (newQty < currentQty * 0.3 ? 'LOW' : inventoryItem.state)
            })
          } catch (updateErr) {
            console.error(`Error updating inventory for ${ingredientName}:`, updateErr)
          }
        }
        await loadInventory()
      }
    } catch (error) {
      console.error('Error updating inventory:', error)
    }
  }

  const handleStartCooking = async () => {
    await loadInventory()
    setIsCooking(true)
    setCurrentStep(0)
    setCompletedSteps(new Set())
  }

  const handleStepComplete = async (stepIndex: number) => {
    // Mark step as completed
    setCompletedSteps(prev => new Set(Array.from(prev).concat([stepIndex])))
    
    // Update inventory after completing step
    await updateInventoryAfterStep(stepIndex)
    
    // Move to next step
    if (stepIndex < (recipe?.instructions.length || 0) - 1) {
      setCurrentStep(stepIndex + 1)
    } else {
      // Recipe completed!
      setIsCooking(false)
      setCurrentStep(0)
    }
  }

  const handleFinishCooking = () => {
    setIsCooking(false)
    setCurrentStep(0)
    setCompletedSteps(new Set())
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
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-orange-500 to-red-500 rounded-xl flex items-center justify-center shadow-lg">
              <ChefHat className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-orange-600 to-red-600 bg-clip-text text-transparent">
                Recipe Generator
              </h1>
              <p className="text-gray-600">Get personalized recipes based on your pantry</p>
            </div>
          </div>
        </motion.div>

        <AnimatePresence mode="wait">
          {step === 'meal-type' && (
            <motion.div
              key="meal-type"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="bg-white rounded-2xl shadow-xl p-8"
            >
              <h2 className="text-2xl font-bold mb-6 text-gray-800">What would you like to cook?</h2>
              
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
                {mealTypes.map((type) => (
                  <button
                    key={type.value}
                    onClick={() => {
                      setMealType(type.value)
                      setStep('preferences')
                    }}
                    className={`p-6 rounded-xl border-2 transition-all ${
                      mealType === type.value
                        ? 'border-orange-500 bg-orange-50'
                        : 'border-gray-200 hover:border-orange-300 hover:bg-gray-50'
                    }`}
                  >
                    <div className="text-4xl mb-2">{type.icon}</div>
                    <div className="font-semibold text-gray-800">{type.label}</div>
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {step === 'preferences' && (
            <motion.div
              key="preferences"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="bg-white rounded-2xl shadow-xl p-8"
            >
              <button
                onClick={() => setStep('meal-type')}
                className="flex items-center gap-2 text-gray-600 hover:text-gray-800 mb-6"
              >
                <ArrowLeft className="w-4 h-4" />
                Back
              </button>

              <h2 className="text-2xl font-bold mb-6 text-gray-800">Customize Your Recipe</h2>

              {/* Servings */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  Number of Servings
                </label>
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => setServings(Math.max(1, servings - 1))}
                    className="w-10 h-10 rounded-lg border-2 border-gray-300 hover:border-orange-500 flex items-center justify-center text-black font-bold text-xl"
                  >
                    -
                  </button>
                  <span className="text-2xl font-bold w-12 text-center text-black">{servings}</span>
                  <button
                    onClick={() => setServings(Math.min(20, servings + 1))}
                    className="w-10 h-10 rounded-lg border-2 border-gray-300 hover:border-orange-500 flex items-center justify-center text-black font-bold text-xl"
                  >
                    +
                  </button>
                </div>
              </div>

              {/* Cuisine Style */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Cuisine Style (Optional)
                </label>
                <select
                  value={cuisineStyle}
                  onChange={(e) => setCuisineStyle(e.target.value)}
                  className="w-full p-3 rounded-lg border-2 border-gray-300 focus:border-orange-500 focus:outline-none"
                >
                  <option value="">Any Style</option>
                  {cuisineStyles.map((style) => (
                    <option key={style} value={style.toLowerCase()}>{style}</option>
                  ))}
                </select>
              </div>

              {/* Dietary Preferences */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Dietary Preferences (Optional)
                </label>
                <div className="flex flex-wrap gap-2">
                  {dietaryOptions.map((option) => (
                    <button
                      key={option}
                      onClick={() => toggleDietaryPreference(option)}
                      className={`px-4 py-2 rounded-lg border-2 transition-all ${
                        dietaryPreferences.includes(option)
                          ? 'border-orange-500 bg-orange-50 text-orange-700'
                          : 'border-gray-300 hover:border-orange-300 text-gray-700'
                      }`}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </div>

              {/* Cooking Time */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  Cooking Time (Optional)
                </label>
                <select
                  value={cookingTime}
                  onChange={(e) => setCookingTime(e.target.value)}
                  className="w-full p-3 rounded-lg border-2 border-gray-300 focus:border-orange-500 focus:outline-none"
                >
                  <option value="">Any Time</option>
                  {cookingTimes.map((time) => (
                    <option key={time} value={time}>{time}</option>
                  ))}
                </select>
              </div>

              {/* Difficulty */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Difficulty Level (Optional)
                </label>
                <div className="flex gap-2">
                  {difficultyLevels.map((level) => (
                    <button
                      key={level}
                      onClick={() => setDifficulty(level.toLowerCase())}
                      className={`flex-1 p-3 rounded-lg border-2 transition-all ${
                        difficulty === level.toLowerCase()
                          ? 'border-orange-500 bg-orange-50 text-orange-700'
                          : 'border-gray-300 hover:border-orange-300 text-gray-700'
                      }`}
                    >
                      {level}
                    </button>
                  ))}
                </div>
              </div>

              {error && (
                <div className="mb-6 p-4 bg-red-50 border-2 border-red-200 rounded-lg text-red-700">
                  {error}
                </div>
              )}

              <button
                onClick={handleGenerateRecipe}
                disabled={loadingRecipe}
                className="w-full py-4 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-xl font-semibold text-lg hover:from-orange-600 hover:to-red-600 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {loadingRecipe ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Generating Recipe...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    Generate Recipe
                  </>
                )}
              </button>
            </motion.div>
          )}

          {step === 'recipe' && recipe && (
            <motion.div
              key="recipe"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="bg-white rounded-2xl shadow-xl p-8"
            >
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h2 className="text-3xl font-bold mb-2 text-gray-800">{recipe.title}</h2>
                  <p className="text-gray-600">{recipe.description}</p>
                </div>
                <button
                  onClick={handleReset}
                  className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg"
                  title="Generate New Recipe"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Recipe Info */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="p-4 bg-blue-50 rounded-lg">
                  <div className="text-sm text-gray-600 mb-1">Servings</div>
                  <div className="text-2xl font-bold text-blue-600">{recipe.servings}</div>
                </div>
                <div className="p-4 bg-green-50 rounded-lg">
                  <div className="text-sm text-gray-600 mb-1">Prep Time</div>
                  <div className="text-2xl font-bold text-green-600">{recipe.prep_time}</div>
                </div>
                <div className="p-4 bg-purple-50 rounded-lg">
                  <div className="text-sm text-gray-600 mb-1">Cook Time</div>
                  <div className="text-2xl font-bold text-purple-600">{recipe.cook_time}</div>
                </div>
                <div className="p-4 bg-orange-50 rounded-lg">
                  <div className="text-sm text-gray-600 mb-1">Difficulty</div>
                  <div className="text-2xl font-bold text-orange-600 capitalize">{recipe.difficulty}</div>
                </div>
              </div>

              {/* Ingredients */}
              <div className="mb-6">
                <h3 className="text-xl font-bold mb-4 text-gray-800 flex items-center gap-2">
                  <UtensilsCrossed className="w-5 h-5" />
                  Ingredients
                </h3>
                <ul className="space-y-2">
                  {Array.isArray(recipe.ingredients) && recipe.ingredients.map((ingredient: any, index: number) => {
                    // Handle different ingredient formats safely
                    let name = 'Unknown ingredient'
                    let amount = ''
                    let notes = ''

                    if (typeof ingredient === 'string') {
                      name = ingredient
                    } else if (typeof ingredient === 'object' && ingredient !== null) {
                      // Safely extract name, amount, and notes - ensure they are all strings
                      const nameValue = ingredient.name || ingredient.ingredient || ingredient.title
                      const amountValue = ingredient.amount || ingredient.quantity
                      const notesValue = ingredient.notes || ingredient.note
                      
                      name = nameValue ? (typeof nameValue === 'string' ? nameValue : String(nameValue)) : 'Unknown ingredient'
                      amount = amountValue ? (typeof amountValue === 'string' ? amountValue : String(amountValue)) : ''
                      notes = notesValue ? (typeof notesValue === 'string' ? notesValue : String(notesValue)) : ''
                    } else {
                      name = String(ingredient || 'Unknown ingredient')
                    }
                    
                    // Final safety check - ensure all are strings
                    name = String(name || 'Unknown ingredient')
                    amount = amount ? String(amount) : ''
                    notes = notes ? String(notes) : ''

                    return (
                      <li key={index} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                        <CheckCircle className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                        <div>
                          <span className="font-semibold text-gray-800">{name}</span>
                          {amount && <span className="text-gray-600"> - {amount}</span>}
                          {notes && (
                            <span className="text-sm text-gray-500 italic"> ({notes})</span>
                          )}
                        </div>
                      </li>
                    )
                  })}
                </ul>
              </div>

              {/* Instructions */}
              <div className="mb-6">
                <h3 className="text-xl font-bold mb-4 text-gray-800">Instructions</h3>
                <ol className="space-y-4">
                  {recipe.instructions.map((instruction, index) => (
                    <li key={index} className="flex gap-4">
                      <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-orange-500 to-red-500 text-white rounded-full flex items-center justify-center font-bold">
                        {index + 1}
                      </div>
                      <p className="text-gray-700 leading-relaxed pt-1">{instruction}</p>
                    </li>
                  ))}
                </ol>
              </div>

              {/* Tips */}
              {recipe.tips && recipe.tips.length > 0 && (
                <div className="mb-6 p-4 bg-yellow-50 border-l-4 border-yellow-400 rounded-lg">
                  <h3 className="text-lg font-bold mb-2 text-gray-800">Tips</h3>
                  <ul className="space-y-1">
                    {recipe.tips.map((tip, index) => (
                      <li key={index} className="text-gray-700">• {tip}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Suggested Additional Ingredients */}
              {recipe.suggested_additional_ingredients && Array.isArray(recipe.suggested_additional_ingredients) && recipe.suggested_additional_ingredients.length > 0 && (
                <div className="mb-6 p-4 bg-blue-50 border-l-4 border-blue-400 rounded-lg">
                  <h3 className="text-lg font-bold mb-2 text-gray-800">Suggested Additional Ingredients</h3>
                  <p className="text-sm text-gray-600 mb-2">These ingredients are not in your pantry but would enhance the recipe:</p>
                  <ul className="space-y-1">
                    {recipe.suggested_additional_ingredients.map((ingredient: any, index: number) => {
                      // Ensure ingredient is a string
                      const ingredientName = typeof ingredient === 'string' 
                        ? ingredient 
                        : (typeof ingredient === 'object' && ingredient !== null 
                          ? String(ingredient.name || ingredient.ingredient || ingredient || 'Unknown')
                          : String(ingredient || 'Unknown'))
                      return (
                        <li key={index} className="text-gray-700">• {ingredientName}</li>
                      )
                    })}
                  </ul>
                </div>
              )}

              {/* Nutrition Info */}
              {recipe.nutrition_info && (
                <div className="p-4 bg-gray-50 rounded-lg">
                  <h3 className="text-lg font-bold mb-3 text-gray-800">Nutrition Information (per serving)</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-sm text-gray-600">Calories</div>
                      <div className="text-xl font-bold text-gray-800">{recipe.nutrition_info.calories_per_serving}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Protein</div>
                      <div className="text-xl font-bold text-gray-800">{recipe.nutrition_info.protein}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Carbs</div>
                      <div className="text-xl font-bold text-gray-800">{recipe.nutrition_info.carbs}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Fat</div>
                      <div className="text-xl font-bold text-gray-800">{recipe.nutrition_info.fat}</div>
                    </div>
                  </div>
                </div>
              )}

              <div className="mt-6 flex gap-3">
                <button
                  onClick={handleStartCooking}
                  className="flex-1 py-4 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl font-semibold text-lg hover:from-green-600 hover:to-emerald-600 transition-all flex items-center justify-center gap-2"
                >
                  <Play className="w-5 h-5" />
                  Start Cooking
                </button>
                <button
                  onClick={handleReset}
                  className="px-6 py-4 bg-gray-100 text-gray-700 rounded-xl font-semibold hover:bg-gray-200 transition-all flex items-center justify-center gap-2"
                >
                  <ArrowLeft className="w-4 h-4" />
                  New Recipe
                </button>
              </div>
            </motion.div>
          )}

          {step === 'recipe' && isCooking && recipe && (
            <motion.div
              key="cooking"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="bg-white rounded-2xl shadow-xl p-8"
            >
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h2 className="text-3xl font-bold mb-2 text-gray-800 flex items-center gap-3">
                    <CookingIcon className="w-8 h-8 text-orange-500" />
                    {recipe.title}
                  </h2>
                  <p className="text-gray-600">Step {currentStep + 1} of {recipe.instructions.length}</p>
                </div>
                <button
                  onClick={handleFinishCooking}
                  className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg"
                  title="Finish Cooking"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Progress Bar */}
              <div className="mb-6">
                <div className="flex justify-between text-sm text-gray-600 mb-2">
                  <span>Progress</span>
                  <span>{Math.round(((currentStep + 1) / recipe.instructions.length) * 100)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div 
                    className="bg-gradient-to-r from-orange-500 to-red-500 h-3 rounded-full transition-all duration-300"
                    style={{ width: `${((currentStep + 1) / recipe.instructions.length) * 100}%` }}
                  />
                </div>
              </div>

              {/* Current Step */}
              {recipe.instructions[currentStep] && (
                <div className="mb-6">
                  <div className="p-6 bg-gradient-to-br from-orange-50 to-red-50 rounded-xl border-2 border-orange-200">
                    <div className="flex items-start gap-4 mb-4">
                      <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-orange-500 to-red-500 text-white rounded-full flex items-center justify-center font-bold text-xl shadow-lg">
                        {currentStep + 1}
                      </div>
                      <div className="flex-1">
                        <h3 className="text-xl font-bold text-gray-800 mb-2">Step {currentStep + 1}</h3>
                        <p className="text-gray-700 leading-relaxed text-lg">{recipe.instructions[currentStep]}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Ingredients used in this step (simplified - showing all ingredients) */}
              {currentStep === 0 && (
                <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Ingredients you'll need:</h3>
                  <ul className="space-y-1">
                    {recipe.ingredients.slice(0, 5).map((ingredient: any, index: number) => {
                      const name = typeof ingredient === 'string' 
                        ? ingredient 
                        : (ingredient.name || ingredient.ingredient || 'Unknown')
                      const amount = typeof ingredient === 'object' && ingredient.amount 
                        ? ingredient.amount 
                        : ''
                      return (
                        <li key={index} className="text-sm text-gray-600">
                          • {name} {amount && `(${amount})`}
                        </li>
                      )
                    })}
                    {recipe.ingredients.length > 5 && (
                      <li className="text-sm text-gray-500">... and {recipe.ingredients.length - 5} more</li>
                    )}
                  </ul>
                </div>
              )}

              {/* Navigation */}
              <div className="flex gap-3">
                {currentStep > 0 && (
                  <button
                    onClick={() => setCurrentStep(currentStep - 1)}
                    className="px-6 py-3 bg-gray-100 text-gray-700 rounded-xl font-semibold hover:bg-gray-200 transition-all flex items-center justify-center gap-2"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    Previous
                  </button>
                )}
                <button
                  onClick={() => handleStepComplete(currentStep)}
                  className="flex-1 py-4 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl font-semibold text-lg hover:from-green-600 hover:to-emerald-600 transition-all flex items-center justify-center gap-2"
                >
                  <Check className="w-5 h-5" />
                  {currentStep < recipe.instructions.length - 1 ? 'Step Complete' : 'Finish Recipe'}
                </button>
              </div>

              {/* Completed Steps Summary */}
              {completedSteps.size > 0 && (
                <div className="mt-6 p-4 bg-green-50 rounded-lg border border-green-200">
                  <h3 className="text-sm font-semibold text-green-800 mb-2">Completed Steps:</h3>
                  <div className="flex flex-wrap gap-2">
                    {Array.from(completedSteps).sort((a, b) => a - b).map((stepIdx) => (
                      <div
                        key={stepIdx}
                        className="px-3 py-1 bg-green-200 text-green-800 rounded-full text-sm font-medium"
                      >
                        Step {stepIdx + 1}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </DashboardLayout>
  )
}

