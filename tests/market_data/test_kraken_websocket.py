"""
Tests for Kraken WebSocket client functionality.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime
from src.market_data.kraken_client import KrakenClient, KrakenError
from websockets.exceptions import ConnectionClosed

@pytest.fixture
def mock_websocket():
    """Fixture for mocked websocket connection."""
    with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws
        yield mock_ws

@pytest.fixture
def kraken_client():
    """Fixture for KrakenClient instance."""
    return KrakenClient()

class TestKrakenWebSocket:
    """Test suite for Kraken WebSocket functionality."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, kraken_client, mock_websocket):
        """Test WebSocket connection establishment."""
        await kraken_client.connect_websocket()
        assert kraken_client.is_ws_connected
        
    @pytest.mark.asyncio
    async def test_websocket_subscription(self, kraken_client, mock_websocket):
        """Test subscribing to WebSocket feeds."""
        pairs = ["XBT/USD", "ETH/USD"]
        subscription = {
            "event": "subscribe",
            "pair": pairs,
            "subscription": {"name": "ticker"}
        }
        
        await kraken_client.connect_websocket()
        await kraken_client.subscribe_ticker(pairs)
        
        mock_websocket.send.assert_called_with(json.dumps(subscription))
        
    @pytest.mark.asyncio
    async def test_websocket_message_handling(self, kraken_client, mock_websocket):
        """Test handling of incoming WebSocket messages."""
        # Mock ticker data
        ticker_data = {
            "e": "ticker",
            "s": "XBT/USD",
            "p": "50000.00",
            "v": "1.23456",
            "t": str(int(datetime.now().timestamp()))
        }
        
        mock_websocket.recv.return_value = json.dumps(ticker_data)
        
        await kraken_client.connect_websocket()
        message = await kraken_client.receive_message()
        
        assert message == ticker_data
        
    @pytest.mark.asyncio
    async def test_websocket_reconnection(self, kraken_client, mock_websocket):
        """Test automatic WebSocket reconnection."""
        # Simulate connection drop
        mock_websocket.recv.side_effect = [
            ConnectionClosed(None, None),
            json.dumps({"event": "connected"})
        ]
        
        await kraken_client.connect_websocket()
        with pytest.raises(ConnectionClosed):
            await kraken_client.receive_message()
            
        assert not kraken_client.is_ws_connected
        
        # Test reconnection
        await kraken_client.connect_websocket()
        assert kraken_client.is_ws_connected
        
    @pytest.mark.asyncio
    async def test_websocket_heartbeat(self, kraken_client, mock_websocket):
        """Test WebSocket heartbeat mechanism."""
        heartbeat = {"event": "heartbeat"}
        mock_websocket.recv.return_value = json.dumps(heartbeat)
        
        await kraken_client.connect_websocket()
        message = await kraken_client.receive_message()
        
        assert message == heartbeat
        assert kraken_client.last_heartbeat is not None
        
    @pytest.mark.asyncio
    async def test_websocket_unsubscribe(self, kraken_client, mock_websocket):
        """Test unsubscribing from WebSocket feeds."""
        pairs = ["XBT/USD"]
        unsubscribe = {
            "event": "unsubscribe",
            "pair": pairs,
            "subscription": {"name": "ticker"}
        }
        
        await kraken_client.connect_websocket()
        await kraken_client.unsubscribe_ticker(pairs)
        
        mock_websocket.send.assert_called_with(json.dumps(unsubscribe))
        
    @pytest.mark.asyncio
    async def test_websocket_error_handling(self, kraken_client, mock_websocket):
        """Test handling of WebSocket errors."""
        error_msg = {
            "event": "error",
            "errorMessage": "Invalid subscription"
        }
        mock_websocket.recv.return_value = json.dumps(error_msg)
        
        await kraken_client.connect_websocket()
        with pytest.raises(KrakenError, match="WebSocket error: Invalid subscription"):
            await kraken_client.receive_message()
