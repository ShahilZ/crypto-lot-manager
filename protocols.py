from enum import Enum
from typing import Dict, Optional


class Protocol(Enum):
    """
    Enum representing different cryptocurrency protocols/assets.
    Each protocol has a name and ticker symbol.
    """
    ALEO = ("aleo", "ALEO")
    ALGORAND = ("algorand", "ALGO")
    BALANCER = ("balancer", "BAL")
    BITCOIN = ("bitcoin", "BTC")
    CARDANO = ("cardano", "ADA")
    CBETH = ("cbeth", "CBETH")
    COSMOS = ("cosmos", "ATOM")
    ETHEREUM = ("ethereum", "ETH")
    MATIC = ("matic", "MATIC")
    POLYGON = ("polygon", "POL")
    SOLANA = ("solana", "SOL")
    USDC = ("usdc", "USDC")
    XRP = ("xrp", "XRP")
    
    def __init__(self, protocol_name: str, ticker: str):
        self.protocol_name = protocol_name
        self.ticker = ticker
    
    @classmethod
    def from_name(cls, protocol_name: str) -> Optional['Protocol']:
        """
        Look up a Protocol by its name.
        
        Args:
            protocol_name: The name of the protocol
            
        Returns:
            The Protocol enum value if found, None otherwise
        """
        for protocol in cls:
            if protocol.protocol_name.lower() == protocol_name.lower():
                return protocol
        return None
    
    @classmethod
    def from_ticker(cls, ticker: str) -> Optional['Protocol']:
        """
        Look up a Protocol by its ticker symbol.
        
        Args:
            ticker: The ticker symbol of the protocol
            
        Returns:
            The Protocol enum value if found, None otherwise
        """
        for protocol in cls:
            if protocol.ticker.lower() == ticker.lower():
                return protocol
        return None
    
    @classmethod
    def get_all_names(cls) -> Dict[str, str]:
        """
        Get a dictionary mapping protocol names to their ticker symbols.
        
        Returns:
            Dictionary with protocol names as keys and ticker symbols as values
        """
        return {protocol.protocol_name: protocol.ticker for protocol in cls}
    
    @classmethod
    def get_all_tickers(cls) -> Dict[str, str]:
        """
        Get a dictionary mapping ticker symbols to their protocol names.
        
        Returns:
            Dictionary with ticker symbols as keys and protocol names as values
        """
        return {protocol.ticker: protocol.protocol_name for protocol in cls}

    