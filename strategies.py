from enum import Enum

class Strategy(Enum):
    FIFO = "FIFO" # First In, First Out based on acquisition date
    LIFO = "LIFO" # Last In, First Out based on acquisition date
    HCFO = "HCFO" # Highest Cost, First Out based on cost basis
    LCFO = "LCFO" # Lowest Cost, First Out based on cost basis
