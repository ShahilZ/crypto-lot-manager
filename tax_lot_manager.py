import logging
from decimal import Decimal
from datetime import datetime
from typing import List, Tuple, Optional

from models import TaxLot
from protocols import Protocol
from strategies import Strategy

logger = logging.getLogger(__name__)

def select_tax_lots_by_strategy(
    tax_lots: List[TaxLot],
    strategy: Strategy,
    quantity: Decimal,
    asset: Protocol,
    close_date: Optional[datetime] = None,
    close_price: Optional[Decimal] = None,
    notes: Optional[str] = None
) -> Tuple[List[TaxLot], List[TaxLot]]:
    """
    Select tax lots based on the specified strategy.
    
    Args:
        tax_lots: List of available tax lots
        strategy: Strategy to use for selection (FIFO, LIFO, HIFO, LOFO)
        quantity: Quantity to sell
        asset: Asset being sold
        close_date: Date of the sale (optional)
        close_price: Price of the sale (optional)
        notes: Notes to attach to the selected lots (optional)
        
    Returns:
        Tuple containing:
        - List of selected TaxLot objects
        - List of all TaxLot objects (including unused ones)
    """
    # Create a deep copy of the tax lots to avoid modifying the original
    updated_lots = [TaxLot(
        asset=lot.asset,
        quantity=lot.quantity,
        cost_basis=lot.cost_basis,
        cost_basis_per_unit=lot.cost_basis_per_unit,
        txn_source=lot.txn_source,
        acquisition_date=lot.acquisition_date,
        transaction_id=lot.transaction_id,
        remaining_quantity=lot.remaining_quantity,
        is_closed=lot.is_closed,
        close_date=lot.close_date,
        close_price=lot.close_price,
        realized_gain_loss=lot.realized_gain_loss
    ) for lot in tax_lots]
    
    # Filter tax lots for the specified asset and ensure they're not already closed
    available_lots = [lot for lot in updated_lots if lot.asset == asset.ticker and not lot.is_closed]
    
    if not available_lots:
        logger.warning(f"No available tax lots found for asset {asset.ticker}")
        return [], updated_lots
    
    # Sort lots based on strategy
    match strategy:
        case Strategy.FIFO:
            # First In, First Out - sort by acquisition date ascending
            available_lots.sort(key=lambda x: x.acquisition_date)
        case Strategy.LIFO:
            # Last In, First Out - sort by acquisition date descending
            available_lots.sort(key=lambda x: x.acquisition_date, reverse=True)
        case Strategy.HCFO:
            # Highest Cost, First Out - sort by cost basis per unit descending
            available_lots.sort(key=lambda x: x.cost_basis_per_unit, reverse=True)
        case Strategy.LCFO:
            # Lowest Cost, First Out - sort by cost basis per unit ascending
            available_lots.sort(key=lambda x: x.cost_basis_per_unit)
        case _:
            logger.error(f"Unknown strategy: {strategy}")
            return [], updated_lots
    
    # Select lots until we have enough quantity
    selected_lots = []
    remaining_quantity = quantity
    
    for lot in available_lots:
        if remaining_quantity <= 0:
            break
            
        # Calculate how much of this lot to use
        lot_quantity = min(remaining_quantity, lot.remaining_quantity)
        
        # Create a new tax lot with the selected quantity
        selected_lot = TaxLot(
            asset=lot.asset,
            quantity=lot_quantity,
            cost_basis=lot.cost_basis * (lot_quantity / lot.quantity),
            cost_basis_per_unit=lot.cost_basis_per_unit,
            txn_source=lot.txn_source,
            acquisition_date=lot.acquisition_date,
            transaction_id=lot.transaction_id,
            remaining_quantity=lot_quantity,
            is_closed=True,
            close_date=close_date if close_date else None,
            close_price=close_price if close_price else None,
            realized_gain_loss=(
                (close_price - lot.cost_basis_per_unit) * lot_quantity
                if close_price is not None
                else None
            ),
            notes=notes
        )
        
        selected_lots.append(selected_lot)
        
        # Update the original lot's remaining quantity
        lot.remaining_quantity -= lot_quantity
        if lot.remaining_quantity < 0:
          raise ValueError(f"Remaining quantity is negative for lot {lot.transaction_id}")
        
        # Update the original lot's cost basis proportionally if it's not fully used
        if lot.remaining_quantity > 0:
          lot.cost_basis = lot.cost_basis * (lot.remaining_quantity / lot.quantity)
        
        # If the lot is now fully used, mark it as closed
        if lot.remaining_quantity == 0:
            lot.is_closed = True
            lot.close_date = close_date if close_date else None
            lot.close_price = close_price if close_price else None
            if close_price:
                lot.realized_gain_loss = (
                    (close_price - lot.cost_basis_per_unit) * lot.quantity
                )
            lot.notes = notes
        
        remaining_quantity -= lot_quantity
    
    if remaining_quantity > 0:
        logger.warning(
            f"Not enough quantity available for {asset}. "
            f"Requested: {quantity}, Available: {quantity - remaining_quantity}"
        )

    return selected_lots, updated_lots 