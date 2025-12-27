"""
API routes
"""
from . import inventory
from . import products
from . import receipts
from . import shopping_lists
from . import habits
from . import predictor
from . import auth
from . import recipes

__all__ = ["inventory", "products", "receipts", "shopping_lists", "habits", "predictor", "auth", "recipes"]
