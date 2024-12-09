"""
Trade recommendation module based on technical analysis.
"""
from typing import Dict, List
from .technical import TechnicalAnalysis

class TradeRecommender:
    def __init__(self, analyzer: TechnicalAnalysis):
        self.analyzer = analyzer

    def get_recommendations(self, pairs: List[str], risk_level: str = 'medium', min_confidence: int = 70) -> Dict:
        """Generate trade recommendations based on technical analysis"""
        recommendations = {}
        
        # Adjust thresholds based on risk level
        if risk_level == 'low':
            rsi_oversold = 25
            rsi_overbought = 75
            min_confidence = max(min_confidence, 80)
        elif risk_level == 'high':
            rsi_oversold = 35
            rsi_overbought = 65
            min_confidence = min(min_confidence, 60)
        else:  # medium
            rsi_oversold = 30
            rsi_overbought = 70
        
        for pair in pairs:
            analysis = self.analyzer.analyze(pair)
            
            # Initialize recommendation
            recommendation = {
                'signal': 'HOLD',
                'confidence': 50,
                'reasons': []
            }
            
            # RSI Analysis
            rsi = analysis[pair]['rsi']
            if rsi < rsi_oversold:
                recommendation['signal'] = 'BUY'
                recommendation['confidence'] += 20
                recommendation['reasons'].append(f'Oversold (RSI: {rsi:.2f})')
            elif rsi > rsi_overbought:
                recommendation['signal'] = 'SELL'
                recommendation['confidence'] += 20
                recommendation['reasons'].append(f'Overbought (RSI: {rsi:.2f})')
            
            # MACD Analysis
            if 'macd' in analysis[pair]:
                macd = analysis[pair]['macd']
                macd_signal = analysis[pair]['macd_signal']
                
                if macd > macd_signal:
                    if recommendation['signal'] == 'BUY':
                        recommendation['confidence'] += 15
                    elif recommendation['signal'] == 'HOLD':
                        recommendation['signal'] = 'BUY'
                        recommendation['confidence'] += 10
                    recommendation['reasons'].append('MACD crossed above signal line')
                elif macd < macd_signal:
                    if recommendation['signal'] == 'SELL':
                        recommendation['confidence'] += 15
                    elif recommendation['signal'] == 'HOLD':
                        recommendation['signal'] = 'SELL'
                        recommendation['confidence'] += 10
                    recommendation['reasons'].append('MACD crossed below signal line')
            
            # Bollinger Bands Analysis
            if all(k in analysis[pair] for k in ['bb_upper', 'bb_middle', 'bb_lower']):
                price = self.analyzer.client.get_ticker_info([pair])[pair]['last']
                
                if price < analysis[pair]['bb_lower']:
                    if recommendation['signal'] == 'BUY':
                        recommendation['confidence'] += 15
                    elif recommendation['signal'] == 'HOLD':
                        recommendation['signal'] = 'BUY'
                        recommendation['confidence'] += 10
                    recommendation['reasons'].append('Price below lower Bollinger Band')
                elif price > analysis[pair]['bb_upper']:
                    if recommendation['signal'] == 'SELL':
                        recommendation['confidence'] += 15
                    elif recommendation['signal'] == 'HOLD':
                        recommendation['signal'] = 'SELL'
                        recommendation['confidence'] += 10
                    recommendation['reasons'].append('Price above upper Bollinger Band')
            
            # Filter low confidence signals
            if recommendation['confidence'] < min_confidence:
                recommendation['signal'] = 'HOLD'
                recommendation['reasons'] = ['No strong signals detected']
            
            recommendations[pair] = recommendation
        
        return recommendations
