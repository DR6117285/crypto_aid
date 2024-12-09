"""
Backtesting module for cryptocurrency trading strategies.
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Union
from datetime import datetime
import pandas as pd
import numpy as np

from .technical import TechnicalAnalysis, TradingSignal

@dataclass
class Trade:
    """Represents a completed trade with entry and exit information"""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    position_size: float
    profit_loss: float
    exit_reason: str  # 'take_profit', 'stop_loss', 'signal', etc.
    entry_signal: TradingSignal
    exit_signal: Optional[TradingSignal] = None

@dataclass
class BacktestResult:
    """Results of a backtest run"""
    pair: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    trades: List[Trade]
    market_condition: str
    metrics: Dict[str, float]

class Backtester:
    """Backtesting engine for technical analysis strategies"""
    
    def __init__(self, technical_analyzer: TechnicalAnalysis):
        self.analyzer = technical_analyzer
        
    def run(
        self,
        pair: str,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        initial_capital: float,
        position_size: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        dynamic_sizing: bool = False
    ) -> BacktestResult:
        """
        Run backtest for a given pair and time period
        
        Args:
            pair: Trading pair (e.g., "BTC/USD")
            start_date: Start date as string (YYYY-MM-DD) or datetime
            end_date: End date as string (YYYY-MM-DD) or datetime
            initial_capital: Initial capital to trade with
            position_size: Position size as fraction of capital (0-1)
            stop_loss: Optional stop loss as decimal (e.g., 0.02 for 2%)
            take_profit: Optional take profit as decimal (e.g., 0.04 for 4%)
            dynamic_sizing: Whether to adjust position size based on volatility
        
        Returns:
            BacktestResult object containing performance metrics and trade history
        """
        # Convert dates to timestamps
        if isinstance(start_date, str):
            start_ts = int(pd.Timestamp(start_date).timestamp())
        else:
            start_ts = int(pd.Timestamp(start_date).timestamp())
            
        if isinstance(end_date, str):
            end_ts = int(pd.Timestamp(end_date).timestamp())
        else:
            end_ts = int(pd.Timestamp(end_date).timestamp())
        
        # Get historical data
        ohlcv_data = self.analyzer.client.get_ohlcv(pair, '1d', start_ts, end_ts)
        if not ohlcv_data:
            raise ValueError(f"No data available for {pair} in specified date range")
        
        # Convert to DataFrame for easier processing
        df = pd.DataFrame(
            ohlcv_data,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('timestamp', inplace=True)
        
        # Initialize tracking variables
        capital = float(initial_capital)
        position = None
        trades: List[Trade] = []
        daily_returns = []
        
        # Calculate market condition
        market_condition = self._determine_market_condition(df)
        
        # Process each day
        for i in range(1, len(df)):
            current_date = df.index[i]
            current_price = float(df['close'].iloc[i])
            
            # Get analysis for current day
            historical_slice = df.iloc[max(0, i-30):i+1]
            historical_data = pd.DataFrame({
                'timestamp': historical_slice.index.astype(np.int64) // 10**9,
                'open': historical_slice['open'].astype(float),
                'high': historical_slice['high'].astype(float),
                'low': historical_slice['low'].astype(float),
                'close': historical_slice['close'].astype(float),
                'volume': historical_slice['volume'].astype(float)
            })
            
            # Create a temporary client with historical data
            class HistoricalClient:
                def __init__(self, data):
                    self.data = data.values.tolist()
                def get_ohlcv(self, *args, **kwargs):
                    return self.data
            
            temp_analyzer = TechnicalAnalysis(HistoricalClient(historical_data))
            analysis = temp_analyzer.analyze(
                [pair],
                timeframe='1d',
                indicators=['rsi', 'macd', 'bollinger', 'stochastic', 'atr']
            )
            if not analysis or pair not in analysis:
                continue
            
            signal = self.analyzer.generate_signal(pair, analysis[pair])
            
            # Calculate position size
            current_position_size = self._calculate_position_size(
                position_size,
                capital,
                dynamic_sizing,
                df.iloc[i-20:i] if i >= 20 else df.iloc[:i]
            )
            
            # Check for exit conditions if in position
            if position:
                exit_price = None
                exit_reason = None
                
                # Check stop loss
                if stop_loss and current_price <= position.entry_price * (1 - stop_loss):
                    exit_price = current_price
                    exit_reason = 'stop_loss'
                
                # Check take profit
                elif take_profit and current_price >= position.entry_price * (1 + take_profit):
                    exit_price = current_price
                    exit_reason = 'take_profit'
                
                # Check for exit signal
                elif signal.signal == 'sell' and signal.strength > 0.2:  
                    exit_price = current_price
                    exit_reason = 'signal'
                
                # Execute exit if conditions met
                if exit_price:
                    profit_loss = (exit_price - position.entry_price) * position.position_size
                    position_value = capital * position.position_size
                    capital += position_value * (exit_price - position.entry_price) / position.entry_price
                    
                    trades.append(Trade(
                        entry_time=position.entry_time,
                        exit_time=current_date,
                        entry_price=position.entry_price,
                        exit_price=exit_price,
                        position_size=position.position_size,
                        profit_loss=profit_loss,
                        exit_reason=exit_reason,
                        entry_signal=position.entry_signal,
                        exit_signal=signal
                    ))
                    
                    position = None
                
                # Handle end of period
                elif i == len(df) - 1:
                    profit_loss = (current_price - position.entry_price) * position.position_size
                    position_value = capital * position.position_size
                    capital += position_value * (current_price - position.entry_price) / position.entry_price
                    
                    # Use the next day for exit time
                    next_day = current_date + pd.Timedelta(days=1)
                    
                    trades.append(Trade(
                        entry_time=position.entry_time,
                        exit_time=next_day,  # Use next day for end-of-period trades
                        entry_price=position.entry_price,
                        exit_price=current_price,
                        position_size=position.position_size,
                        profit_loss=profit_loss,
                        exit_reason='end_of_period',
                        entry_signal=position.entry_signal,
                        exit_signal=None
                    ))
            
            # Check for entry conditions if not in position
            elif signal.signal == 'buy' and signal.strength > 0.2:  
                position = Trade(
                    entry_time=current_date,
                    exit_time=None,  
                    entry_price=current_price,
                    exit_price=0,  
                    position_size=current_position_size,  # Use dynamically calculated size
                    profit_loss=0,  
                    exit_reason='',  
                    entry_signal=signal,
                    exit_signal=None
                )
            
            # Calculate daily return
            daily_return = (df['close'].iloc[i] - df['close'].iloc[i-1]) / df['close'].iloc[i-1]
            daily_returns.append(daily_return)
        
        # Close any open position at the end
        if position:
            final_price = float(df['close'].iloc[-1])
            profit_loss = (final_price - position.entry_price) * position.position_size * capital
            capital += profit_loss
            
            trades.append(Trade(
                entry_time=position.entry_time,
                exit_time=df.index[-1],
                entry_price=position.entry_price,
                exit_price=final_price,
                position_size=position.position_size,
                profit_loss=profit_loss,
                exit_reason='end_of_period',
                entry_signal=position.entry_signal
            ))
        
        # Calculate metrics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.profit_loss > 0])
        losing_trades = len([t for t in trades if t.profit_loss < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Calculate profit factor (total gains / total losses)
        total_gains = sum(t.profit_loss for t in trades if t.profit_loss > 0)
        total_losses = abs(sum(t.profit_loss for t in trades if t.profit_loss < 0))
        profit_factor = total_gains / total_losses if total_losses > 0 else float('inf')
        
        # Calculate max drawdown
        peak = float(initial_capital)
        max_drawdown = 0.0
        running_capital = float(initial_capital)
        
        for trade in trades:
            running_capital += trade.profit_loss
            if running_capital > peak:
                peak = running_capital
            drawdown = (peak - running_capital) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        # Calculate Sharpe ratio (assuming risk-free rate of 0)
        if len(daily_returns) > 1:
            returns_array = np.array(daily_returns)
            sharpe_ratio = np.mean(returns_array) / np.std(returns_array) if np.std(returns_array) > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Calculate additional metrics
        total_return = (capital - initial_capital) / initial_capital
        trading_days = (df.index[-1] - df.index[0]).days
        annualized_return = ((1 + total_return) ** (365 / trading_days)) - 1 if trading_days > 0 else 0
        volatility = np.std(daily_returns) if len(daily_returns) > 1 else 0
        
        metrics = {
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': float(-max_drawdown),  # Make drawdown negative and ensure float
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility
        }
        
        return BacktestResult(
            pair=pair,
            start_date=df.index[0],
            end_date=df.index[-1],
            initial_capital=initial_capital,
            final_capital=capital,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=float(-max_drawdown),  # Make drawdown negative and ensure float
            trades=trades,
            market_condition=market_condition,
            metrics=metrics
        )
    
    def _calculate_position_size(
        self,
        base_size: float,
        capital: float,
        dynamic_sizing: bool,
        price_data: pd.DataFrame
    ) -> float:
        """Calculate position size based on strategy parameters"""
        if not dynamic_sizing or len(price_data) < 2:
            return base_size
            
        # Calculate volatility using price data
        returns = price_data['close'].pct_change().dropna()
        volatility = returns.std()
        
        # Adjust position size based on volatility
        # Higher volatility = smaller position size
        volatility_factor = 1 - np.clip(volatility * 10, 0, 0.5)  # Cap reduction at 50%
        
        # Ensure position size varies more in dynamic mode
        dynamic_size = base_size * volatility_factor
        if dynamic_size > base_size:
            dynamic_size = base_size * 1.2  # Allow up to 20% increase
        return dynamic_size
    
    def _determine_market_condition(self, df: pd.DataFrame) -> str:
        """Determine market condition (uptrend, downtrend, or sideways)"""
        if len(df) < 20:
            return 'unknown'
        
        # Calculate short and long term trends using EMAs
        ema20 = df['close'].ewm(span=20, adjust=False).mean()
        ema50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Calculate trend strength
        trend_strength = abs((ema20.iloc[-1] - ema50.iloc[-1]) / ema50.iloc[-1])
        
        if trend_strength < 0.02:  # 2% threshold for sideways market
            return 'sideways'
        elif ema20.iloc[-1] > ema50.iloc[-1]:
            return 'uptrend'
        else:
            return 'downtrend'
    
    def _calculate_metrics(
        self,
        trades: List[Trade],
        daily_returns: List[float],
        initial_capital: float,
        final_capital: float
    ) -> Dict[str, float]:
        """Calculate various performance metrics"""
        if not trades:
            return {
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'total_return': 0.0,
                'annualized_return': 0.0,
                'volatility': 0.0
            }
        
        # Basic metrics
        winning_trades = [t for t in trades if t.profit_loss > 0]
        losing_trades = [t for t in trades if t.profit_loss <= 0]
        
        win_rate = len(winning_trades) / len(trades)
        
        # Profit factor
        gross_profits = sum(t.profit_loss for t in winning_trades)
        gross_losses = abs(sum(t.profit_loss for t in losing_trades))
        profit_factor = gross_profits / gross_losses if gross_losses != 0 else float('inf')
        
        # Returns and volatility
        returns_array = np.array(daily_returns)
        volatility = np.std(returns_array) * np.sqrt(252)  # Annualized
        
        # Sharpe ratio (assuming risk-free rate of 2%)
        risk_free_rate = 0.02
        excess_returns = returns_array - risk_free_rate/252
        sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252) if len(returns_array) > 1 else 0
        
        # Maximum drawdown
        cumulative_returns = (1 + returns_array).cumprod()
        rolling_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = abs(min(drawdowns))
        
        # Total and annualized returns
        total_return = (final_capital - initial_capital) / initial_capital
        trading_days = len(daily_returns)
        annualized_return = (1 + total_return) ** (252/trading_days) - 1 if trading_days > 0 else 0
        
        return {
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility
        }
