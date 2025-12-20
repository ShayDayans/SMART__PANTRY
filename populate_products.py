"""
Script to populate the database with 100 basic food products and categories
"""
import os
from supabase import create_client, Client

# Supabase credentials
SUPABASE_URL = "https://ujwefoymuvjqrbkczbqk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVqd2Vmb3ltdXZqcXJia2N6YnFrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzQzNTk4MTQsImV4cCI6MjA0OTkzNTgxNH0.BoHw4Sn97PvVdcZgLMnZSYc7m9nC-fOiHsP2-WX0fpU"

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Categories with their products
CATEGORIES_AND_PRODUCTS = {
    "Dairy & Eggs": [
        {"name": "Milk", "barcode": "1000000001"},
        {"name": "Butter", "barcode": "1000000002"},
        {"name": "Cheese", "barcode": "1000000003"},
        {"name": "Yogurt", "barcode": "1000000004"},
        {"name": "Eggs", "barcode": "1000000005"},
        {"name": "Cream", "barcode": "1000000006"},
        {"name": "Sour Cream", "barcode": "1000000007"},
        {"name": "Cottage Cheese", "barcode": "1000000008"},
    ],
    "Bread & Bakery": [
        {"name": "White Bread", "barcode": "2000000001"},
        {"name": "Whole Wheat Bread", "barcode": "2000000002"},
        {"name": "Pita Bread", "barcode": "2000000003"},
        {"name": "Bagels", "barcode": "2000000004"},
        {"name": "Croissants", "barcode": "2000000005"},
        {"name": "Tortillas", "barcode": "2000000006"},
    ],
    "Meat & Poultry": [
        {"name": "Chicken Breast", "barcode": "3000000001"},
        {"name": "Ground Beef", "barcode": "3000000002"},
        {"name": "Steak", "barcode": "3000000003"},
        {"name": "Pork Chops", "barcode": "3000000004"},
        {"name": "Bacon", "barcode": "3000000005"},
        {"name": "Sausages", "barcode": "3000000006"},
        {"name": "Turkey Breast", "barcode": "3000000007"},
        {"name": "Lamb Chops", "barcode": "3000000008"},
    ],
    "Fish & Seafood": [
        {"name": "Salmon", "barcode": "4000000001"},
        {"name": "Tuna", "barcode": "4000000002"},
        {"name": "Shrimp", "barcode": "4000000003"},
        {"name": "Tilapia", "barcode": "4000000004"},
        {"name": "Cod", "barcode": "4000000005"},
    ],
    "Fruits": [
        {"name": "Apples", "barcode": "5000000001"},
        {"name": "Bananas", "barcode": "5000000002"},
        {"name": "Oranges", "barcode": "5000000003"},
        {"name": "Strawberries", "barcode": "5000000004"},
        {"name": "Grapes", "barcode": "5000000005"},
        {"name": "Watermelon", "barcode": "5000000006"},
        {"name": "Lemons", "barcode": "5000000007"},
        {"name": "Pears", "barcode": "5000000008"},
        {"name": "Peaches", "barcode": "5000000009"},
        {"name": "Mangoes", "barcode": "5000000010"},
    ],
    "Vegetables": [
        {"name": "Tomatoes", "barcode": "6000000001"},
        {"name": "Cucumbers", "barcode": "6000000002"},
        {"name": "Lettuce", "barcode": "6000000003"},
        {"name": "Carrots", "barcode": "6000000004"},
        {"name": "Potatoes", "barcode": "6000000005"},
        {"name": "Onions", "barcode": "6000000006"},
        {"name": "Broccoli", "barcode": "6000000007"},
        {"name": "Bell Peppers", "barcode": "6000000008"},
        {"name": "Spinach", "barcode": "6000000009"},
        {"name": "Garlic", "barcode": "6000000010"},
        {"name": "Mushrooms", "barcode": "6000000011"},
        {"name": "Zucchini", "barcode": "6000000012"},
    ],
    "Grains & Pasta": [
        {"name": "Rice", "barcode": "7000000001"},
        {"name": "Pasta", "barcode": "7000000002"},
        {"name": "Spaghetti", "barcode": "7000000003"},
        {"name": "Oats", "barcode": "7000000004"},
        {"name": "Quinoa", "barcode": "7000000005"},
        {"name": "Couscous", "barcode": "7000000006"},
    ],
    "Canned & Jarred": [
        {"name": "Canned Tomatoes", "barcode": "8000000001"},
        {"name": "Canned Beans", "barcode": "8000000002"},
        {"name": "Canned Corn", "barcode": "8000000003"},
        {"name": "Canned Tuna", "barcode": "8000000004"},
        {"name": "Tomato Sauce", "barcode": "8000000005"},
        {"name": "Peanut Butter", "barcode": "8000000006"},
        {"name": "Jam", "barcode": "8000000007"},
        {"name": "Pickles", "barcode": "8000000008"},
    ],
    "Condiments & Sauces": [
        {"name": "Ketchup", "barcode": "9000000001"},
        {"name": "Mustard", "barcode": "9000000002"},
        {"name": "Mayonnaise", "barcode": "9000000003"},
        {"name": "Soy Sauce", "barcode": "9000000004"},
        {"name": "Hot Sauce", "barcode": "9000000005"},
        {"name": "BBQ Sauce", "barcode": "9000000006"},
        {"name": "Olive Oil", "barcode": "9000000007"},
        {"name": "Vegetable Oil", "barcode": "9000000008"},
        {"name": "Vinegar", "barcode": "9000000009"},
    ],
    "Snacks": [
        {"name": "Potato Chips", "barcode": "10000000001"},
        {"name": "Pretzels", "barcode": "10000000002"},
        {"name": "Popcorn", "barcode": "10000000003"},
        {"name": "Crackers", "barcode": "10000000004"},
        {"name": "Cookies", "barcode": "10000000005"},
        {"name": "Chocolate Bar", "barcode": "10000000006"},
        {"name": "Granola Bars", "barcode": "10000000007"},
    ],
    "Beverages": [
        {"name": "Orange Juice", "barcode": "11000000001"},
        {"name": "Apple Juice", "barcode": "11000000002"},
        {"name": "Coffee", "barcode": "11000000003"},
        {"name": "Tea", "barcode": "11000000004"},
        {"name": "Soda", "barcode": "11000000005"},
        {"name": "Water", "barcode": "11000000006"},
        {"name": "Energy Drink", "barcode": "11000000007"},
    ],
    "Frozen Foods": [
        {"name": "Frozen Pizza", "barcode": "12000000001"},
        {"name": "Ice Cream", "barcode": "12000000002"},
        {"name": "Frozen Vegetables", "barcode": "12000000003"},
        {"name": "Frozen Fries", "barcode": "12000000004"},
        {"name": "Frozen Chicken Nuggets", "barcode": "12000000005"},
    ],
    "Spices & Seasonings": [
        {"name": "Salt", "barcode": "13000000001"},
        {"name": "Pepper", "barcode": "13000000002"},
        {"name": "Garlic Powder", "barcode": "13000000003"},
        {"name": "Paprika", "barcode": "13000000004"},
        {"name": "Cumin", "barcode": "13000000005"},
        {"name": "Oregano", "barcode": "13000000006"},
        {"name": "Basil", "barcode": "13000000007"},
    ],
}


def create_categories_and_products():
    """Create categories and products in the database"""
    print("Starting to populate database...")
    
    total_products = 0
    
    for category_name, products in CATEGORIES_AND_PRODUCTS.items():
        print(f"\nCreating category: {category_name}")
        
        # Check if category exists
        existing_category = supabase.table("categories").select("*").eq("name", category_name).execute()
        
        if existing_category.data:
            category_id = existing_category.data[0]["category_id"]
            print(f"  Category '{category_name}' already exists (ID: {category_id})")
        else:
            # Create category
            category_data = {
                "name": category_name,
                "description": f"{category_name} products"
            }
            result = supabase.table("categories").insert(category_data).execute()
            category_id = result.data[0]["category_id"]
            print(f"  Created category '{category_name}' (ID: {category_id})")
        
        # Create products for this category
        for product in products:
            try:
                # Check if product exists by barcode
                existing_product = supabase.table("products").select("*").eq("barcode", product["barcode"]).execute()
                
                if existing_product.data:
                    print(f"    Product '{product['name']}' already exists")
                else:
                    product_data = {
                        "name": product["name"],
                        "barcode": product["barcode"],
                        "category_id": category_id,
                    }
                    supabase.table("products").insert(product_data).execute()
                    total_products += 1
                    print(f"    Created product: {product['name']} (Barcode: {product['barcode']})")
            except Exception as e:
                print(f"    Error creating product {product['name']}: {e}")
    
    print(f"\n✅ Done! Created {total_products} new products")
    
    # Count total products and categories
    total_products_in_db = supabase.table("products").select("*", count="exact").execute()
    total_categories_in_db = supabase.table("categories").select("*", count="exact").execute()
    
    print(f"📊 Total products in database: {total_products_in_db.count}")
    print(f"📊 Total categories in database: {total_categories_in_db.count}")


if __name__ == "__main__":
    create_categories_and_products()

