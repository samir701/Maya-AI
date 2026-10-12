"""ZETTA Expense Tracking Provider Interface and Fake Implementation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class ExpenseItem:
    """Standardized expense entry."""
    category: str
    amount: float
    currency: str = "USD"
    merchant: str = "General Vendor"
    id: str = field(default_factory=lambda: str(uuid4()))
    date: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""


class BaseExpenseProvider(ABC):
    """Abstract interface for logging and tracking expenses."""

    @abstractmethod
    def record_expense(self, item: ExpenseItem) -> Dict[str, Any]:
        """Record a newly incurred expense."""
        raise NotImplementedError

    @abstractmethod
    def get_summary(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate totals across recorded expenses."""
        raise NotImplementedError

    @abstractmethod
    def list_expenses(self, limit: int = 50) -> List[ExpenseItem]:
        """List recent expenses."""
        raise NotImplementedError


class FakeExpenseProvider(BaseExpenseProvider):
    """Deterministic offline expense provider."""

    def __init__(self) -> None:
        self.expenses: List[ExpenseItem] = [
            ExpenseItem(category="Software", amount=20.0, merchant="GitHub", notes="Copilot subscription"),
            ExpenseItem(category="Office", amount=45.5, merchant="Stationery", notes="Desk organizer"),
        ]

    def record_expense(self, item: ExpenseItem) -> Dict[str, Any]:
        self.expenses.append(item)
        return {
            "success": True,
            "id": item.id,
            "amount": item.amount,
            "currency": item.currency,
            "category": item.category,
        }

    def get_summary(self, category: Optional[str] = None) -> Dict[str, Any]:
        target = self.expenses
        if category:
            target = [e for e in target if e.category.lower() == category.lower()]
        total = sum(e.amount for e in target)
        return {
            "count": len(target),
            "total": total,
            "category": category or "all",
        }

    def list_expenses(self, limit: int = 50) -> List[ExpenseItem]:
        return self.expenses[-limit:]
