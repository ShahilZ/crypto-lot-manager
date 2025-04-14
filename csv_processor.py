import pandas as pd
from decimal import Decimal
from typing import List, Dict
from collections import defaultdict
import logging
from datetime import datetime
import pytz

from models import CoinbaseTransaction, TaxLot
from protocols import Protocol

logger = logging.getLogger(__name__)

def process_coinbase_csv(csv_path: str, skip_rows: int = 2) -> List[TaxLot]:
    """
    Process a Coinbase CSV file and convert transactions into tax lots.
    
    Args:
        csv_path: Path to the Coinbase CSV file
        skip_rows: Number of rows to skip before reading the header (default: 2)
        
    Returns:
        List of TaxLot objects
    """
    # Read the CSV file
    try:
        logger.info(f"Reading CSV file from: {csv_path}")
        df = pd.read_csv(csv_path, skiprows=skip_rows)
        required_columns = [
            "ID", "Timestamp", "Transaction Type", "Asset",
            "Quantity Transacted", "Price Currency", "Price at Transaction",
            "Subtotal", "Total (inclusive of fees and/or spread)",
            "Fees and/or Spread", "Notes"
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"CSV is missing required columns: {', '.join(missing_columns)}")
        
        logger.info(f"Found {len(df)} transactions in CSV")
        
        # Convert transactions to our CoinbaseTransaction model
        transactions = []
        error_count = 0
        for index, row in df.iterrows():
            try:
                # Log the raw row data for debugging
                logger.debug(f"Processing row {index+1}: {row.to_dict()}")
                
                # Convert numeric strings that might contain commas
                quantity = safe_decimal_convert(row['Quantity Transacted'])
                price = safe_decimal_convert(row['Price at Transaction'])
                subtotal = safe_decimal_convert(row['Subtotal'])
                total = safe_decimal_convert(row['Total (inclusive of fees and/or spread)'])
                fees = safe_decimal_convert(row['Fees and/or Spread'])
                
                # Parse timestamp - preserve UTC timezone
                timestamp_str = row['Timestamp']
                # Check if the timestamp already has timezone info
                # Remove the UTC suffix and parse as UTC
                timestamp_str = timestamp_str.replace(' UTC', '')
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                # Make the datetime timezone-aware by setting it to UTC
                timestamp = pytz.UTC.localize(timestamp)
               
                
                logger.debug(f"Parsed timestamp: {timestamp} (UTC)")
                
                # Create a dictionary with all the fields for better error reporting
                # Use the exact field names from the CSV which match the model's aliases
                transaction_data = {
                    'ID': str(row['ID']),
                    'Timestamp': timestamp,
                    'Transaction Type': row['Transaction Type'],
                    'Asset': row['Asset'],
                    'Quantity Transacted': quantity,
                    'Price Currency': row['Price Currency'],
                    'Price at Transaction': price,
                    'Subtotal': subtotal,
                    'Total (inclusive of fees and/or spread)': total,
                    'Fees and/or Spread': fees,
                    'Notes': row['Notes'] if pd.notna(row['Notes']) else None
                }
                
                # Log the processed data for debugging
                logger.debug(f"Processed data for row {index+1}: {transaction_data}")
                
                # Create the transaction using the model's alias feature
                # This will automatically map the CSV field names to the model's attribute names
                transaction = CoinbaseTransaction(**transaction_data)
                transactions.append(transaction)
            except Exception as e:
                error_count += 1
                # Log detailed error information
                logger.error(f"Error processing row {index+1} (ID: {row.get('ID', 'Unknown')}):")
                logger.error(f"  Raw data: {row.to_dict()}")
                logger.error(f"  Error: {str(e)}")
                if hasattr(e, '__cause__') and e.__cause__:
                    logger.error(f"  Caused by: {str(e.__cause__)}")
                continue
        
        if error_count > 0:
            logger.warning(f"Failed to process {error_count} transactions")
        
        logger.info(f"Successfully processed {len(transactions)} transactions")
        
        # Convert transactions to tax lots
        tax_lots = []
        assets_found = set()
        for transaction in transactions:
            # Only create tax lots for buy transactions + staking income
            if 'buy' in transaction.transaction_type.lower() or 'staking income' in transaction.transaction_type.lower():
                tax_lot = TaxLot(
                    asset=transaction.asset,
                    quantity=transaction.quantity,
                    cost_basis=transaction.total,  # Include fees in cost basis
                    cost_basis_per_unit=transaction.price,
                    acquisition_date=transaction.timestamp,
                    transaction_id=transaction.id,
                    txn_source=transaction.transaction_type,
                    remaining_quantity=transaction.quantity,
                    is_closed=False,
                )
                tax_lots.append(tax_lot)
                assets_found.add(transaction.asset)
        
        logger.info(f"Created {len(tax_lots)} tax lots for {len(assets_found)} assets: {', '.join(sorted(assets_found))}")
        return tax_lots
    
    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}", exc_info=True)
        raise


def write_tax_lots_to_excel(tax_lots: Dict[Protocol, List[TaxLot]], output_path: str):
    """
    Write tax lots to an Excel file with multiple sheets (one per asset).
    Each sheet will be sorted by acquisition date.
    
    Args:
        tax_lots: Dictionary mapping Protocol objects to lists of TaxLot objects
        output_path: Path to save the Excel file
    """
    try:
        logger.info(f"Writing tax lots to Excel: {output_path}")
        
        # Create Excel writer
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Write each asset to its own sheet
            for protocol, lots in tax_lots.items():
                logger.debug(f"Writing {len(lots)} tax lots for {protocol.ticker}")
                
                # Sort lots by acquisition date
                sorted_lots = sorted(lots, key=lambda x: x.acquisition_date)
                logger.debug(f"Sorted {len(sorted_lots)} lots by acquisition date")
                
                # Convert TaxLot objects to dictionaries
                lot_dicts = []
                for lot in sorted_lots:
                    # Convert TaxLot to dict, handling None values
                    lot_dict = lot.model_dump()
                    
                    # Convert timezone-aware datetimes to timezone-naive for Excel compatibility
                    for key, value in lot_dict.items():
                        if isinstance(value, datetime) and value.tzinfo is not None:
                            # Convert to UTC and then remove timezone info
                            utc_time = value.astimezone(pytz.UTC)
                            lot_dict[key] = utc_time.replace(tzinfo=None)
                            logger.debug(f"Converted timezone-aware datetime to naive: {value} -> {lot_dict[key]}")
                        elif isinstance(value, Decimal):
                            # Convert Decimal objects to floats for Excel compatibility
                            lot_dict[key] = float(value)
                        # Keep boolean values as is (don't convert to float)
                        elif isinstance(value, bool):
                            lot_dict[key] = value
                    
                    lot_dicts.append(lot_dict)
                
                # Convert list of dicts to DataFrame
                df = pd.DataFrame(lot_dicts)
                
                # Ensure boolean columns are properly handled
                if 'is_closed' in df.columns:
                    # Convert to string 'True'/'False' to avoid Excel formula syntax
                    df['is_closed'] = df['is_closed'].map({True: 'True', False: 'False'})
                
                # Write to Excel
                df.to_excel(writer, sheet_name=protocol.ticker, index=False)
        
        logger.info(f"Successfully wrote tax lots to {len(tax_lots)} sheets in {output_path}")
    
    except Exception as e:
        logger.error(f"Error writing Excel file: {str(e)}", exc_info=True)
        raise

def write_tax_lots_to_csv(tax_lots: List[TaxLot], output_path: str):
    """
    Write tax lots to a single CSV file, sorted by asset and timestamp.
    
    Args:
        tax_lots: List of TaxLot objects to write
        output_path: Path to save the CSV file
    """
    try:
        logger.info(f"Writing {len(tax_lots)} tax lots to CSV: {output_path}")
        
        # Convert all tax lots to dicts
        lots_dicts = []
        for lot in tax_lots:
            lot_dict = lot.model_dump()
            # Convert Decimal objects to floats for CSV compatibility
            for key, value in lot_dict.items():
                if isinstance(value, Decimal):
                    lot_dict[key] = float(value)
            lots_dicts.append(lot_dict)
        
        # Convert to DataFrame and sort
        df = pd.DataFrame(lots_dicts)
        df = df.sort_values(['asset', 'acquisition_date'])
        
        # Write to CSV
        df.to_csv(output_path, index=False)
        logger.info(f"Successfully wrote tax lots to {output_path}")
    
    except Exception as e:
        logger.error(f"Error writing CSV file: {str(e)}", exc_info=True)
        raise

def safe_decimal_convert(value) -> Decimal:
    """
    Safely convert a value to Decimal, handling common formatting issues.
    
    Args:
        value: The value to convert (string, float, or Decimal)
        
    Returns:
        Decimal: The converted value
        
    Raises:
        ValueError: If the value cannot be converted to a valid Decimal
    """
    if pd.isna(value):
        return Decimal('0')
    
    if isinstance(value, Decimal):
        return value
        
    # Convert to string and clean up
    value_str = str(value).strip()
    
    # Log the original value for debugging
    logger.debug(f"Converting to Decimal: '{value_str}' (type: {type(value).__name__})")
    
    # Handle negative values in parentheses format like '($55.73)'
    if value_str.startswith('(') and value_str.endswith(')'):
        value_str = '-' + value_str[1:-1]
        logger.debug(f"Converted parentheses format to negative: '{value_str}'")
    
    # Handle scientific notation (e.g., '5.51316e-08')
    if 'e' in value_str.lower() or 'E' in value_str:
        try:
            # Convert to float first, then to Decimal
            float_val = float(value_str)
            result = Decimal(str(float_val))
            logger.debug(f"Converted scientific notation: '{value_str}' -> {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to convert scientific notation '{value_str}': {str(e)}")
            raise ValueError(f"Invalid scientific notation: '{value_str}'")
    
    # Remove currency symbols and other non-numeric characters except decimal point and minus
    # First, handle common currency symbols
    value_str = value_str.replace('$', '').replace('£', '').replace('€', '')
    
    # Remove any other non-numeric characters except decimal point and minus
    value_str = ''.join(c for c in value_str if c.isdigit() or c in '.-')
    
    # Handle empty string after cleaning
    if not value_str:
        logger.warning(f"Empty value after cleaning: '{value}'")
        return Decimal('0')
    
    # Handle multiple decimal points (keep only the first one)
    if value_str.count('.') > 1:
        parts = value_str.split('.')
        value_str = parts[0] + '.' + ''.join(parts[1:])
        logger.debug(f"Fixed multiple decimal points: '{value_str}'")
    
    # Handle multiple minus signs (keep only the first one if at the beginning)
    if value_str.count('-') > 1:
        if value_str.startswith('-'):
            value_str = '-' + value_str.replace('-', '')
        else:
            value_str = value_str.replace('-', '')
        logger.debug(f"Fixed multiple minus signs: '{value_str}'")
    
    try:
        result = Decimal(value_str)
        logger.debug(f"Successfully converted '{value}' to Decimal: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to convert '{value}' to Decimal: {str(e)}")
        logger.error(f"  Cleaned value: '{value_str}'")
        raise ValueError(f"Invalid number format: '{value}' (cleaned: '{value_str}')")

def read_tax_lots_from_excel(excel_path: str) -> Dict[Protocol, List[TaxLot]]:
    """
    Read tax lots from an Excel file with multiple sheets (one per asset).
    
    Args:
        excel_path: Path to the Excel file containing tax lots
        
    Returns:
        Dictionary mapping assets to lists of TaxLot objects
    """
    try:
        logger.info(f"Reading tax lots from Excel: {excel_path}")
        
        # Dictionary to store tax lots by asset
        tax_lots_by_asset: Dict[Protocol, List[TaxLot]] = {}
        
        with pd.ExcelFile(excel_path) as xls:
            # Get all sheet names
            sheet_names = xls.sheet_names
            logger.info(f"Found {len(sheet_names)} sheets in Excel file: {', '.join(sheet_names)}")
            
            # Process each sheet
            for sheet_name in sheet_names:
                # Read the sheet into a DataFrame
                df = pd.read_excel(xls, sheet_name=sheet_name)
                logger.debug(f"Read {len(df)} rows from sheet '{sheet_name}'")
                
                # Initialize list for this asset
                asset_lots = []
                
                # Convert DataFrame rows to TaxLot objects
                for _, row in df.iterrows():
                    try:
                        # Create a dictionary with default values
                        row_dict = {
                            'quantity': Decimal('0'),
                            'cost_basis': Decimal('0'),
                            'cost_basis_per_unit': Decimal('0'),
                            'remaining_quantity': Decimal('0'),
                            'close_date': None,
                            'close_price': Decimal('0'),
                            'realized_gain_loss': Decimal('0'),
                            'txn_source': None,
                            'is_closed': False
                        }
                        
                        # Update with actual values from the row
                        for col in df.columns:
                            if col in row and pd.notna(row[col]):
                                row_dict[col] = row[col]
                        
                        # Convert numeric values to Decimal
                        for col in ['quantity', 'cost_basis', 'cost_basis_per_unit', 'remaining_quantity', 'close_price', 'realized_gain_loss']:
                            if isinstance(row_dict.get(col), (int, float)):
                                row_dict[col] = Decimal(str(row_dict[col]))
                        # Handle txn_source
                        if 'txn_source' in row_dict:
                            row_dict['txn_source'] = row_dict['txn_source']

                        # Handle acquisition_date - required field
                        if 'acquisition_date' not in row_dict or pd.isna(row_dict['acquisition_date']):
                            logger.error("Missing required field: acquisition_date")
                            continue
                            
                        # Make acquisition_date timezone-aware
                        if isinstance(row_dict['acquisition_date'], datetime):
                            if row_dict['acquisition_date'].tzinfo is None:
                                row_dict['acquisition_date'] = pytz.UTC.localize(row_dict['acquisition_date'])
                        else:
                            try:
                                dt = pd.to_datetime(row_dict['acquisition_date'])
                                if dt.tzinfo is None:
                                    dt = pytz.UTC.localize(dt)
                                row_dict['acquisition_date'] = dt
                            except Exception as e:
                                logger.error(f"Error parsing acquisition_date '{row_dict['acquisition_date']}': {str(e)}")
                                continue
                        
                        # Make close_date timezone-aware if present
                        if 'close_date' in row_dict and row_dict['close_date'] is not None:
                            if isinstance(row_dict['close_date'], datetime):
                                if row_dict['close_date'].tzinfo is None:
                                    row_dict['close_date'] = pytz.UTC.localize(row_dict['close_date'])
                            else:
                                try:
                                    dt = pd.to_datetime(row_dict['close_date'])
                                    if dt.tzinfo is None:
                                        dt = pytz.UTC.localize(dt)
                                    row_dict['close_date'] = dt
                                except Exception as e:
                                    logger.error(f"Error parsing close_date '{row_dict['close_date']}': {str(e)}")
                                    row_dict['close_date'] = None
                        
                        # Convert is_closed to boolean
                        if 'is_closed' in row_dict:
                            if isinstance(row_dict['is_closed'], (int, float)):
                                row_dict['is_closed'] = bool(row_dict['is_closed'])
                            elif isinstance(row_dict['is_closed'], str):
                                row_dict['is_closed'] = row_dict['is_closed'].lower() in ('true', '1', 'yes')
                        
                        # Create TaxLot object
                        tax_lot = TaxLot(**row_dict)
                        asset_lots.append(tax_lot)
                        
                    except Exception as e:
                        logger.error(f"Error processing row in sheet '{sheet_name}': {str(e)}")
                        logger.error(f"  Row data: {row.to_dict()}")
                        continue
                
                # Add the asset's lots to the dictionary
                protocol = Protocol.from_ticker(sheet_name)
                tax_lots_by_asset[protocol] = asset_lots
        
        total_lots = sum(len(lots) for lots in tax_lots_by_asset.values())
        logger.info(f"Successfully read {total_lots} tax lots from {len(tax_lots_by_asset)} assets in Excel file")
        return tax_lots_by_asset
    
    except Exception as e:
        logger.error(f"Error reading Excel file: {str(e)}", exc_info=True)
        raise