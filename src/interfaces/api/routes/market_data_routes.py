"""
Market Data API Routes
Consolidated market data endpoints from all modules
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import BaseModel

from ..dependencies import get_application_service, get_correlation_id
from src.application.services.market_data_application_service import MarketDataApplicationService
from src.domain.market_data.entities.market_data import MarketData
from src.domain.market_data.value_objects.ohlcv import OHLCV

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models for API requests/responses
class MarketDataCreateRequest(BaseModel):
    """Request model for creating market data"""
    symbol: str
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    exchange: str = "NSE"


class MarketDataResponse(BaseModel):
    """Response model for market data"""
    symbol: str
    timestamp: str
    timeframe: str
    ohlcv: dict
    date_partition: str

    @classmethod
    def from_entity(cls, entity: MarketData) -> 'MarketDataResponse':
        """Create response from domain entity"""
        return cls(
            symbol=entity.symbol,
            timestamp=entity.parsed_timestamp.isoformat(),
            timeframe=entity.timeframe,
            ohlcv={
                'open': entity.ohlcv.open,
                'high': entity.ohlcv.high,
                'low': entity.ohlcv.low,
                'close': entity.ohlcv.close,
                'volume': entity.ohlcv.volume
            },
            date_partition=entity.date_partition
        )


class MarketDataSummaryResponse(BaseModel):
    """Response model for market data summary"""
    symbol: str
    period_days: int
    total_records: int
    average_price: float
    price_change_percent: float
    volatility: float
    volume_trend: str


@router.get("/current/{symbol}")
async def get_current_market_data(
    symbol: str,
    timeframe: str = Query("1D", description="Data timeframe"),
    service: MarketDataApplicationService = Depends(get_application_service),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Get current market data for a symbol

    Args:
        symbol: Trading symbol (e.g., AAPL, RELIANCE)
        timeframe: Data timeframe (1D, 1H, etc.)
        service: Application service
        correlation_id: Request correlation ID

    Returns:
        Current market data
    """
    try:
        logger.info(f"API: Getting current market data for {symbol}", extra={'correlation_id': correlation_id})

        result = await service.get_current_market_data(symbol, timeframe)

        if not result.success:
            raise HTTPException(
                status_code=404,
                detail=f"Market data not found for symbol: {symbol}"
            )

        if result.data:
            return MarketDataResponse.from_entity(result.data)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No current market data available for {symbol}"
            )

    except Exception as e:
        logger.error(f"Error getting current market data for {symbol}: {e}", extra={'correlation_id': correlation_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{symbol}")
async def get_market_data_history(
    symbol: str,
    days: int = Query(30, description="Number of days of history"),
    limit: int = Query(1000, description="Maximum records to return"),
    service: MarketDataApplicationService = Depends(get_application_service),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Get historical market data for a symbol

    Args:
        symbol: Trading symbol
        days: Number of days of historical data
        limit: Maximum number of records
        service: Application service
        correlation_id: Request correlation ID

    Returns:
        Historical market data records
    """
    try:
        logger.info(f"API: Getting {days} days history for {symbol}", extra={'correlation_id': correlation_id})

        result = await service.get_market_data_history(symbol, days=days, limit=limit)

        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve history for {symbol}: {result.error_message}"
            )

        # Convert domain entities to response models
        response_data = []
        if result.data:
            for record in result.data:
                if isinstance(record, MarketData):
                    response_data.append(MarketDataResponse.from_entity(record))

        return {
            "symbol": symbol,
            "record_count": len(response_data),
            "data": response_data,
            "metadata": result.metadata
        }

    except Exception as e:
        logger.error(f"Error getting market data history for {symbol}: {e}", extra={'correlation_id': correlation_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_market_data(
    request: MarketDataCreateRequest,
    service: MarketDataApplicationService = Depends(get_application_service),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Create new market data record

    Args:
        request: Market data creation request
        service: Application service
        correlation_id: Request correlation ID

    Returns:
        Created market data record
    """
    try:
        logger.info(f"API: Creating market data for {request.symbol}", extra={'correlation_id': correlation_id})

        # Create market data entity
        market_data = await service.create_market_data_from_raw(
            symbol=request.symbol,
            timestamp=request.timestamp,
            open_price=request.open_price,
            high_price=request.high_price,
            low_price=request.low_price,
            close_price=request.close_price,
            volume=request.volume,
            exchange=request.exchange
        )

        # Update market data
        result = await service.update_market_data(request.symbol, market_data)

        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create market data: {result.error_message}"
            )

        return MarketDataResponse.from_entity(market_data)

    except Exception as e:
        logger.error(f"Error creating market data for {request.symbol}: {e}", extra={'correlation_id': correlation_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/{symbol}")
async def get_market_data_summary(
    symbol: str,
    analysis_period_days: int = Query(30, description="Analysis period in days"),
    service: MarketDataApplicationService = Depends(get_application_service),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Get market data summary and analytics

    Args:
        symbol: Trading symbol
        analysis_period_days: Period for analysis
        service: Application service
        correlation_id: Request correlation ID

    Returns:
        Market data summary and analytics
    """
    try:
        logger.info(f"API: Getting summary for {symbol}", extra={'correlation_id': correlation_id})

        result = await service.get_market_data_summary(symbol, analysis_period_days)

        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate summary for {symbol}: {result.error_message}"
            )

        return result.data

    except Exception as e:
        logger.error(f"Error getting market data summary for {symbol}: {e}", extra={'correlation_id': correlation_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def get_market_data_health(
    service: MarketDataApplicationService = Depends(get_application_service),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Get market data system health status

    Args:
        service: Application service
        correlation_id: Request correlation ID

    Returns:
        System health information
    """
    try:
        logger.info("API: Getting market data health status", extra={'correlation_id': correlation_id})

        health_data = await service.get_market_health_status()

        return {
            "service": "market_data",
            "status": health_data.get("status", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "details": health_data
        }

    except Exception as e:
        logger.error(f"Error getting market data health: {e}", extra={'correlation_id': correlation_id})
        raise HTTPException(status_code=500, detail=str(e))
