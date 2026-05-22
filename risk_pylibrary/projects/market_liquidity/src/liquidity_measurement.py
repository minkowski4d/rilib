import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Position:
    """Represents a trading position"""
    symbol: str
    quantity: float
    market_price: float
    bid_price: float
    ask_price: float
    avg_daily_volume: float
    position_value: float = None

    def __post_init__(self):
        if self.position_value is None:
            self.position_value = abs(self.quantity * self.market_price)


class LiquidityAnalyzer:
    """Analyzes liquidity/illiquidity metrics for a trading book"""

    def __init__(self, positions: List[Position]):
        self.positions = positions
        self.metrics = {}

    def calculate_bid_ask_spread(self, position: Position) -> Dict[str, float]:
        """Calculate bid-ask spread metrics"""
        spread = position.ask_price - position.bid_price
        mid_price = (position.bid_price + position.ask_price) / 2

        return {
            'absolute_spread': spread,
            'relative_spread': (spread / mid_price) * 100,  # in percentage
            'spread_bps': (spread / mid_price) * 10000  # in basis points
        }

    def calculate_amihud_illiquidity(self, position: Position,
                                     returns: Optional[float] = None) -> float:
        """
        Calculate Amihud Illiquidity Ratio
        Measures price impact per unit of volume
        Higher values = more illiquid
        """
        if returns is None:
            returns = 0.01  # assume 1% daily return as default

        if position.avg_daily_volume == 0:
            return np.inf

        return abs(returns) / (position.avg_daily_volume * position.market_price)

    def calculate_volume_liquidity_ratio(self, position: Position) -> float:
        """
        Calculate position size relative to average daily volume
        Higher ratio = harder to liquidate without market impact
        """
        if position.avg_daily_volume == 0:
            return np.inf

        days_to_liquidate = abs(position.quantity) / position.avg_daily_volume
        return days_to_liquidate

    def calculate_market_impact(self, position: Position,
                               participation_rate: float = 0.1) -> Dict[str, float]:
        """
        Estimate market impact of liquidating position
        participation_rate: fraction of daily volume we can trade (default 10%)
        """
        spread_metrics = self.calculate_bid_ask_spread(position)
        volume_ratio = self.calculate_volume_liquidity_ratio(position)

        # Simple market impact model: impact increases with volume ratio
        # Temporary impact (bid-ask spread cost)
        temporary_impact = spread_metrics['relative_spread'] / 2

        # Permanent impact (price movement from large order)
        # This is a simplified model; real models are more complex
        permanent_impact = (volume_ratio / participation_rate) * 0.1  # 0.1% per day of volume

        total_impact_pct = temporary_impact + permanent_impact
        total_impact_value = (total_impact_pct / 100) * position.position_value

        return {
            'temporary_impact_pct': temporary_impact,
            'permanent_impact_pct': permanent_impact,
            'total_impact_pct': total_impact_pct,
            'total_impact_value': total_impact_value,
            'days_to_liquidate': volume_ratio / participation_rate
        }

    def calculate_liquidity_score(self, position: Position) -> float:
        """
        Calculate composite liquidity score (0-100)
        100 = highly liquid, 0 = highly illiquid
        """
        spread_metrics = self.calculate_bid_ask_spread(position)
        volume_ratio = self.calculate_volume_liquidity_ratio(position)

        # Normalize metrics (lower is better for liquidity)
        spread_score = max(0, 100 - spread_metrics['spread_bps'])
        volume_score = max(0, 100 - (volume_ratio * 20))  # penalize if takes >5 days

        # Weighted average
        liquidity_score = (spread_score * 0.6 + volume_score * 0.4)

        return max(0, min(100, liquidity_score))

    def analyze_position(self, position: Position) -> Dict:
        """Complete liquidity analysis for a single position"""
        spread_metrics = self.calculate_bid_ask_spread(position)
        amihud = self.calculate_amihud_illiquidity(position)
        volume_ratio = self.calculate_volume_liquidity_ratio(position)
        market_impact = self.calculate_market_impact(position)
        liquidity_score = self.calculate_liquidity_score(position)

        return {
            'symbol': position.symbol,
            'position_value': position.position_value,
            'bid_ask_spread_bps': spread_metrics['spread_bps'],
            'relative_spread_pct': spread_metrics['relative_spread'],
            'amihud_illiquidity': amihud,
            'days_to_liquidate_10pct': volume_ratio / 0.1,
            'estimated_liquidation_cost_pct': market_impact['total_impact_pct'],
            'estimated_liquidation_cost_value': market_impact['total_impact_value'],
            'liquidity_score': liquidity_score,
            'liquidity_rating': self._get_rating(liquidity_score)
        }

    def _get_rating(self, score: float) -> str:
        """Convert liquidity score to rating"""
        if score >= 80:
            return 'Highly Liquid'
        elif score >= 60:
            return 'Liquid'
        elif score >= 40:
            return 'Moderately Liquid'
        elif score >= 20:
            return 'Illiquid'
        else:
            return 'Highly Illiquid'

    def analyze_book(self) -> pd.DataFrame:
        """Analyze entire trading book"""
        results = []
        for position in self.positions:
            results.append(self.analyze_position(position))

        df = pd.DataFrame(results)
        return df.sort_values('liquidity_score', ascending=False)

    def get_book_summary(self) -> Dict:
        """Get summary statistics for the entire book"""
        df = self.analyze_book()

        total_book_value = df['position_value'].sum()
        weighted_avg_spread = (df['bid_ask_spread_bps'] * df['position_value']).sum() / total_book_value
        weighted_liquidation_cost = (df['estimated_liquidation_cost_value']).sum()

        return {
            'total_positions': len(self.positions),
            'total_book_value': total_book_value,
            'weighted_avg_spread_bps': weighted_avg_spread,
            'total_estimated_liquidation_cost': weighted_liquidation_cost,
            'liquidation_cost_pct_of_book': (weighted_liquidation_cost / total_book_value) * 100,
            'avg_liquidity_score': df['liquidity_score'].mean(),
            'highly_illiquid_positions': len(df[df['liquidity_score'] < 20]),
            'liquid_positions': len(df[df['liquidity_score'] >= 60])
        }


def example_usage():
    """Example usage of the LiquidityAnalyzer"""

    # Example trading book
    positions = [
        Position(
            symbol='AAPL',
            quantity=10000,
            market_price=180.50,
            bid_price=180.48,
            ask_price=180.52,
            avg_daily_volume=50_000_000
        ),
        Position(
            symbol='TSLA',
            quantity=5000,
            market_price=242.80,
            bid_price=242.70,
            ask_price=242.90,
            avg_daily_volume=100_000_000
        ),
        Position(
            symbol='SMALLCAP',
            quantity=50000,
            market_price=15.25,
            bid_price=15.10,
            ask_price=15.40,
            avg_daily_volume=100_000
        ),
        Position(
            symbol='MICROCAP',
            quantity=100000,
            market_price=2.50,
            bid_price=2.40,
            ask_price=2.60,
            avg_daily_volume=50_000
        )
    ]

    # Analyze liquidity
    analyzer = LiquidityAnalyzer(positions)

    # Get detailed position analysis
    print("=" * 80)
    print("POSITION-LEVEL LIQUIDITY ANALYSIS")
    print("=" * 80)
    results_df = analyzer.analyze_book()
    print(results_df.to_string(index=False))

    # Get book summary
    print("\n" + "=" * 80)
    print("TRADING BOOK SUMMARY")
    print("=" * 80)
    summary = analyzer.get_book_summary()
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"{key}: {value:,.2f}")
        else:
            print(f"{key}: {value}")


if __name__ == "__main__":
    example_usage()
