from abc import ABC, abstractmethod

class Strategy(ABC):
    """
    Abstract Base Class for all trading strategies.
    Using ABC (Abstract Base Class) forces any child strategy
    to implement the calculate_signal method, preventing bugs.
    """
    def __init__(self, name: str, min_bars_required: int):
        self.name = name
        self.min_bars_required = min_bars_required

    @abstractmethod
    def calculate_signal(self, df: pd.DataFrame) -> str:
        """
        Takes a sliced DataFrame containing historical data up to the current bar.
        Must return a string signal: 'BUY', 'SELL', or 'HOLD'.
        """
        pass