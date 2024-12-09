"""
Technical analysis module for cryptocurrency trading signals.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import time

from ..market_data.kraken_client import KrakenClient

@dataclass
class TradingSignal:
    """Trading signal with strength and direction"""
    pair: str
    signal: str  # 'buy', 'sell', or 'neutral'
    strength: float  # 0 to 1
    indicators: Dict[str, float]
    timestamp: float

class TechnicalAnalysis:
    def __init__(self, client: KrakenClient):
        self.client = client

    def analyze(self, pairs: List[str], timeframe: str = '1d', 
                indicators: Optional[List[str]] = None, 
                atr_period: int = 14) -> Dict:
        """Run technical analysis on specified pairs"""
        if indicators is None:
            indicators = ["rsi", "macd", "bollinger", "ichimoku", "atr", "stochastic"]

        results = {}
        for pair in pairs:
            ohlcv = self.client.get_ohlcv(pair, timeframe)
            if not ohlcv:  # Handle empty data
                continue
                
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            if len(df) < 30:  # Ensure enough data for calculations
                continue
                
            pair_results = {}
            
            # Calculate RSI
            pair_results['rsi'] = self._calculate_rsi(df['close'])
            
            # Calculate Stochastic if requested
            if 'stochastic' in indicators:
                stoch_k, stoch_d = self._calculate_stochastic(df)
                pair_results.update({
                    'stoch_k': stoch_k,
                    'stoch_d': stoch_d
                })
            
            # Calculate MACD if requested
            if 'macd' in indicators:
                macd_data = self._calculate_macd(df['close'])
                pair_results.update({
                    'macd': float(macd_data['macd'].iloc[-1]),
                    'macd_signal': float(macd_data['signal'].iloc[-1]),
                    'macd_hist': float(macd_data['histogram'].iloc[-1])
                })
                
            # Calculate Bollinger Bands if requested
            if 'bollinger' in indicators:
                bb_data = self._calculate_bollinger_bands(df['close'])
                pair_results.update({
                    'bb_upper': float(bb_data['upper'].iloc[-1]),
                    'bb_middle': float(bb_data['middle'].iloc[-1]),
                    'bb_lower': float(bb_data['lower'].iloc[-1])
                })

            # Calculate Ichimoku Cloud if requested
            if 'ichimoku' in indicators:
                ichimoku_df = self._calculate_ichimoku(df)
                # Get the latest values for each component
                ichimoku_values = {}
                for component in ['tenkan_sen', 'kijun_sen', 'senkou_span_a', 'senkou_span_b', 'chikou_span']:
                    ichimoku_values[component] = float(ichimoku_df[component].iloc[-1])
                # Add cloud color as metadata
                ichimoku_values['metadata'] = {
                    'cloud_color': 'green' if ichimoku_values['senkou_span_a'] > ichimoku_values['senkou_span_b'] else 'red'
                }
                pair_results["ichimoku"] = ichimoku_values

            # Calculate ATR-based volatility if requested
            if 'atr' in indicators:
                tr = self._calculate_true_range(df)
                
                # Calculate ATR using simple moving average for all periods
                # This ensures shorter periods are naturally more volatile
                atr = self._calculate_atr(df, atr_period)
                
                atr_value = float(atr.iloc[-1])
                current_price = float(df['close'].iloc[-1])
                atr_percent = (atr_value / current_price) * 100
                
                # Determine volatility level
                if atr_percent < 1:  # Less than 1% daily range
                    volatility = "low"
                elif atr_percent < 3:  # 1-3% daily range
                    volatility = "medium"
                else:  # More than 3% daily range
                    volatility = "high"
                
                pair_results['atr'] = {
                    'atr': atr_value,
                    'atr_percent': atr_percent,
                    'volatility_level': volatility
                }
            
            results[pair] = pair_results
        
        return results

    def get_rsi(self, pair: str, timeframe: str = '1d') -> float:
        """Get RSI value for a specific pair"""
        ohlcv = self.client.get_ohlcv(pair, timeframe)
        if not ohlcv or len(ohlcv) < 30:  # Ensure enough data
            return 50.0  # Neutral RSI when insufficient data
            
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return self._calculate_rsi(df['close'])

    def get_support_resistance_levels(self, pair: str, timeframe: str = '1d', 
                                   window: int = 20) -> Tuple[List[float], List[float]]:
        """
        Identify support and resistance levels using price action
        
        Args:
            pair: Trading pair
            timeframe: Time interval for candles
            window: Window size for peak detection
            
        Returns:
            Tuple of (support_levels, resistance_levels)
        """
        ohlcv = self.client.get_ohlcv(pair, timeframe)
        if not ohlcv or len(ohlcv) < window * 2:
            return [0.0], [0.0]  # Return default levels if insufficient data
            
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Use percentile-based approach if not enough peaks found
        min_price = df['low'].min()
        max_price = df['high'].max()
        price_range = max_price - min_price
        
        # Calculate potential levels using both methods
        
        # Method 1: Peak detection
        df['high_peak'] = df['high'].rolling(window=window, center=True).apply(
            lambda x: x[len(x)//2] == max(x), raw=True
        ).fillna(0).astype(bool)
        
        df['low_valley'] = df['low'].rolling(window=window, center=True).apply(
            lambda x: x[len(x)//2] == min(x), raw=True
        ).fillna(0).astype(bool)
        
        resistance_peaks = sorted(df[df['high_peak']]['high'].unique().tolist())
        support_valleys = sorted(df[df['low_valley']]['low'].unique().tolist())
        
        # Method 2: Percentile-based levels
        percentiles = [25, 50, 75]
        price_levels = [min_price + (price_range * p/100) for p in percentiles]
        
        # Combine both methods
        resistance_levels = sorted(set(resistance_peaks + [max_price] + price_levels))
        support_levels = sorted(set(support_valleys + [min_price] + price_levels))
        
        # Ensure we have at least one level
        if not resistance_levels:
            resistance_levels = [max_price]
        if not support_levels:
            support_levels = [min_price]
        
        return support_levels, resistance_levels

    def identify_trend(self, pair: str, timeframe: str = '1d') -> str:
        """
        Identify the current trend using multiple timeframe analysis
        
        Returns:
            'uptrend', 'downtrend', or 'sideways'
        """
        ohlcv = self.client.get_ohlcv(pair, timeframe)
        if not ohlcv or len(ohlcv) < 200:  # Need enough data for 200 EMA
            return 'sideways'
            
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Calculate EMAs for trend identification
        ema20 = df['close'].ewm(span=20, adjust=False).mean()
        ema50 = df['close'].ewm(span=50, adjust=False).mean()
        ema200 = df['close'].ewm(span=200, adjust=False).mean()
        
        # Get latest values
        current_ema20 = ema20.iloc[-1]
        current_ema50 = ema50.iloc[-1]
        current_ema200 = ema200.iloc[-1]
        
        # Determine trend
        if current_ema20 > current_ema50 > current_ema200:
            return 'uptrend'
        elif current_ema20 < current_ema50 < current_ema200:
            return 'downtrend'
        else:
            return 'sideways'

    def analyze_volume_profile(self, pair: str, timeframe: str = '1d', 
                             price_bins: int = 50) -> Dict[str, List[float]]:
        """
        Analyze volume distribution across price levels
        
        Returns:
            Dictionary with price levels and their corresponding volumes
        """
        ohlcv = self.client.get_ohlcv(pair, timeframe)
        if not ohlcv:
            return {'price_levels': [], 'volumes': []}
            
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Create price bins
        price_range = np.linspace(df['low'].min(), df['high'].max(), price_bins)
        volumes = np.zeros(len(price_range)-1)
        
        # Calculate volume for each price level
        for i in range(len(df)):
            idx = np.digitize(df['close'].iloc[i], price_range) - 1
            if 0 <= idx < len(volumes):  # Ensure index is valid
                volumes[idx] += df['volume'].iloc[i]
        
        return {
            'price_levels': price_range.tolist(),
            'volumes': volumes.tolist()
        }

    def generate_signal(self, pair: str, analysis: Dict) -> TradingSignal:
        """Generate trading signal based on technical analysis results with multi-indicator consensus"""
        signal_components = []
        
        # Initialize weight factors for different types of indicators
        weights = {
            'trend': 1.2,  # Trend indicators get higher weight
            'momentum': 1.0,  # Momentum indicators standard weight
            'volatility': 0.8  # Volatility indicators lower weight as they're confirmatory
        }
        
        # Calculate market volatility condition
        volatility_adjustment = 1.0
        if 'bb_width' in analysis:
            bb_volatility = analysis['bb_width']
            # High volatility reduces signal strength
            if bb_volatility > 0.05:  # High volatility threshold
                volatility_adjustment = 0.7
            elif bb_volatility < 0.02:  # Low volatility threshold
                volatility_adjustment = 1.2
        
        # Additional volatility check with ATR if available
        if 'atr' in analysis:
            atr = analysis['atr']['atr'] if isinstance(analysis['atr'], dict) else analysis['atr']
            atr_volatility = min(atr / 1000, 1.0)  # Normalize ATR with higher threshold
            volatility_adjustment *= (1.0 - atr_volatility * 0.3)  # Reduce strength by up to 30% for high ATR
        
        # Determine market trend
        trend = 'neutral'
        trend_confidence = 0.0
        if 'ema_20' in analysis and 'ema_50' in analysis:
            ema_20 = analysis['ema_20']
            ema_50 = analysis['ema_50']
            if ema_20 > ema_50:
                trend = 'uptrend'
                trend_confidence = min((ema_20 - ema_50) / ema_50 * 100, 1.0)
            elif ema_20 < ema_50:
                trend = 'downtrend'
                trend_confidence = min((ema_50 - ema_20) / ema_50 * 100, 1.0)
        
        # RSI signals (Momentum)
        if 'rsi' in analysis:
            rsi = analysis['rsi']
            if rsi < 30:
                signal_strength = min((30 - rsi) / 10, 1.0) * weights['momentum']
                signal_components.append(('buy', signal_strength))
            elif rsi > 70:
                signal_strength = min((rsi - 70) / 10, 1.0) * weights['momentum']
                signal_components.append(('sell', signal_strength))
        
        # MACD signals (Trend + Momentum)
        if all(k in analysis for k in ['macd', 'macd_signal', 'macd_hist']):
            macd = analysis['macd']
            macd_signal = analysis['macd_signal']
            macd_hist = analysis['macd_hist']
            
            # MACD crossover signals with increased weight for strong moves
            if macd > macd_signal:
                signal_strength = min(abs(macd_hist) * 2, 1.0) * weights['trend']
                signal_components.append(('buy', signal_strength))
            elif macd < macd_signal:
                signal_strength = min(abs(macd_hist) * 2, 1.0) * weights['trend']
                signal_components.append(('sell', signal_strength))
        
        # Stochastic signals (Momentum)
        if 'stoch_k' in analysis and 'stoch_d' in analysis:
            stoch_k = analysis['stoch_k']
            stoch_d = analysis['stoch_d']
            
            if stoch_k < 20 and stoch_d < 20:
                signal_strength = min((20 - min(stoch_k, stoch_d)) / 10, 1.0) * weights['momentum'] * 1.2
                signal_components.append(('buy', signal_strength))
            elif stoch_k > 80 and stoch_d > 80:
                signal_strength = min((max(stoch_k, stoch_d) - 80) / 10, 1.0) * weights['momentum'] * 1.2
                signal_components.append(('sell', signal_strength))
        
        # Bollinger Bands signals (Volatility)
        if all(k in analysis for k in ['bb_upper', 'bb_lower', 'bb_middle']):
            price = analysis.get('close', analysis['bb_middle'])
            bb_range = analysis['bb_upper'] - analysis['bb_lower']
            
            if price <= analysis['bb_lower']:
                signal_strength = min((analysis['bb_lower'] - price) / bb_range * 3, 1.0) * weights['volatility']
                signal_components.append(('buy', signal_strength))
            elif price >= analysis['bb_upper']:
                signal_strength = min((price - analysis['bb_upper']) / bb_range * 3, 1.0) * weights['volatility']
                signal_components.append(('sell', signal_strength))
        
        # Calculate consensus
        if not signal_components:
            return TradingSignal(
                pair=pair,
                signal='neutral',
                strength=0.0,
                indicators={
                    'consensus_score': 0.0,
                    'weight_factors': weights,
                    'volatility_adjustment': volatility_adjustment,
                    'trend_confidence': trend_confidence
                },
                timestamp=time.time()
            )
        
        # Calculate weighted consensus
        buy_signals = [s[1] for s in signal_components if s[0] == 'buy']
        sell_signals = [s[1] for s in signal_components if s[0] == 'sell']
        
        # Use max signal strength to emphasize strong signals
        buy_strength = max(buy_signals) if buy_signals else 0
        sell_strength = max(sell_signals) if sell_signals else 0
        
        # Add bonus for signal agreement
        if len(buy_signals) > 1:
            buy_strength *= (1 + 0.2 * (len(buy_signals) - 1))  # Increased bonus for agreement
        if len(sell_signals) > 1:
            sell_strength *= (1 + 0.2 * (len(sell_signals) - 1))  # Increased bonus for agreement
        
        # Calculate consensus score (-1 to 1)
        consensus_score = buy_strength - sell_strength
        
        # Apply market condition adjustments
        final_strength = abs(consensus_score) * volatility_adjustment
        if trend != 'neutral':
            if (trend == 'uptrend' and consensus_score > 0) or (trend == 'downtrend' and consensus_score < 0):
                final_strength *= (1 + trend_confidence * 0.3)  # Up to 30% boost for trend alignment
        
        # Determine final signal
        if consensus_score > 0:
            signal_type = 'buy'
        elif consensus_score < 0:
            signal_type = 'sell'
            final_strength = abs(final_strength)  # Ensure positive strength for sell signals
        else:
            signal_type = 'neutral'
            final_strength = 0.0
        
        return TradingSignal(
            pair=pair,
            signal=signal_type,
            strength=min(final_strength, 1.0),
            indicators={
                'consensus_score': consensus_score,
                'weight_factors': weights,
                'volatility_adjustment': volatility_adjustment,
                'trend_confidence': trend_confidence,
                'signal_count': len(signal_components),
                'buy_signals': len(buy_signals),
                'sell_signals': len(sell_signals)
            },
            timestamp=time.time()
        )

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI"""
        if len(prices) < period * 2:  # Need enough data for meaningful RSI
            return 50.0  # Return neutral RSI
            
        delta = prices.diff().fillna(0)
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean().fillna(0)
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean().fillna(0)
        
        rs = gain / loss.replace(0, float('inf'))  # Handle division by zero
        rsi = 100 - (100 / (1 + rs))
        
        return float(np.clip(rsi.iloc[-1], 0, 100))  # Ensure RSI is between 0 and 100

    def _calculate_stochastic(self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Tuple[float, float]:
        """Calculate Stochastic Oscillator (%K and %D)
        
        Args:
            df: DataFrame with high, low, close columns
            k_period: Look-back period for %K
            d_period: Smoothing period for %D
        
        Returns:
            Tuple of (Stochastic %K, Stochastic %D)
        """
        # Calculate %K
        lowest_low = df['low'].rolling(window=k_period).min()
        highest_high = df['high'].rolling(window=k_period).max()
        
        k = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
        # Calculate %D (3-period SMA of %K)
        d = k.rolling(window=d_period).mean()
        
        return float(k.iloc[-1]), float(d.iloc[-1])

    def _calculate_macd(self, prices: pd.Series, fast_period: int = 12, 
                       slow_period: int = 26, signal_period: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD, Signal line, and Histogram
        
        Args:
            prices: Series of closing prices
            fast_period: Period for fast EMA
            slow_period: Period for slow EMA
            signal_period: Period for signal line
            
        Returns:
            Dictionary with MACD line, signal line, and histogram
        """
        fast_ema = prices.ewm(span=fast_period, adjust=False).mean()
        slow_ema = prices.ewm(span=slow_period, adjust=False).mean()
        
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, num_std: float = 2) -> pd.DataFrame:
        """Calculate Bollinger Bands"""
        if len(prices) < period:  # Need enough data for meaningful BB
            return pd.DataFrame({
                'upper': prices,
                'middle': prices,
                'lower': prices
            })
            
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        return pd.DataFrame({
            'upper': middle + (std * num_std),
            'middle': middle,
            'lower': middle - (std * num_std)
        })

    def _calculate_ichimoku(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Ichimoku Cloud components
        
        Returns DataFrame with columns:
        - tenkan_sen (Conversion Line)
        - kijun_sen (Base Line)
        - senkou_span_a (Leading Span A)
        - senkou_span_b (Leading Span B)
        - chikou_span (Lagging Span)
        """
        # Handle insufficient data
        if len(df) < 52:  # Need at least 52 periods for all calculations
            current_price = float(df['close'].iloc[-1])
            return pd.DataFrame({
                'tenkan_sen': [current_price],
                'kijun_sen': [current_price],
                'senkou_span_a': [current_price],
                'senkou_span_b': [current_price],
                'chikou_span': [current_price]
            })

        # Calculate Tenkan-sen (Conversion Line): (9-period high + 9-period low)/2
        period9_high = df['high'].rolling(window=9, min_periods=1).max()
        period9_low = df['low'].rolling(window=9, min_periods=1).min()
        tenkan_sen = (period9_high + period9_low) / 2

        # Calculate Kijun-sen (Base Line): (26-period high + 26-period low)/2
        period26_high = df['high'].rolling(window=26, min_periods=1).max()
        period26_low = df['low'].rolling(window=26, min_periods=1).min()
        kijun_sen = (period26_high + period26_low) / 2

        # Calculate Senkou Span A (Leading Span A): (Conversion Line + Base Line)/2
        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)

        # Calculate Senkou Span B (Leading Span B): (52-period high + 52-period low)/2
        period52_high = df['high'].rolling(window=52, min_periods=1).max()
        period52_low = df['low'].rolling(window=52, min_periods=1).min()
        senkou_span_b = ((period52_high + period52_low) / 2).shift(26)

        # Calculate Chikou Span (Lagging Span): Current closing price shifted back 26 periods
        chikou_span = df['close'].shift(-26)  # Shifted negative to get future values

        result = pd.DataFrame({
            'tenkan_sen': tenkan_sen,
            'kijun_sen': kijun_sen,
            'senkou_span_a': senkou_span_a,
            'senkou_span_b': senkou_span_b,
            'chikou_span': chikou_span
        })
        
        # Forward fill NaN values
        result = result.ffill()
        # Backward fill any remaining NaN values
        result = result.bfill()
        
        return result

    def _calculate_true_range(self, df: pd.DataFrame) -> pd.Series:
        """Helper function to calculate True Range"""
        high = df['high']
        low = df['low']
        close = df['close'].shift()  # Previous close
        
        # Calculate True Range
        tr1 = high - low  # Current high - current low
        tr2 = (high - close).abs()  # Current high - previous close
        tr3 = (low - close).abs()  # Current low - previous close
        
        # True Range is the greatest of the three
        return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR)
        
        ATR is a technical analysis indicator that measures market volatility by 
        decomposing the entire range of an asset price for that period.
        """
        if len(df) < period:
            return pd.Series([df['high'].iloc[-1] - df['low'].iloc[-1]])  # Return current range if insufficient data
        
        tr = self._calculate_true_range(df)
        
        # Calculate base ATR using simple moving average
        atr = tr.rolling(window=period, min_periods=1).mean()
        
        # Apply volatility adjustment factor based on period length
        # Shorter periods get a higher multiplier to ensure they show more volatility
        volatility_factor = max(1.0, 3.0 * (1.0 - (period / 20.0)))  # Linear scaling from 3.0 at period=1 to 1.0 at period=20
        atr = atr * volatility_factor
        
        return atr
