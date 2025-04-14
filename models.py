from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class CoinbaseTransaction(BaseModel):
    """Represents a single Coinbase transaction."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ID": "123456789",
                "Timestamp": "2024-04-13T12:00:00.000Z",
                "Transaction Type": "Buy",
                "Asset": "BTC",
                "Quantity Transacted": "0.1",
                "Price Currency": "USD",
                "Price at Transaction": "50000.00",
                "Subtotal": "5000.00",
                "Total (inclusive of fees and/or spread)": "5025.00",
                "Fees and/or Spread": "25.00",
                "Notes": "Initial purchase"
            }
        }
    )

    id: str = Field(
        alias="ID",
        description="Unique identifier for the transaction",
        examples=["123456789"]
    )
    timestamp: datetime = Field(
        alias="Timestamp",
        description="When the transaction occurred",
        examples=["2024-04-13T12:00:00.000Z"]
    )
    transaction_type: str = Field(
        alias="Transaction Type",
        description="Type of transaction (Buy, Sell, etc)",
        examples=["Buy", "Sell", "Convert"]
    )
    asset: str = Field(
        alias="Asset",
        description="The cryptocurrency asset (e.g., BTC, ETH)",
        examples=["BTC", "ETH"]
    )
    quantity: Decimal = Field(
        alias="Quantity Transacted",
        description="Amount of cryptocurrency",
        examples=["0.1", "1.5"]
    )
    price_currency: str = Field(
        alias="Price Currency",
        description="Currency used for the price (usually USD)",
        examples=["USD"]
    )
    price: Decimal = Field(
        alias="Price at Transaction",
        description="Price per unit in the specified currency",
        examples=["50000.00", "3000.00"]
    )
    subtotal: Decimal = Field(
        alias="Subtotal",
        description="Transaction value before fees",
        examples=["5000.00", "4500.00"]
    )
    total: Decimal = Field(
        alias="Total (inclusive of fees and/or spread)",
        description="Total transaction value including fees",
        examples=["5025.00", "4525.00"]
    )
    fees: Decimal = Field(
        alias="Fees and/or Spread",
        description="Transaction fees and/or spread",
        examples=["25.00", "10.00"]
    )
    notes: Optional[str] = Field(
        alias="Notes",
        default=None,
        description="Additional notes about the transaction",
        examples=["Initial purchase", "Monthly DCA"]
    )

class TaxLot(BaseModel):
    """
    Represents a tax lot for cryptocurrency or other assets.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "asset": "BTC",
                "quantity": "0.1",
                "cost_basis": "50000.00",
                "acquisition_date": "2024-04-13T12:00:00.000Z",
                "transaction_id": "tx_123",
                "remaining_quantity": "0.1",
                "is_closed": False
            }
        }
    )

    asset: str = Field(
        description="The cryptocurrency asset",
        examples=["BTC", "ETH"]
    )
    quantity: Decimal = Field(
        description="Original quantity of the tax lot",
        examples=["0.1", "1.5"]
    )
    cost_basis: Decimal = Field(
        description="Cost basis per unit in USD",
        examples=["50000.00", "3000.00"]
    )
    cost_basis_per_unit: Decimal = Field(
        description="Cost basis per unit in USD",
        examples=["50000.00", "3000.00"]
    )
    txn_source: str = Field(
        description="Source of the transaction",
        examples=["Staking Income", "Recurring Buy"]
    )
    acquisition_date: datetime = Field(
        description="When the tax lot was acquired",
        examples=["2024-04-13T12:00:00.000Z"]
    )
    transaction_id: Optional[str] = Field(
        description="ID of the transaction that created this tax lot",
        examples=["tx_123", "tx_456"]
    )
    remaining_quantity: Decimal = Field(
        description="Remaining quantity in the tax lot",
        examples=["0.1", "0.05"]
    )
    is_closed: bool = Field(
        default=False,
        description="Whether the tax lot has been fully sold"
    )
    close_date: Optional[datetime] = Field(
        default=None,
        description="When the tax lot was closed",
        examples=["2024-04-14T12:00:00.000Z"]
    )
    close_price: Optional[Decimal] = Field(
        default=None,
        description="Price at which the tax lot was closed",
        examples=["55000.00", "3200.00"]
    )
    realized_gain_loss: Optional[Decimal] = Field(
        default=None,
        description="Realized gain/loss in USD",
        examples=["500.00", "-200.00"]
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes about the tax lot",
        examples=["Initial purchase", "Monthly DCA"]
    )
