"""Portfolio management for tracking positions and PnL."""

from dataclasses import dataclass
import pandas as pd


@dataclass
class Position:
    """Represents a contract position."""
    contract_type: str  # "YES" or "NO"
    quantity: float
    entry_price: float
    entry_time: pd.Timestamp
    strike_price: float


class Portfolio:
    """
    Portfolio class that:
    - tracks cash balance
    - tracks YES and NO positions
    - applies fees
    - prevents over-allocation
    """
    
    def __init__(self, starting_balance: float, fee_per_contract: float = 0.0):
        """
        Initialize portfolio.
        
        Args:
            starting_balance: Initial cash balance
            fee_per_contract: Fee per contract traded
        """
        self.initial_balance = starting_balance
        self.cash = starting_balance
        self.fee_per_contract = fee_per_contract
        self.positions = []  # List of Position objects
        self.trade_history = []  # List of all trades
        self.pnl_history = []  # Track PnL over time
        
    def can_afford(self, quantity: float, price: float) -> bool:
        """
        Check if we can afford to buy contracts.
        
        Args:
            quantity: Number of contracts
            price: Price per contract
            
        Returns:
            True if affordable, False otherwise
        """
        total_cost = quantity * price + quantity * self.fee_per_contract
        return total_cost <= self.cash
    
    def buy_yes(self, 
                quantity: float,
                price: float,
                timestamp: pd.Timestamp,
                strike_price: float) -> bool:
        """
        Buy YES contracts.
        
        Args:
            quantity: Number of contracts to buy
            price: Price per YES contract
            timestamp: Time of purchase
            strike_price: Strike price of the market
            
        Returns:
            True if trade executed, False if insufficient funds
        """
        if not self.can_afford(quantity, price):
            return False
        
        # Deduct cost and fees
        total_cost = quantity * price + quantity * self.fee_per_contract
        self.cash -= total_cost
        
        # Create position
        position = Position(
            contract_type="YES",
            quantity=quantity,
            entry_price=price,
            entry_time=timestamp,
            strike_price=strike_price
        )
        self.positions.append(position)
        
        # Record trade
        # Note: Both 'timestamp' and 'entry_timestamp' are kept for compatibility
        # 'entry_timestamp' is used by metrics for duration calculations
        self.trade_history.append({
            'timestamp': timestamp,
            'entry_timestamp': timestamp,
            'action': 'BUY_YES',
            'quantity': quantity,
            'price': price,
            'fees': quantity * self.fee_per_contract,
            'strike_price': strike_price
        })
        
        return True
    
    def buy_no(self, 
               quantity: float,
               price: float,
               timestamp: pd.Timestamp,
               strike_price: float) -> bool:
        """
        Buy NO contracts.
        
        Args:
            quantity: Number of contracts to buy
            price: Price per NO contract
            timestamp: Time of purchase
            strike_price: Strike price of the market
            
        Returns:
            True if trade executed, False if insufficient funds
        """
        if not self.can_afford(quantity, price):
            return False
        
        # Deduct cost and fees
        total_cost = quantity * price + quantity * self.fee_per_contract
        self.cash -= total_cost
        
        # Create position
        position = Position(
            contract_type="NO",
            quantity=quantity,
            entry_price=price,
            entry_time=timestamp,
            strike_price=strike_price
        )
        self.positions.append(position)
        
        # Record trade
        # Note: Both 'timestamp' and 'entry_timestamp' are kept for compatibility
        # 'entry_timestamp' is used by metrics for duration calculations
        self.trade_history.append({
            'timestamp': timestamp,
            'entry_timestamp': timestamp,
            'action': 'BUY_NO',
            'quantity': quantity,
            'price': price,
            'fees': quantity * self.fee_per_contract,
            'strike_price': strike_price
        })
        
        return True
    
    def resolve_positions(self, 
                         final_btc_price: float,
                         resolution_time: pd.Timestamp) -> float:
        """
        Resolve all positions at market expiry.
        
        Args:
            final_btc_price: Final BTC price at hour end
            resolution_time: Time of resolution
            
        Returns:
            Total PnL from position resolution
        """
        total_pnl = 0.0
        
        for position in self.positions:
            # Determine if position wins
            if position.contract_type == "YES":
                wins = final_btc_price >= position.strike_price
            else:  # NO
                wins = final_btc_price < position.strike_price
            
            # Calculate payout
            if wins:
                payout = position.quantity * 1.0  # Win pays $1 per contract
            else:
                payout = 0.0  # Loss pays $0
            
            # Calculate PnL (payout - cost)
            cost = position.quantity * position.entry_price
            pnl = payout - cost
            
            self.cash += payout
            total_pnl += pnl
            
            # Record resolution
            self.pnl_history.append({
                'timestamp': resolution_time,
                'exit_timestamp': resolution_time,
                'entry_timestamp': position.entry_time,
                'contract_type': position.contract_type,
                'quantity': position.quantity,
                'entry_price': position.entry_price,
                'payout': payout,
                'pnl': pnl,
                'strike_price': position.strike_price,
                'final_btc_price': final_btc_price,
                'win': wins
            })
        
        # Clear positions
        self.positions = []
        
        return total_pnl
    
    def get_total_value(self) -> float:
        """Get total portfolio value (cash + unrealized positions)."""
        # For unrealized positions, we'd need current market prices
        # For simplicity, just return cash for now
        return self.cash
    
    def get_total_pnl(self) -> float:
        """Get total realized PnL."""
        return self.cash - self.initial_balance
