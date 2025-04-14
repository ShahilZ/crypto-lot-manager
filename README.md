# crypto-lot-manager
Manager for Crypto Tax Lots


## Usage:

### Gifting
```
python manager.py select-lots --strategy LOFO --quantity 41 --protocol solana --input output\lots.xls --notes "enter notes here"
```


### Sales

```
python manager.py select-lots --strategy LOFO --quantity 30 --sale-date 2025-01-10 --sale-price 180 --protocol solana --input output\lots.xls
```

### Importing

```
python manager.py import-csv --csv-path input\coinbase_txns.csv --output lots.xls
```