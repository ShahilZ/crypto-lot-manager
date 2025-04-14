import click
import logging
from collections import defaultdict
from decimal import Decimal

from csv_processor import process_coinbase_csv, write_tax_lots_to_excel, read_tax_lots_from_excel
from tax_lot_manager import select_tax_lots_by_strategy
from strategies import Strategy
from protocols import Protocol

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

@click.group()
def cli():
    """Crypto Tax Lot Manager - Manage your cryptocurrency tax lots efficiently."""
    pass

@cli.command()
@click.option('--csv-path', type=click.Path(exists=True), required=True, help='Path to the Coinbase CSV file')
@click.option('--output', '-o', type=click.Path(), help='Output file for processed tax lots')
def import_csv(csv_path, output):
    """Import transactions from a Coinbase CSV file and process them into tax lots."""
    logger.info(f"Processing CSV file: {csv_path}")
    
    # Process the CSV file
    tax_lots = process_coinbase_csv(csv_path)

    # Group tax lots by protocol
    logger.info(f"Grouping tax lots by protocol")
    tax_lots_by_protocol = defaultdict(list)
    for lot in tax_lots:
        protocol = Protocol.from_ticker(lot.asset)
        tax_lots_by_protocol[protocol].append(lot)
    
    # If output is specified, save the tax lots
    if output:
        # TODO: Implement saving tax lots to file
        logger.info(f"Tax lots will be saved to: {output}")
        # Write tax lots to file
        write_tax_lots_to_excel(tax_lots_by_protocol, f"output/{output}")
    
    logger.info(f"Successfully processed {len(tax_lots)} tax lots")

@cli.command()
@click.option('--strategy', '-s', type=Strategy, required=True, help='Tax calculation strategy')
@click.option('--quantity', '-q', type=Decimal, required=True, help='Quantity to select')
@click.option('--sale-date', '-d', type=click.DateTime(formats=['%Y-%m-%d']), required=False, help='Sale date')
@click.option('--sale-price', '-p', type=Decimal, required=False, help='Sale price')
@click.option('--protocol', '-p', type=str, required=True, help='Protocol to use for selection')
@click.option('--input', '-i', type=click.Path(exists=True), required=True, help='Path to the input tax lots file')
@click.option('--notes', '-n', type=str, help='Notes to attach to the selected lots')
def select_lots(strategy, quantity, sale_date, sale_price, protocol, input, notes):
    """Select tax lots based on the selected strategy."""
    # Sale Date + Sale price are required unless notes are provided
    if not sale_date and not sale_price and not notes:
        raise click.UsageError("Either sale date and sale price or notes are required")
    
    protocol = Protocol.from_name(protocol)
    logger.info(f"Selecting tax lots using strategy: {strategy}")
    logger.info(f"Input file: {input}")
    tax_lots = read_tax_lots_from_excel(input)
    logger.info(f"Successfully read {len(tax_lots)} tax lots from Excel file")

    # Filter tax lots by protocol
    filtered_lots = tax_lots[protocol]

    # Select tax lots based on the selected strategy
    selected_lots, updated_lots = select_tax_lots_by_strategy(
        tax_lots=filtered_lots, 
        strategy=strategy, 
        quantity=quantity, 
        asset=protocol, 
        close_date=sale_date, 
        close_price=sale_price,
        notes=notes
    )
    logger.info(f"Successfully selected {len(selected_lots)} tax lots")
    
    # Log selected lots in a more readable format
    logger.info("Selected lots:")
    for i, lot in enumerate(selected_lots, 1):
        logger.info(f"  Lot #{i}:")
        logger.info(f"    Asset: {lot.asset}")
        logger.info(f"    Quantity: {lot.quantity}")
        logger.info(f"    Cost Basis: ${lot.cost_basis}")
        logger.info(f"    Cost Basis Per Unit: ${lot.cost_basis_per_unit}")
        logger.info(f"    Acquisition Date: {lot.acquisition_date.strftime('%Y-%m-%d %H:%M:%S')}")
        if lot.close_date:
            logger.info(f"    Close Date: {lot.close_date.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"    Close Price: ${lot.close_price}")
            logger.info(f"    Realized Gain/Loss: ${lot.realized_gain_loss}")
        logger.info(f"    Is Closed: {lot.is_closed}")
        logger.info(f"    Notes: {lot.notes}")
                    
    # Save the updated tax lots to a new Excel file
    tax_lots[protocol] = updated_lots
    output_path = f"output/updated_lots.xlsx"
    write_tax_lots_to_excel(tax_lots, output_path)

    # Log total realized gain/loss + cost basis
    total_realized_gain_loss = sum(lot.realized_gain_loss if lot.realized_gain_loss else 0 for lot in selected_lots)
    logger.info(f"Total realized gain/loss: ${total_realized_gain_loss}")
    total_cost_basis = sum(lot.cost_basis for lot in selected_lots)
    logger.info(f"Total cost basis: ${total_cost_basis}")


if __name__ == '__main__':
    cli() 