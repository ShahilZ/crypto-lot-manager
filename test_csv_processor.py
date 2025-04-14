import unittest
import os
import tempfile
import pandas as pd
from decimal import Decimal
from datetime import datetime
import pytz

from csv_processor import (
    safe_decimal_convert,
    process_coinbase_csv,
    write_tax_lots_to_excel,
    write_tax_lots_to_csv
)
from models import TaxLot

class TestCSVProcessor(unittest.TestCase):
    """Test cases for csv_processor.py"""
    
    def test_safe_decimal_convert(self):
        """Test the safe_decimal_convert function with various formats"""
        # Test regular numbers
        self.assertEqual(safe_decimal_convert("123.45"), Decimal("123.45"))
        self.assertEqual(safe_decimal_convert("123"), Decimal("123"))
        
        # Test numbers with commas
        self.assertEqual(safe_decimal_convert("1,234.56"), Decimal("1234.56"))
        
        # Test currency symbols
        self.assertEqual(safe_decimal_convert("$1,234.56"), Decimal("1234.56"))
        self.assertEqual(safe_decimal_convert("£1,234.56"), Decimal("1234.56"))
        self.assertEqual(safe_decimal_convert("€1,234.56"), Decimal("1234.56"))
        
        # Test negative numbers in parentheses
        self.assertEqual(safe_decimal_convert("($55.73)"), Decimal("-55.73"))
        self.assertEqual(safe_decimal_convert("($1,234.56)"), Decimal("-1234.56"))
        
        # Test scientific notation
        self.assertEqual(safe_decimal_convert("5.51316e-08"), Decimal("0.0000000551316"))
        self.assertEqual(safe_decimal_convert("1.23E+4"), Decimal("12300"))
        
        # Test empty or None values
        self.assertEqual(safe_decimal_convert(""), Decimal("0"))
        self.assertEqual(safe_decimal_convert(None), Decimal("0"))
        
        # Test multiple decimal points (should keep first one)
        self.assertEqual(safe_decimal_convert("1.234.56"), Decimal("1234.56"))
        
        # Test multiple minus signs
        self.assertEqual(safe_decimal_convert("--1,234.56"), Decimal("-1234.56"))
        
        # Test whitespace
        self.assertEqual(safe_decimal_convert(" 1,234.56 "), Decimal("1234.56"))
    
    def test_write_tax_lots_to_excel(self):
        """Test writing tax lots to Excel"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Create some test tax lots
            tax_lots = [
                TaxLot(
                    asset="BTC",
                    quantity=Decimal("0.1"),
                    cost_basis=Decimal("50000.00"),
                    acquisition_date=datetime.now(pytz.UTC),
                    transaction_id="test_tx_1",
                    remaining_quantity=Decimal("0.1")
                ),
                TaxLot(
                    asset="ETH",
                    quantity=Decimal("1.5"),
                    cost_basis=Decimal("3000.00"),
                    acquisition_date=datetime.now(pytz.UTC),
                    transaction_id="test_tx_2",
                    remaining_quantity=Decimal("1.5")
                )
            ]
            
            # Write to Excel
            write_tax_lots_to_excel(tax_lots, temp_path)
            
            # Verify the file was created
            self.assertTrue(os.path.exists(temp_path))
            
            # Read the Excel file and verify contents
            with pd.ExcelFile(temp_path) as xls:
                # Check that we have sheets for both assets
                self.assertIn("BTC", xls.sheet_names)
                self.assertIn("ETH", xls.sheet_names)
                
                # Check BTC sheet
                btc_df = pd.read_excel(xls, "BTC")
                self.assertEqual(len(btc_df), 1)
                self.assertEqual(btc_df.iloc[0]["asset"], "BTC")
                self.assertEqual(btc_df.iloc[0]["quantity"], 0.1)
                
                # Check ETH sheet
                eth_df = pd.read_excel(xls, "ETH")
                self.assertEqual(len(eth_df), 1)
                self.assertEqual(eth_df.iloc[0]["asset"], "ETH")
                self.assertEqual(eth_df.iloc[0]["quantity"], 1.5)
        
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_write_tax_lots_to_csv(self):
        """Test writing tax lots to CSV"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Create some test tax lots
            tax_lots = [
                TaxLot(
                    asset="BTC",
                    quantity=Decimal("0.1"),
                    cost_basis=Decimal("50000.00"),
                    acquisition_date=datetime.now(pytz.UTC),
                    transaction_id="test_tx_1",
                    remaining_quantity=Decimal("0.1")
                ),
                TaxLot(
                    asset="ETH",
                    quantity=Decimal("1.5"),
                    cost_basis=Decimal("3000.00"),
                    acquisition_date=datetime.now(pytz.UTC),
                    transaction_id="test_tx_2",
                    remaining_quantity=Decimal("1.5")
                )
            ]
            
            # Write to CSV
            write_tax_lots_to_csv(tax_lots, temp_path)
            
            # Verify the file was created
            self.assertTrue(os.path.exists(temp_path))
            
            # Read the CSV file and verify contents
            df = pd.read_csv(temp_path)
            self.assertEqual(len(df), 2)
            self.assertEqual(df.iloc[0]["asset"], "BTC")
            self.assertEqual(df.iloc[0]["quantity"], 0.1)
            self.assertEqual(df.iloc[1]["asset"], "ETH")
            self.assertEqual(df.iloc[1]["quantity"], 1.5)
        
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

if __name__ == "__main__":
    unittest.main() 