"""
Database enums matching the SQL schema
"""
from enum import Enum


class InventoryState(str, Enum):
    EMPTY = "EMPTY"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    FULL = "FULL"
    UNKNOWN = "UNKNOWN"


class InventorySource(str, Enum):
    RECEIPT = "RECEIPT"
    SHOPPING_LIST = "SHOPPING_LIST"
    MANUAL = "MANUAL"
    SYSTEM = "SYSTEM"


class InventoryAction(str, Enum):
    PURCHASE = "PURCHASE"
    ADJUST = "ADJUST"
    TRASH = "TRASH"
    EMPTY = "EMPTY"
    REPURCHASE = "REPURCHASE"


class ShoppingListStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class ShoppingItemStatus(str, Enum):
    PLANNED = "PLANNED"
    BOUGHT = "BOUGHT"
    NOT_FOUND = "NOT_FOUND"
    SKIPPED = "SKIPPED"


class ItemAddedBy(str, Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"


class HabitStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    EXPIRED = "EXPIRED"


class HabitType(str, Enum):
    DIET = "DIET"
    HOUSEHOLD = "HOUSEHOLD"
    SHOPPING_SCHEDULE = "SHOPPING_SCHEDULE"
    OTHER = "OTHER"


class HabitInputSource(str, Enum):
    CHAT = "CHAT"
    FORM = "FORM"
    SYSTEM = "SYSTEM"


class PredictorMethod(str, Enum):
    RULES = "RULES"
    EMA = "EMA"
    BAYES_FILTER = "BAYES_FILTER"

