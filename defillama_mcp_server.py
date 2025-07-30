#!/usr/bin/env python3
"""
DefiLlama MCP Server - Comprehensive Edition

A Model Context Protocol server that provides complete access to DefiLlama's DeFi data APIs,
including protocols, prices, TVL, yield farming, stablecoins, DEX data, and more.

This server exposes tools for:
- Protocol analysis and comparison
- Token price tracking (current, historical, charts)
- Chain TVL analysis
- Yield farming optimization
- Stablecoin monitoring
- DEX volume and performance analysis
- Portfolio optimization
- Risk assessment

Features:
- Full parameter support for all endpoints
- Advanced filtering and sorting capabilities
- Data enrichment and normalization
- Intelligent caching
- Error handling and validation
- AI-friendly response formatting

Usage:
    python defillama_mcp_server.py

For Claude Desktop integration, add to claude_desktop_config.json:
{
    "mcpServers": {
        "defillama": {
            "command": "python",
            "args": ["/path/to/defillama_mcp_server.py"]
        }
    }
}
"""

import asyncio
import atexit
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple, cast
from urllib.parse import quote, urlencode
from functools import lru_cache
import statistics

import httpx
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the MCP server
mcp = FastMCP(
    name="DefiLlama-Comprehensive",
    dependencies=["httpx>=0.24.0"]
)

# Constants
DEFILLAMA_API_BASE = "https://api.llama.fi"
DEFILLAMA_COINS_API = "https://coins.llama.fi"
DEFILLAMA_YIELDS_API = "https://yields.llama.fi"
DEFILLAMA_STABLECOINS_API = "https://stablecoins.llama.fi"
USER_AGENT = "DefiLlama-MCP-Server/2.0"
DEFAULT_TIMEOUT = 30.0
CACHE_TTL = 300  # 5 minutes
REQUEST_DELAY = 0.1  # Rate limiting delay

# Global HTTP client and cache
http_client: Optional[httpx.AsyncClient] = None
response_cache: Dict[str, Tuple[float, Any]] = {}


async def get_http_client() -> httpx.AsyncClient:
    """Get or create the global HTTP client."""
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True
        )
    return http_client


def get_cache_key(url: str, params: Optional[Dict[str, Any]] = None) -> str:
    """Generate cache key from URL and parameters."""
    if params:
        param_str = urlencode(sorted(params.items()))
        return f"{url}?{param_str}"
    return url


async def make_api_request(url: str, params: Optional[Dict[str, Any]] = None, use_cache: bool = True) -> Dict[str, Any]:
    """
    Make a request to the DefiLlama API with caching and error handling.
    
    Args:
        url: The API endpoint URL
        params: Optional query parameters
        use_cache: Whether to use caching
        
    Returns:
        Parsed JSON response
        
    Raises:
        ValueError: If the API request fails or returns invalid data
    """
    cache_key = get_cache_key(url, params)
    
    # Check cache first
    if use_cache and cache_key in response_cache:
        timestamp, data = response_cache[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return data
    
    client = await get_http_client()
    
    try:
        # Rate limiting
        await asyncio.sleep(REQUEST_DELAY)
        
        response = await client.get(url, params=params)
        response.raise_for_status()
        
        # Handle empty responses
        if not response.content:
            raise ValueError("Empty response from API")
            
        data = response.json()
        
        # Cache the response
        if use_cache:
            response_cache[cache_key] = (time.time(), data)
            
        return data
        
    except httpx.HTTPStatusError as e:
        raise ValueError(f"API request failed with status {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        raise ValueError(f"Network error: {str(e)}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response: {str(e)}")


def format_number(value: Union[int, float], decimals: int = 2) -> str:
    """Format large numbers with appropriate suffixes."""
    if not isinstance(value, (int, float)) or value == 0:
        return "0"
    
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    
    if abs_value >= 1_000_000_000_000:
        return f"{sign}{abs_value/1_000_000_000_000:.{decimals}f}T"
    elif abs_value >= 1_000_000_000:
        return f"{sign}{abs_value/1_000_000_000:.{decimals}f}B"
    elif abs_value >= 1_000_000:
        return f"{sign}{abs_value/1_000_000:.{decimals}f}M"
    elif abs_value >= 1_000:
        return f"{sign}{abs_value/1_000:.{decimals}f}K"
    else:
        return f"{sign}{abs_value:.{decimals}f}"


def format_timestamp(timestamp: Union[int, float, str]) -> str:
    """Format timestamp to readable date."""
    try:
        if isinstance(timestamp, str):
            timestamp = float(timestamp)
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except (ValueError, TypeError):
        return str(timestamp)


def apply_filters(data: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Apply filters to data list."""
    if not filters or not data:
        return data
    
    filtered_data = data.copy()
    
    for key, value in filters.items():
        if key.startswith('min_'):
            field = key[4:]  # Remove 'min_' prefix
            filtered_data = [item for item in filtered_data 
                           if isinstance(item.get(field), (int, float)) and item.get(field, 0) >= value]
        elif key.startswith('max_'):
            field = key[4:]  # Remove 'max_' prefix
            filtered_data = [item for item in filtered_data 
                           if isinstance(item.get(field), (int, float)) and item.get(field, float('inf')) <= value]
        elif key == 'chains':
            if isinstance(value, str):
                value = [v.strip() for v in value.split(',')]
            filtered_data = [item for item in filtered_data 
                           if item.get('chain', '').lower() in [v.lower() for v in value]]
        elif key == 'protocols':
            if isinstance(value, str):
                value = [v.strip() for v in value.split(',')]
            filtered_data = [item for item in filtered_data 
                           if item.get('project', '').lower() in [v.lower() for v in value]]
        elif key == 'symbols':
            if isinstance(value, str):
                value = [v.strip() for v in value.split(',')]
            filtered_data = [item for item in filtered_data 
                           if any(symbol.lower() in item.get('symbol', '').lower() for symbol in value)]
    
    return filtered_data


def sort_data(data: List[Dict[str, Any]], sort_by: str = 'tvl', ascending: bool = False) -> List[Dict[str, Any]]:
    """Sort data by specified field."""
    if not data or not sort_by:
        return data
    
    # Map common sort keys to actual field names
    sort_mapping = {
        'tvl': 'tvlUsd',
        'apy': 'apy',
        'volume': 'volume',
        'price': 'price',
        'mcap': 'mcap',
        'change': 'change_1h',
        'name': 'name',
        'symbol': 'symbol'
    }
    
    actual_field = sort_mapping.get(sort_by, sort_by)
    
    try:
        return sorted(data, 
                     key=lambda x: x.get(actual_field, 0) if isinstance(x.get(actual_field), (int, float)) else 0,
                     reverse=not ascending)
    except Exception:
        return data


# =============================================================================
# PROTOCOL TOOLS
# =============================================================================

@mcp.tool()
async def get_protocols(
    sort_by: str = "tvl",
    ascending: bool = False,
    limit: Optional[int] = None,
    min_tvl: Optional[float] = None,
    chains: Optional[str] = None,
    categories: Optional[str] = None
) -> str:
    """
    Get list of all DeFi protocols with filtering and sorting.
    
    Args:
        sort_by: Sort field (tvl, name, change_1h, change_1d, change_7d, mcap)
        ascending: Sort order (False for descending)
        limit: Maximum number of results
        min_tvl: Minimum TVL threshold in USD
        chains: Comma-separated list of chains to filter by
        categories: Comma-separated list of categories to filter by
        
    Returns:
        Formatted string with protocol information
    """
    try:
        url = f"{DEFILLAMA_API_BASE}/protocols"
        data = await make_api_request(url)
        
        if not isinstance(data, list):
            return "❌ Invalid protocols data format received"
        
        # Apply filters
        filters = {}
        if min_tvl:
            filters['min_tvl'] = min_tvl
        if chains:
            chain_list = [c.strip() for c in chains.split(',')]
            data = [p for p in data if isinstance(p, dict) and any(c.lower() in str(p.get('chains', [])).lower() for c in chain_list)]
        if categories:
            cat_list = [c.strip().lower() for c in categories.split(',')]
            data = [p for p in data if isinstance(p, dict) and p.get('category', '').lower() in cat_list]
        
        # Ensure data is properly typed
        data = cast(List[Dict[str, Any]], [p for p in data if isinstance(p, dict)])
        data = apply_filters(data, filters)
        data = sort_data(data, sort_by, ascending)
        
        if limit:
            data = data[:limit]
        
        if not data:
            return "No protocols found matching the criteria."
        
        result_lines = [f"**DeFi Protocols ({len(data)} results)**\n"]
        
        for i, protocol in enumerate(data, 1):
            name = protocol.get('name', 'Unknown')
            tvl = protocol.get('tvl', 0)
            change_1d = protocol.get('change_1d', 0)
            change_7d = protocol.get('change_7d', 0)
            category = protocol.get('category', 'Unknown')
            chains = protocol.get('chains', [])
            
            tvl_str = f"${format_number(tvl)}"
            change_1d_str = f"{change_1d:+.2f}%" if isinstance(change_1d, (int, float)) else "N/A"
            change_7d_str = f"{change_7d:+.2f}%" if isinstance(change_7d, (int, float)) else "N/A"
            
            chains_str = ', '.join(chains[:3]) if isinstance(chains, list) and chains else 'Unknown'
            if isinstance(chains, list) and len(chains) > 3:
                chains_str += f" (+{len(chains)-3} more)"
            
            result_lines.append(
                f"{i:2d}. **{name}** | {category}\n"
                f"    💰 TVL: {tvl_str}\n"
                f"    📈 1D: {change_1d_str} | 7D: {change_7d_str}\n"
                f"    ⛓️ Chains: {chains_str}\n"
            )
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching protocols: {e}")
        return f"❌ Error fetching protocols: {str(e)}"


@mcp.tool()
async def get_protocol_details(protocol_name: str) -> str:
    """
    Get detailed information about a specific protocol.
    
    Args:
        protocol_name: Name or slug of the protocol
        
    Returns:
        Formatted string with detailed protocol information
    """
    try:
        protocol_clean = quote(protocol_name.strip().lower(), safe='')
        url = f"{DEFILLAMA_API_BASE}/protocol/{protocol_clean}"
        data = await make_api_request(url)
        
        if not isinstance(data, dict):
            return f"❌ Protocol '{protocol_name}' not found"
        
        name = data.get('name', 'Unknown')
        symbol = data.get('symbol', 'N/A')
        category = data.get('category', 'Unknown')
        tvl = data.get('tvl', 0)
        change_1h = data.get('change_1h', 0)
        change_1d = data.get('change_1d', 0)
        change_7d = data.get('change_7d', 0)
        mcap = data.get('mcap', 0)
        description = data.get('description', 'No description available')
        url_link = data.get('url', 'N/A')
        twitter = data.get('twitter', 'N/A')
        chains = data.get('chains', [])
        
        result_lines = [
            f"**{name} ({symbol})**",
            f"🏷️ Category: {category}",
            f"💰 TVL: ${format_number(tvl)}",
            f"📊 Market Cap: ${format_number(mcap)}",
            "",
            "**Price Changes:**",
            f"• 1H: {change_1h:+.2f}%" if isinstance(change_1h, (int, float)) else "• 1H: N/A",
            f"• 1D: {change_1d:+.2f}%" if isinstance(change_1d, (int, float)) else "• 1D: N/A",
            f"• 7D: {change_7d:+.2f}%" if isinstance(change_7d, (int, float)) else "• 7D: N/A",
            "",
            f"⛓️ **Chains:** {', '.join(chains) if chains else 'Unknown'}",
            "",
            f"🌐 **Website:** {url_link}",
            f"🐦 **Twitter:** {twitter}",
            "",
            f"**Description:**",
            f"{description[:500]}{'...' if len(description) > 500 else ''}",
        ]
        
        # Add chain-specific TVL if available
        if 'chainTvls' in data and data['chainTvls']:
            result_lines.extend(["", "**TVL by Chain:**"])
            for chain, chain_tvl in data['chainTvls'].items():
                if isinstance(chain_tvl, (int, float)) and chain_tvl > 0:
                    result_lines.append(f"• {chain}: ${format_number(chain_tvl)}")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching protocol details: {e}")
        return f"❌ Error fetching protocol details: {str(e)}"


@mcp.tool()
async def get_protocol_tvl(protocol_name: str) -> str:
    """
    Get TVL data for a specific protocol.
    
    Args:
        protocol_name: Name or slug of the protocol
        
    Returns:
        Formatted string with protocol TVL information
    """
    try:
        protocol_clean = quote(protocol_name.strip().lower(), safe='')
        url = f"{DEFILLAMA_API_BASE}/tvl/{protocol_clean}"
        data = await make_api_request(url)
        
        if not isinstance(data, (int, float)):
            return f"❌ TVL data not found for protocol '{protocol_name}'"
        
        tvl_str = f"${format_number(data)}"
        
        return f"**{protocol_name} TVL**\n\n💰 Current TVL: {tvl_str}"
        
    except Exception as e:
        logger.error(f"Error fetching protocol TVL: {e}")
        return f"❌ Error fetching protocol TVL: {str(e)}"


# =============================================================================
# CHAIN ANALYSIS TOOLS
# =============================================================================

@mcp.tool()
async def get_chains() -> str:
    """
    Get list of all supported chains with TVL data.
    
    Returns:
        Formatted string with chain information
    """
    try:
        url = f"{DEFILLAMA_API_BASE}/v2/chains"
        data = await make_api_request(url)
        
        if not isinstance(data, list):
            return "❌ Invalid chains data format received"
        
        # Sort by TVL descending
        chains_data = cast(List[Dict[str, Any]], [c for c in data if isinstance(c, dict)])
        chains_data = sorted(chains_data, key=lambda x: x.get('tvl', 0), reverse=True)
        
        result_lines = [f"**Blockchain Networks ({len(chains_data)} chains)**\n"]
        
        for i, chain in enumerate(chains_data, 1):
            name = chain.get('name', 'Unknown')
            tvl = chain.get('tvl', 0)
            protocols = chain.get('protocols', 0)
            change_1d = chain.get('change_1d', 0)
            change_7d = chain.get('change_7d', 0)
            
            tvl_str = f"${format_number(tvl)}"
            change_1d_str = f"{change_1d:+.2f}%" if isinstance(change_1d, (int, float)) else "N/A"
            change_7d_str = f"{change_7d:+.2f}%" if isinstance(change_7d, (int, float)) else "N/A"
            
            result_lines.append(
                f"{i:2d}. **{name}**\n"
                f"    💰 TVL: {tvl_str} | 🏗️ Protocols: {protocols}\n"
                f"    📈 1D: {change_1d_str} | 7D: {change_7d_str}\n"
            )
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching chains: {e}")
        return f"❌ Error fetching chains: {str(e)}"


@mcp.tool()
async def get_chain_tvl_history(chain_name: str) -> str:
    """
    Get historical TVL data for a specific chain.
    
    Args:
        chain_name: Name of the blockchain
        
    Returns:
        Formatted string with chain TVL history
    """
    try:
        chain_clean = quote(chain_name.strip(), safe='')
        url = f"{DEFILLAMA_API_BASE}/v2/historicalChainTvl/{chain_clean}"
        data = await make_api_request(url)
        
        if not isinstance(data, list):
            return f"❌ Historical TVL data not found for chain '{chain_name}'"
        
        if not data:
            return f"❌ No historical data available for chain '{chain_name}'"
        
        # Type cast and get recent data points (last 30 days)
        tvl_data = cast(List[Dict[str, Any]], data)
        recent_data = tvl_data[-30:] if len(tvl_data) > 30 else tvl_data
        
        result_lines = [
            f"**{chain_name} TVL History**",
            f"📊 Total Data Points: {len(data)}",
            f"📈 Showing Recent 30 Days:",
            ""
        ]
        
        for point in recent_data:
            date = point.get('date')
            tvl = point.get('tvl', 0)
            
            if date:
                try:
                    # Convert date string to readable format
                    dt = datetime.fromtimestamp(int(date), tz=timezone.utc)
                    date_str = dt.strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    date_str = str(date)
            else:
                date_str = "Unknown"
            
            tvl_str = f"${format_number(tvl)}"
            result_lines.append(f"• {date_str}: {tvl_str}")
        
        # Calculate growth if we have enough data
        if len(tvl_data) >= 7:
            current_tvl = tvl_data[-1].get('tvl', 0) if isinstance(tvl_data[-1], dict) else 0
            week_ago_tvl = tvl_data[-7].get('tvl', 0) if isinstance(tvl_data[-7], dict) else 0
            if week_ago_tvl > 0:
                growth = ((current_tvl - week_ago_tvl) / week_ago_tvl) * 100
                result_lines.insert(3, f"📊 7-Day Growth: {growth:+.2f}%")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching chain TVL history: {e}")
        return f"❌ Error fetching chain TVL history: {str(e)}"


@mcp.tool()
async def get_all_chains_tvl() -> str:
    """
    Get historical TVL data for all chains combined.
    
    Returns:
        Formatted string with total TVL history
    """
    try:
        url = f"{DEFILLAMA_API_BASE}/v2/historicalChainTvl"
        data = await make_api_request(url)
        
        if not isinstance(data, list):
            return "❌ Invalid historical TVL data format received"
        
        if not data:
            return "❌ No historical TVL data available"
        
        # Type cast and get recent data points (last 30 days)
        all_tvl_data = cast(List[Dict[str, Any]], data)
        recent_data = all_tvl_data[-30:] if len(all_tvl_data) > 30 else all_tvl_data
        
        result_lines = [
            f"**Total DeFi TVL History**",
            f"📊 Total Data Points: {len(data)}",
            f"📈 Showing Recent 30 Days:",
            ""
        ]
        
        for point in recent_data:
            date = point.get('date')
            tvl = point.get('tvl', 0)
            
            if date:
                try:
                    dt = datetime.fromtimestamp(int(date), tz=timezone.utc)
                    date_str = dt.strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    date_str = str(date)
            else:
                date_str = "Unknown"
            
            tvl_str = f"${format_number(tvl)}"
            result_lines.append(f"• {date_str}: {tvl_str}")
        
        # Calculate growth metrics
        if len(all_tvl_data) >= 30:
            current_tvl = all_tvl_data[-1].get('tvl', 0) if isinstance(all_tvl_data[-1], dict) else 0
            week_ago_tvl = all_tvl_data[-7].get('tvl', 0) if isinstance(all_tvl_data[-7], dict) else 0
            month_ago_tvl = all_tvl_data[-30].get('tvl', 0) if isinstance(all_tvl_data[-30], dict) else 0
            
            growth_metrics = []
            if week_ago_tvl > 0:
                growth_7d = ((current_tvl - week_ago_tvl) / week_ago_tvl) * 100
                growth_metrics.append(f"7D: {growth_7d:+.2f}%")
            if month_ago_tvl > 0:
                growth_30d = ((current_tvl - month_ago_tvl) / month_ago_tvl) * 100
                growth_metrics.append(f"30D: {growth_30d:+.2f}%")
            
            if growth_metrics:
                result_lines.insert(3, f"📊 Growth: {' | '.join(growth_metrics)}")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching all chains TVL: {e}")
        return f"❌ Error fetching all chains TVL: {str(e)}"


# =============================================================================
# PRICE TOOLS
# =============================================================================

@mcp.tool()
async def get_current_prices(
    coins: str,
    search_width: Optional[str] = None
) -> str:
    """
    Get current prices for specified tokens.
    
    Args:
        coins: Comma-separated list of coin identifiers. Can be:
               - Contract addresses (e.g., ethereum:0xA0b86a33E6)
               - Coin gecko IDs (e.g., coingecko:bitcoin)
               - Symbols (e.g., WETH, USDC)
        search_width: Search width for price data (optional)
        
    Returns:
        Formatted string with current price information
    """
    try:
        coins_clean = quote(coins.strip(), safe=',:-')
        url = f"{DEFILLAMA_COINS_API}/prices/current/{coins_clean}"
        
        params = {}
        if search_width:
            params["searchWidth"] = search_width
        
        logger.info(f"Fetching current prices for: {coins}")
        data = await make_api_request(url, params)
        
        if not data or "coins" not in data:
            return "No price data available"
        
        result_lines = ["**Current Token Prices**\n"]
        
        for coin_id, coin_data in data["coins"].items():
            if not isinstance(coin_data, dict):
                continue
                
            symbol = coin_data.get("symbol", "Unknown")
            price = coin_data.get("price", "N/A")
            decimals = coin_data.get("decimals", "N/A")
            timestamp = coin_data.get("timestamp")
            confidence = coin_data.get("confidence", "N/A")
            
            formatted_price = f"${price:,.6f}" if isinstance(price, (int, float)) else str(price)
            
            timestamp_str = ""
            if timestamp:
                timestamp_str = f" ({format_timestamp(timestamp)})"
            
            result_lines.append(f"**{symbol}** | {coin_id}")
            result_lines.append(f"💰 Price: {formatted_price}{timestamp_str}")
            if decimals != "N/A":
                result_lines.append(f"🔢 Decimals: {decimals}")
            if confidence != "N/A":
                result_lines.append(f"📊 Confidence: {confidence}")
            result_lines.append("")
        
        return "\n".join(result_lines) if len(result_lines) > 1 else "No valid price data found"
        
    except Exception as e:
        logger.error(f"Error fetching current prices: {e}")
        return f"❌ Error fetching current prices: {str(e)}"


@mcp.tool()
async def get_historical_prices(
    timestamp: Union[int, str],
    coins: str,
    search_width: Optional[str] = None
) -> str:
    """
    Get historical prices for tokens at a specific timestamp.
    
    Args:
        timestamp: Unix timestamp or date string (YYYY-MM-DD)
        coins: Comma-separated list of coin identifiers
        search_width: Search width for price data (optional)
        
    Returns:
        Formatted string with historical price information
    """
    try:
        # Convert date string to timestamp if needed
        if isinstance(timestamp, str):
            try:
                if "-" in timestamp:  # Assume YYYY-MM-DD format
                    dt = datetime.strptime(timestamp, "%Y-%m-%d")
                    timestamp = int(dt.replace(tzinfo=timezone.utc).timestamp())
                else:
                    timestamp = int(timestamp)
            except ValueError:
                return "❌ Invalid timestamp format. Use Unix timestamp or YYYY-MM-DD format."
        
        coins_clean = quote(str(coins).strip(), safe=',:-')
        url = f"{DEFILLAMA_COINS_API}/prices/historical/{timestamp}/{coins_clean}"
        
        params = {}
        if search_width:
            params["searchWidth"] = search_width
        
        logger.info(f"Fetching historical prices for: {coins} at timestamp: {timestamp}")
        data = await make_api_request(url, params)
        
        if not data or "coins" not in data:
            return "No historical price data available"
        
        date_str = format_timestamp(timestamp)
        result_lines = [f"**Historical Token Prices ({date_str})**\n"]
        
        for coin_id, coin_data in data["coins"].items():
            if not isinstance(coin_data, dict):
                continue
                
            symbol = coin_data.get("symbol", "Unknown")
            price = coin_data.get("price", "N/A")
            decimals = coin_data.get("decimals", "N/A")
            confidence = coin_data.get("confidence", "N/A")
            
            formatted_price = f"${price:,.6f}" if isinstance(price, (int, float)) else str(price)
            
            result_lines.append(f"**{symbol}** | {coin_id}")
            result_lines.append(f"💰 Price: {formatted_price}")
            if decimals != "N/A":
                result_lines.append(f"🔢 Decimals: {decimals}")
            if confidence != "N/A":
                result_lines.append(f"📊 Confidence: {confidence}")
            result_lines.append("")
        
        return "\n".join(result_lines) if len(result_lines) > 1 else "No valid historical price data found"
        
    except Exception as e:
        logger.error(f"Error fetching historical prices: {e}")
        return f"❌ Error fetching historical prices: {str(e)}"


@mcp.tool()
async def get_batch_historical_prices(
    coins: str,
    search_width: Optional[str] = None,
    period: str = "1d"
) -> str:
    """
    Get batch historical price data for multiple tokens.
    
    Args:
        coins: Comma-separated list of coin identifiers
        search_width: Search width for price data (optional)
        period: Time period for data (1d, 7d, 30d)
        
    Returns:
        Formatted string with batch historical price information
    """
    try:
        url = f"{DEFILLAMA_COINS_API}/batchHistorical"
        
        params = {
            "coins": coins.strip(),
            "period": period
        }
        if search_width:
            params["searchWidth"] = search_width
        
        logger.info(f"Fetching batch historical prices for: {coins}")
        data = await make_api_request(url, params)
        
        if not data or "coins" not in data:
            return "No batch historical price data available"
        
        result_lines = [f"**Batch Historical Prices ({period} period)**\n"]
        
        for coin_id, coin_data in data["coins"].items():
            if not isinstance(coin_data, dict):
                continue
                
            symbol = coin_data.get("symbol", "Unknown")
            prices = coin_data.get("prices", [])
            
            if not prices:
                continue
                
            result_lines.append(f"**{symbol}** | {coin_id}")
            result_lines.append(f"📊 Price History ({len(prices)} points):")
            
            # Show last few data points
            recent_prices = prices[-5:] if len(prices) > 5 else prices
            for price_point in recent_prices:
                if not isinstance(price_point, dict):
                    continue
                timestamp = price_point.get("timestamp")
                price = price_point.get("price")
                confidence = price_point.get("confidence", "N/A")
                
                if timestamp and price:
                    date_str = format_timestamp(timestamp)
                    price_str = f"${price:,.6f}" if isinstance(price, (int, float)) else str(price)
                    result_lines.append(f"  • {date_str}: {price_str} (confidence: {confidence})")
            result_lines.append("")
        
        return "\n".join(result_lines) if len(result_lines) > 1 else "No valid batch historical price data found"
        
    except Exception as e:
        logger.error(f"Error fetching batch historical prices: {e}")
        return f"❌ Error fetching batch historical prices: {str(e)}"


@mcp.tool()
async def get_price_chart(
    coins: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    span: Optional[int] = None,
    period: str = "1d",
    search_width: Optional[str] = None
) -> str:
    """
    Get price chart data for tokens.
    
    Args:
        coins: Comma-separated list of coin identifiers
        start: Start timestamp (Unix) or date (YYYY-MM-DD)
        end: End timestamp (Unix) or date (YYYY-MM-DD)
        span: Number of data points to return
        period: Time period between data points (1h, 1d, 1w)
        search_width: Search width for price data (optional)
        
    Returns:
        Formatted string with price chart data
    """
    try:
        coins_clean = quote(coins.strip(), safe=',:-')
        url = f"{DEFILLAMA_COINS_API}/chart/{coins_clean}"
        
        params = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if span:
            params["span"] = span
        if period:
            params["period"] = period
        if search_width:
            params["searchWidth"] = search_width
        
        logger.info(f"Fetching price chart for: {coins}")
        data = await make_api_request(url, params)
        
        if not data or "coins" not in data:
            return "No price chart data available"
        
        result_lines = [f"**Price Chart Data ({period} intervals)**\n"]
        
        for coin_id, coin_data in data["coins"].items():
            if not isinstance(coin_data, dict):
                continue
                
            symbol = coin_data.get("symbol", "Unknown")
            decimals = coin_data.get("decimals", "N/A")
            confidence = coin_data.get("confidence", "N/A")
            prices = coin_data.get("prices", [])
            
            if not prices:
                continue
                
            result_lines.append(f"**{symbol}** | {coin_id}")
            result_lines.append(f"🔢 Decimals: {decimals} | 📊 Confidence: {confidence}")
            result_lines.append(f"📈 Price Data ({len(prices)} points):")
            
            # Calculate price statistics
            price_values = [p.get("price", 0) for p in prices if isinstance(p.get("price"), (int, float))]
            if price_values:
                min_price = min(price_values)
                max_price = max(price_values)
                avg_price = statistics.mean(price_values)
                result_lines.append(f"  📊 Min: ${min_price:,.6f} | Max: ${max_price:,.6f} | Avg: ${avg_price:,.6f}")
            
            # Show recent data points
            recent_prices = prices[-10:] if isinstance(prices, list) and len(prices) > 10 else prices
            for price_point in recent_prices:
                if not isinstance(price_point, dict):
                    continue
                timestamp = price_point.get("timestamp")
                price = price_point.get("price")
                
                if timestamp and price:
                    date_str = format_timestamp(timestamp)
                    price_str = f"${price:,.6f}" if isinstance(price, (int, float)) else str(price)
                    result_lines.append(f"  • {date_str}: {price_str}")
            result_lines.append("")
        
        return "\n".join(result_lines) if len(result_lines) > 1 else "No valid price chart data found"
        
    except Exception as e:
        logger.error(f"Error fetching price chart: {e}")
        return f"❌ Error fetching price chart: {str(e)}"


@mcp.tool()
async def get_price_percentage_changes(
    coins: str,
    timestamp: Optional[str] = None,
    lookforward: bool = False,
    period: str = "1d"
) -> str:
    """
    Get percentage price changes for tokens.
    
    Args:
        coins: Comma-separated list of coin identifiers
        timestamp: Reference timestamp (Unix) or date (YYYY-MM-DD)
        lookforward: Whether to look forward from timestamp
        period: Time period for percentage calculation (1h, 1d, 7d, 30d)
        
    Returns:
        Formatted string with percentage changes
    """
    try:
        coins_clean = quote(coins.strip(), safe=',:-')
        url = f"{DEFILLAMA_COINS_API}/percentage/{coins_clean}"
        
        params = {}
        if timestamp:
            params["timestamp"] = timestamp
        if lookforward:
            params["lookforward"] = "true"
        if period:
            params["period"] = period
        
        logger.info(f"Fetching price percentage changes for: {coins}")
        data = await make_api_request(url, params)
        
        if not data or "coins" not in data:
            return "No percentage change data available"
        
        result_lines = [f"**Price Percentage Changes ({period} period)**\n"]
        
        for coin_id, percentage in data["coins"].items():
            if isinstance(percentage, (int, float)):
                change_str = f"{percentage:+.2f}%"
                emoji = "📈" if percentage > 0 else "📉" if percentage < 0 else "➡️"
                result_lines.append(f"{emoji} **{coin_id}**: {change_str}")
        
        return "\n".join(result_lines) if len(result_lines) > 1 else "No valid percentage change data found"
        
    except Exception as e:
        logger.error(f"Error fetching price percentage changes: {e}")
        return f"❌ Error fetching price percentage changes: {str(e)}"


@mcp.tool()
async def get_first_prices(coins: str) -> str:
    """
    Get first recorded prices for tokens.
    
    Args:
        coins: Comma-separated list of coin identifiers
        
    Returns:
        Formatted string with first price information
    """
    try:
        coins_clean = quote(coins.strip(), safe=',:-')
        url = f"{DEFILLAMA_COINS_API}/prices/first/{coins_clean}"
        
        logger.info(f"Fetching first prices for: {coins}")
        data = await make_api_request(url)
        
        if not data or "coins" not in data:
            return "No first price data available"
        
        result_lines = ["**First Recorded Prices**\n"]
        
        for coin_id, coin_data in data["coins"].items():
            if not isinstance(coin_data, dict):
                continue
                
            symbol = coin_data.get("symbol", "Unknown")
            price = coin_data.get("price", "N/A")
            timestamp = coin_data.get("timestamp")
            
            formatted_price = f"${price:,.6f}" if isinstance(price, (int, float)) else str(price)
            timestamp_str = format_timestamp(timestamp) if timestamp else "Unknown"
            
            result_lines.append(f"**{symbol}** | {coin_id}")
            result_lines.append(f"💰 First Price: {formatted_price}")
            result_lines.append(f"📅 Date: {timestamp_str}")
            result_lines.append("")
        
        return "\n".join(result_lines) if len(result_lines) > 1 else "No valid first price data found"
        
    except Exception as e:
        logger.error(f"Error fetching first prices: {e}")
        return f"❌ Error fetching first prices: {str(e)}"


@mcp.tool()
async def get_block_info(chain: str, timestamp: Union[int, str]) -> str:
    """
    Get block information for a specific chain and timestamp.
    
    Args:
        chain: Blockchain name
        timestamp: Unix timestamp or date (YYYY-MM-DD)
        
    Returns:
        Formatted string with block information
    """
    try:
        if isinstance(timestamp, str) and "-" in timestamp:
            dt = datetime.strptime(timestamp, "%Y-%m-%d")
            timestamp = int(dt.replace(tzinfo=timezone.utc).timestamp())
        
        chain_clean = quote(str(chain).strip(), safe='')
        url = f"{DEFILLAMA_COINS_API}/block/{chain_clean}/{timestamp}"
        
        logger.info(f"Fetching block info for {chain} at timestamp: {timestamp}")
        data = await make_api_request(url)
        
        if not isinstance(data, dict):
            return f"❌ Block information not found for {chain} at timestamp {timestamp}"
        
        height = data.get("height", "Unknown")
        block_timestamp = data.get("timestamp", timestamp)
        
        result_lines = [
            f"**Block Information - {chain}**",
            f"⛓️ Chain: {chain}",
            f"🔢 Block Height: {height}",
            f"📅 Timestamp: {format_timestamp(block_timestamp)}",
            f"🕐 Unix Timestamp: {block_timestamp}"
        ]
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching block info: {e}")
        return f"❌ Error fetching block info: {str(e)}"


# =============================================================================
# YIELD FARMING TOOLS
# =============================================================================

@mcp.tool()
async def get_yield_pools(
    sort_by: str = "tvl",
    ascending: bool = False,
    limit: Optional[int] = 50,
    min_tvl: Optional[float] = None,
    min_apy: Optional[float] = None,
    max_apy: Optional[float] = None,
    chains: Optional[str] = None,
    protocols: Optional[str] = None,
    symbols: Optional[str] = None,
    exclude_farm: bool = False
) -> str:
    """
    Get yield farming pools with comprehensive filtering and sorting.
    
    Args:
        sort_by: Sort field (tvl, apy, volume, il7d, apyBase, apyReward)
        ascending: Sort order (False for descending)
        limit: Maximum number of results
        min_tvl: Minimum TVL threshold in USD
        min_apy: Minimum APY threshold
        max_apy: Maximum APY threshold
        chains: Comma-separated list of chains to filter by
        protocols: Comma-separated list of protocols to filter by
        symbols: Comma-separated list of symbols to filter by
        exclude_farm: Exclude farming pools
        
    Returns:
        Formatted string with yield pool information
    """
    try:
        url = f"{DEFILLAMA_YIELDS_API}/pools"
        
        logger.info("Fetching yield pools data")
        data = await make_api_request(url)
        
        # Handle different response formats
        if isinstance(data, dict) and "data" in data:
            pools = data["data"]
        elif isinstance(data, list):
            pools = data
        else:
            return "❌ Invalid pools data format received"
        
        if not isinstance(pools, list):
            return "❌ Expected list of pools but got different format"
        
        # Apply filters
        filters = {}
        if min_tvl:
            filters['min_tvlUsd'] = min_tvl
        if min_apy:
            filters['min_apy'] = min_apy
        if max_apy:
            filters['max_apy'] = max_apy
        if chains:
            filters['chains'] = chains
        if protocols:
            filters['protocols'] = protocols
        if symbols:
            filters['symbols'] = symbols
        
        filtered_pools = apply_filters(pools, filters)
        
        # Exclude farming pools if requested
        if exclude_farm:
            filtered_pools = [p for p in filtered_pools if not p.get('farmProject')]
        
        # Sort pools
        sorted_pools = sort_data(filtered_pools, sort_by, ascending)
        
        if limit:
            sorted_pools = sorted_pools[:limit]
        
        if not sorted_pools:
            return "No yield pools found matching the criteria."
        
        result_lines = [f"**Yield Farming Pools ({len(sorted_pools)} results)**\n"]
        
        for i, pool in enumerate(sorted_pools, 1):
            pool_id = pool.get("pool", "Unknown")
            project = pool.get("project", "Unknown")
            symbol = pool.get("symbol", "Unknown")
            apy = pool.get("apy", 0)
            apy_base = pool.get("apyBase", 0)
            apy_reward = pool.get("apyReward", 0)
            tvl = pool.get("tvlUsd", 0)
            chain = pool.get("chain", "Unknown")
            il7d = pool.get("il7d", 0)
            count = pool.get("count", 0)
            
            tvl_str = f"${format_number(tvl)}"
            apy_str = f"{apy:.2f}%" if isinstance(apy, (int, float)) else "N/A"
            apy_base_str = f"{apy_base:.2f}%" if isinstance(apy_base, (int, float)) else "N/A"
            apy_reward_str = f"{apy_reward:.2f}%" if isinstance(apy_reward, (int, float)) else "N/A"
            il7d_str = f"{il7d:.2f}%" if isinstance(il7d, (int, float)) else "N/A"
            
            result_lines.append(
                f"{i:2d}. **{project}** - {symbol}\n"
                f"    📈 Total APY: {apy_str} (Base: {apy_base_str} + Reward: {apy_reward_str})\n"
                f"    💰 TVL: {tvl_str} | ⛓️ {chain}\n"
                f"    📉 IL 7D: {il7d_str} | 👥 Count: {count}\n"
                f"    🆔 Pool ID: `{pool_id}`\n"
            )
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching yield pools: {e}")
        return f"❌ Error fetching yield pools: {str(e)}"


@mcp.tool()
async def get_pool_chart(pool_id: str) -> str:
    """
    Get historical data for a specific yield pool.
    
    Args:
        pool_id: The unique identifier for the pool
        
    Returns:
        Formatted string with pool historical data
    """
    try:
        pool_id_clean = quote(pool_id.strip(), safe='-')
        url = f"{DEFILLAMA_YIELDS_API}/chart/{pool_id_clean}"
        
        logger.info(f"Fetching pool chart for: {pool_id}")
        data = await make_api_request(url)
        
        if not isinstance(data, dict) or "data" not in data:
            return "❌ Invalid pool chart data format received"
        
        pool_data = data["data"]
        if not pool_data:
            return f"❌ No historical data found for pool: {pool_id}"
        
        status = data.get("status", "unknown")
        
        result_lines = [
            f"**Pool Historical Data**",
            f"🆔 Pool ID: `{pool_id}`",
            f"📊 Status: {status}",
            f"📈 Data Points: {len(pool_data)}",
            ""
        ]
        
        if len(pool_data) > 0:
            # Calculate statistics
            apy_values = [p.get("apy", 0) for p in pool_data if isinstance(p.get("apy"), (int, float))]
            tvl_values = [p.get("tvlUsd", 0) for p in pool_data if isinstance(p.get("tvlUsd"), (int, float))]
            
            if apy_values:
                avg_apy = statistics.mean(apy_values)
                min_apy = min(apy_values)
                max_apy = max(apy_values)
                result_lines.extend([
                    f"📊 APY Stats: Avg {avg_apy:.2f}% | Min {min_apy:.2f}% | Max {max_apy:.2f}%"
                ])
            
            if tvl_values:
                avg_tvl = statistics.mean(tvl_values)
                min_tvl = min(tvl_values)
                max_tvl = max(tvl_values)
                result_lines.extend([
                    f"💰 TVL Stats: Avg ${format_number(avg_tvl)} | Min ${format_number(min_tvl)} | Max ${format_number(max_tvl)}",
                    ""
                ])
            
            # Show recent data points
            result_lines.append("**Recent Performance (Last 10 points):**")
            # Show recent data points (last 10)
            pool_history = cast(List[Dict[str, Any]], pool_data)
            recent_data = pool_history[-10:] if len(pool_history) > 10 else pool_history
            
            for point in recent_data:
                if not isinstance(point, dict):
                    continue
                timestamp = point.get("timestamp")
                apy = point.get("apy")
                tvl = point.get("tvlUsd")
                
                date_str = format_timestamp(timestamp) if timestamp else "Unknown"
                apy_str = f"{apy:.2f}%" if isinstance(apy, (int, float)) else "N/A"
                tvl_str = f"${format_number(tvl)}" if isinstance(tvl, (int, float)) else "N/A"
                
                result_lines.append(f"• {date_str}: APY {apy_str}, TVL {tvl_str}")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching pool chart: {e}")
        return f"❌ Error fetching pool chart: {str(e)}"


# =============================================================================
# STABLECOIN TOOLS
# =============================================================================

@mcp.tool()
async def get_stablecoins(
    sort_by: str = "mcap",
    ascending: bool = False,
    limit: Optional[int] = 50,
    include_prices: bool = True
) -> str:
    """
    Get stablecoin market data.
    
    Args:
        sort_by: Sort field (mcap, name, symbol)
        ascending: Sort order (False for descending)
        limit: Maximum number of results
        include_prices: Include current prices
        
    Returns:
        Formatted string with stablecoin information
    """
    try:
        url = f"{DEFILLAMA_STABLECOINS_API}/stablecoins"
        
        params = {}
        if include_prices:
            params["includePrices"] = "true"
        
        logger.info("Fetching stablecoins data")
        data = await make_api_request(url, params)
        
        if not isinstance(data, dict) or "peggedAssets" not in data:
            return "❌ Invalid stablecoins data format received"
        
        stablecoins = data["peggedAssets"]
        if not isinstance(stablecoins, list):
            return "❌ Expected list of stablecoins but got different format"
        
        # Sort stablecoins
        sorted_stablecoins = sort_data(stablecoins, sort_by, ascending)
        
        if limit:
            sorted_stablecoins = sorted_stablecoins[:limit]
        
        if not sorted_stablecoins:
            return "No stablecoins found."
        
        result_lines = [f"**Stablecoins ({len(sorted_stablecoins)} results)**\n"]
        
        for i, stablecoin in enumerate(sorted_stablecoins, 1):
            name = stablecoin.get("name", "Unknown")
            symbol = stablecoin.get("symbol", "Unknown")
            mcap = stablecoin.get("circulating", {}).get("peggedUSD", 0)
            price = stablecoin.get("price", 1.0)
            pegged_type = stablecoin.get("pegType", "Unknown")

            
            mcap_str = f"${format_number(mcap)}"
            price_str = f"${price:.4f}" if isinstance(price, (int, float)) else "N/A"
            
            # Get top chains by circulation  
            chains_data = stablecoin.get("chainCirculating", {})
            if isinstance(chains_data, dict):
                chain_items = sorted(chains_data.items(), key=lambda x: x[1].get("current", {}).get("peggedUSD", 0) if isinstance(x[1], dict) else 0, reverse=True)
                top_chains = [chain for chain, _ in chain_items[:3]]
                chains_str = ', '.join(top_chains) if top_chains else 'Unknown'
            else:
                chains_str = 'Unknown'
            
            peg_emoji = "🎯" if abs(price - 1.0) < 0.01 else "⚠️" if abs(price - 1.0) < 0.05 else "🚨"
            
            result_lines.append(
                f"{i:2d}. **{name} ({symbol})**\n"
                f"    {peg_emoji} Price: {price_str} | 💰 Market Cap: {mcap_str}\n"
                f"    🏷️ Type: {pegged_type}\n"
                f"    ⛓️ Top Chains: {chains_str}\n"
            )
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching stablecoins: {e}")
        return f"❌ Error fetching stablecoins: {str(e)}"


@mcp.tool()
async def get_stablecoin_charts(
    stablecoin: Optional[str] = None,
    chain: Optional[str] = None,
    include_prices: bool = True
) -> str:
    """
    Get stablecoin circulation charts.
    
    Args:
        stablecoin: Specific stablecoin ID (optional, gets all if not specified)
        chain: Specific chain (optional, gets all chains if not specified)
        include_prices: Include current prices
        
    Returns:
        Formatted string with stablecoin chart data
    """
    try:
        if stablecoin:
            stablecoin_clean = quote(str(stablecoin).strip(), safe='')
            url = f"{DEFILLAMA_STABLECOINS_API}/stablecoin/{stablecoin_clean}"
        elif chain:
            chain_clean = quote(str(chain).strip(), safe='')
            url = f"{DEFILLAMA_STABLECOINS_API}/stablecoincharts/{chain_clean}"
        else:
            url = f"{DEFILLAMA_STABLECOINS_API}/stablecoincharts/all"
        
        params = {}
        if include_prices:
            params["includePrices"] = "true"
        
        logger.info(f"Fetching stablecoin charts")
        data = await make_api_request(url, params)
        
        if not isinstance(data, list):
            return "❌ Invalid stablecoin chart data format received"
        
        if not data:
            return "❌ No stablecoin chart data available"
        
        title = "All Stablecoins"
        if stablecoin:
            title = f"Stablecoin: {stablecoin}"
        elif chain:
            title = f"Chain: {chain}"
        
        result_lines = [
            f"**{title} Chart Data**",
            f"📊 Data Points: {len(data)}",
            ""
        ]
        
        # Show recent data points (last 10)
        chart_data = cast(List[Dict[str, Any]], data)
        recent_data = chart_data[-10:] if len(chart_data) > 10 else chart_data
        result_lines.append("**Recent Circulation Data:**")
        
        for point in recent_data:
            if not isinstance(point, dict):
                continue
            date = point.get("date")
            total_circulating = point.get("totalCirculating", {}).get("peggedUSD", 0)
            
            if date:
                try:
                    dt = datetime.fromtimestamp(int(date), tz=timezone.utc)
                    date_str = dt.strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    date_str = str(date)
            else:
                date_str = "Unknown"
            
            circulating_str = f"${format_number(total_circulating)}"
            result_lines.append(f"• {date_str}: {circulating_str}")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching stablecoin charts: {e}")
        return f"❌ Error fetching stablecoin charts: {str(e)}"


@mcp.tool()
async def get_stablecoin_chains() -> str:
    """
    Get list of chains with stablecoin activity.
    
    Returns:
        Formatted string with supported stablecoin chains
    """
    try:
        url = f"{DEFILLAMA_STABLECOINS_API}/stablecoinchains"
        
        logger.info("Fetching stablecoin chains")
        data = await make_api_request(url)
        
        if not isinstance(data, list):
            return "❌ Invalid stablecoin chains data format received"
        
        result_lines = [f"**Stablecoin Supported Chains ({len(data)} chains)**\n"]
        
        for i, chain in enumerate(data, 1):
            result_lines.append(f"{i:2d}. {chain}")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching stablecoin chains: {e}")
        return f"❌ Error fetching stablecoin chains: {str(e)}"


@mcp.tool()
async def get_stablecoin_prices() -> str:
    """
    Get current prices for all stablecoins.
    
    Returns:
        Formatted string with stablecoin prices
    """
    try:
        url = f"{DEFILLAMA_STABLECOINS_API}/stablecoinprices"
        
        logger.info("Fetching stablecoin prices")
        data = await make_api_request(url)
        
        if not isinstance(data, list):
            return "❌ Invalid stablecoin prices data format received"
        
        result_lines = [f"**Stablecoin Current Prices ({len(data)} stablecoins)**\n"]
        
        for i, stablecoin in enumerate(data, 1):
            if not isinstance(stablecoin, dict):
                continue
            name = stablecoin.get("name", "Unknown")
            symbol = stablecoin.get("symbol", "Unknown")
            price = stablecoin.get("price", 1.0)
            
            price_str = f"${price:.4f}" if isinstance(price, (int, float)) else "N/A"
            peg_emoji = "🎯" if abs(price - 1.0) < 0.01 else "⚠️" if abs(price - 1.0) < 0.05 else "🚨"
            deviation = ((price - 1.0) * 100) if isinstance(price, (int, float)) else 0
            deviation_str = f"({deviation:+.2f}%)" if deviation != 0 else ""
            
            result_lines.append(f"{i:2d}. {peg_emoji} **{name} ({symbol})**: {price_str} {deviation_str}")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching stablecoin prices: {e}")
        return f"❌ Error fetching stablecoin prices: {str(e)}"


# =============================================================================
# DEX TOOLS
# =============================================================================

@mcp.tool()
async def get_dex_overview(
    exclude_total_data_chart: Optional[str] = None,
    exclude_total_data_chart_breakdown: Optional[str] = None,
    data_type: str = "dailyVolume"
) -> str:
    """
    Get DEX volume overview across all chains.
    
    Args:
        exclude_total_data_chart: Comma-separated list of chains to exclude from chart
        exclude_total_data_chart_breakdown: Comma-separated list of chains to exclude from breakdown
        data_type: Type of data (dailyVolume, totalVolume)
        
    Returns:
        Formatted string with DEX overview data
    """
    try:
        url = f"{DEFILLAMA_API_BASE}/overview/dexs"
        
        params = {"dataType": data_type}
        if exclude_total_data_chart:
            params["excludeTotalDataChart"] = exclude_total_data_chart
        if exclude_total_data_chart_breakdown:
            params["excludeTotalDataChartBreakdown"] = exclude_total_data_chart_breakdown
        
        logger.info("Fetching DEX overview")
        data = await make_api_request(url, params)
        
        if not isinstance(data, dict):
            return "❌ Invalid DEX overview data format received"
        
        total_data_chart = data.get("totalDataChart", [])
        protocols = data.get("protocols", [])
        chains = data.get("chains", [])
        
        result_lines = [
            f"**DEX Overview ({data_type})**",
            f"📊 Protocols: {len(protocols)} | ⛓️ Chains: {len(chains)}",
            ""
        ]
        
        # Show top protocols by volume
        if protocols:
            sorted_protocols = sorted(protocols, key=lambda x: x.get(data_type, 0), reverse=True)[:10]
            result_lines.append("**Top 10 DEX Protocols:**")
            for i, protocol in enumerate(sorted_protocols, 1):
                name = protocol.get("name", "Unknown")
                volume = protocol.get(data_type, 0)
                change = protocol.get("change_1d", 0)
                
                volume_str = f"${format_number(volume)}"
                change_str = f"{change:+.2f}%" if isinstance(change, (int, float)) else "N/A"
                
                result_lines.append(f"{i:2d}. **{name}**: {volume_str} ({change_str})")
            result_lines.append("")
        
        # Show top chains by volume
        if chains:
            sorted_chains = sorted(chains, key=lambda x: x.get(data_type, 0), reverse=True)[:10]
            result_lines.append("**Top 10 Chains:**")
            for i, chain in enumerate(sorted_chains, 1):
                name = chain.get("name", "Unknown")
                volume = chain.get(data_type, 0)
                change = chain.get("change_1d", 0)
                
                volume_str = f"${format_number(volume)}"
                change_str = f"{change:+.2f}%" if isinstance(change, (int, float)) else "N/A"
                
                result_lines.append(f"{i:2d}. **{name}**: {volume_str} ({change_str})")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching DEX overview: {e}")
        return f"❌ Error fetching DEX overview: {str(e)}"


@mcp.tool()
async def get_dex_chain_overview(
    chain: str,
    exclude_total_data_chart: Optional[str] = None,
    data_type: str = "dailyVolume"
) -> str:
    """
    Get DEX volume overview for a specific chain.
    
    Args:
        chain: Chain name
        exclude_total_data_chart: Comma-separated list of protocols to exclude
        data_type: Type of data (dailyVolume, totalVolume)
        
    Returns:
        Formatted string with chain DEX data
    """
    try:
        chain_clean = quote(str(chain).strip(), safe='')
        url = f"{DEFILLAMA_API_BASE}/overview/dexs/{chain_clean}"
        
        params = {"dataType": data_type}
        if exclude_total_data_chart:
            params["excludeTotalDataChart"] = exclude_total_data_chart
        
        logger.info(f"Fetching DEX overview for chain: {chain}")
        data = await make_api_request(url, params)
        
        if not isinstance(data, dict):
            return f"❌ Invalid DEX data format received for chain: {chain}"
        
        protocols = data.get("protocols", [])
        total_data_chart = data.get("totalDataChart", [])
        
        result_lines = [
            f"**DEX Overview - {chain} ({data_type})**",
            f"📊 Protocols: {len(protocols)}",
            ""
        ]
        
        # Show protocols by volume
        if protocols:
            sorted_protocols = sorted(protocols, key=lambda x: x.get(data_type, 0), reverse=True)
            result_lines.append("**DEX Protocols on Chain:**")
            for i, protocol in enumerate(sorted_protocols, 1):
                name = protocol.get("name", "Unknown")
                volume = protocol.get(data_type, 0)
                change = protocol.get("change_1d", 0)
                
                volume_str = f"${format_number(volume)}"
                change_str = f"{change:+.2f}%" if isinstance(change, (int, float)) else "N/A"
                
                result_lines.append(f"{i:2d}. **{name}**: {volume_str} ({change_str})")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching DEX chain overview: {e}")
        return f"❌ Error fetching DEX chain overview: {str(e)}"


@mcp.tool()
async def get_dex_protocol_summary(
    protocol: str,
    exclude_total_data_chart: Optional[str] = None,
    data_type: str = "dailyVolume"
) -> str:
    """
    Get DEX protocol summary data.
    
    Args:
        protocol: Protocol name
        exclude_total_data_chart: Comma-separated list of chains to exclude
        data_type: Type of data (dailyVolume, totalVolume)
        
    Returns:
        Formatted string with protocol DEX data
    """
    try:
        protocol_clean = quote(str(protocol).strip(), safe='')
        url = f"{DEFILLAMA_API_BASE}/summary/dexs/{protocol_clean}"
        
        params = {"dataType": data_type}
        if exclude_total_data_chart:
            params["excludeTotalDataChart"] = exclude_total_data_chart
        
        logger.info(f"Fetching DEX summary for protocol: {protocol}")
        data = await make_api_request(url, params)
        
        if not isinstance(data, dict):
            return f"❌ Invalid DEX summary data format received for protocol: {protocol}"
        
        total_volume = data.get("totalVolume", 0)
        daily_volume = data.get("dailyVolume", 0)
        change_1d = data.get("change_1d", 0)
        
        result_lines = [
            f"**DEX Protocol Summary - {protocol}**",
            f"💰 Total {data_type}: ${format_number(total_volume if data_type == 'totalVolume' else daily_volume)}",
            f"📈 24h Change: {change_1d:+.2f}%" if isinstance(change_1d, (int, float)) else "📈 24h Change: N/A",
        ]
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching DEX protocol summary: {e}")
        return f"❌ Error fetching DEX protocol summary: {str(e)}"


# =============================================================================
# OPTIONS TOOLS
# =============================================================================

@mcp.tool()
async def get_options_overview(
    exclude_total_data_chart: Optional[str] = None,
    data_type: str = "dailyPremiumVolume"
) -> str:
    """
    Get options trading overview across all chains.
    
    Args:
        exclude_total_data_chart: Comma-separated list of chains to exclude
        data_type: Type of data (dailyPremiumVolume, dailyNotionalVolume)
        
    Returns:
        Formatted string with options overview
    """
    try:
        url = f"{DEFILLAMA_API_BASE}/overview/options"
        
        params = {"dataType": data_type}
        if exclude_total_data_chart:
            params["excludeTotalDataChart"] = exclude_total_data_chart
        
        logger.info("Fetching options overview")
        data = await make_api_request(url, params)
        
        if not isinstance(data, dict):
            return "❌ Invalid options overview data format received"
        
        protocols = data.get("protocols", [])
        chains = data.get("chains", [])
        
        result_lines = [
            f"**Options Trading Overview ({data_type})**",
            f"📊 Protocols: {len(protocols)} | ⛓️ Chains: {len(chains)}",
            ""
        ]
        
        # Show top protocols
        if protocols:
            sorted_protocols = sorted(protocols, key=lambda x: x.get(data_type, 0), reverse=True)[:10]
            result_lines.append("**Top Options Protocols:**")
            for i, protocol in enumerate(sorted_protocols, 1):
                name = protocol.get("name", "Unknown")
                volume = protocol.get(data_type, 0)
                change = protocol.get("change_1d", 0)
                
                volume_str = f"${format_number(volume)}"
                change_str = f"{change:+.2f}%" if isinstance(change, (int, float)) else "N/A"
                
                result_lines.append(f"{i:2d}. **{name}**: {volume_str} ({change_str})")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching options overview: {e}")
        return f"❌ Error fetching options overview: {str(e)}"


# =============================================================================
# FEES TOOLS
# =============================================================================

@mcp.tool()
async def get_fees_overview(
    exclude_total_data_chart: Optional[str] = None,
    data_type: str = "dailyFees"
) -> str:
    """
    Get protocol fees overview across all chains.
    
    Args:
        exclude_total_data_chart: Comma-separated list of chains to exclude
        data_type: Type of data (dailyFees, dailyRevenue, totalFees, totalRevenue)
        
    Returns:
        Formatted string with fees overview
    """
    try:
        url = f"{DEFILLAMA_API_BASE}/overview/fees"
        
        params = {"dataType": data_type}
        if exclude_total_data_chart:
            params["excludeTotalDataChart"] = exclude_total_data_chart
        
        logger.info("Fetching fees overview")
        data = await make_api_request(url, params)
        
        if not isinstance(data, dict):
            return "❌ Invalid fees overview data format received"
        
        protocols = data.get("protocols", [])
        chains = data.get("chains", [])
        
        result_lines = [
            f"**Protocol Fees Overview ({data_type})**",
            f"📊 Protocols: {len(protocols)} | ⛓️ Chains: {len(chains)}",
            ""
        ]
        
        # Show top protocols by fees
        if protocols:
            sorted_protocols = sorted(protocols, key=lambda x: x.get(data_type, 0), reverse=True)[:10]
            result_lines.append("**Top Fee Generating Protocols:**")
            for i, protocol in enumerate(sorted_protocols, 1):
                name = protocol.get("name", "Unknown")
                fees = protocol.get(data_type, 0)
                change = protocol.get("change_1d", 0)
                
                fees_str = f"${format_number(fees)}"
                change_str = f"{change:+.2f}%" if isinstance(change, (int, float)) else "N/A"
                
                result_lines.append(f"{i:2d}. **{name}**: {fees_str} ({change_str})")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching fees overview: {e}")
        return f"❌ Error fetching fees overview: {str(e)}"


# =============================================================================
# ADVANCED ANALYSIS TOOLS
# =============================================================================

@mcp.tool()
async def analyze_protocol_performance(
    protocol_names: str,
    metrics: str = "tvl,volume,fees",
    timeframe: str = "7d"
) -> str:
    """
    Analyze and compare multiple protocols across various metrics.
    
    Args:
        protocol_names: Comma-separated list of protocol names
        metrics: Comma-separated list of metrics (tvl, volume, fees, apy)
        timeframe: Analysis timeframe (1d, 7d, 30d)
        
    Returns:
        Formatted comparison analysis
    """
    try:
        protocols = [p.strip() for p in protocol_names.split(',')]
        metric_list = [m.strip() for m in metrics.split(',')]
        
        result_lines = [
            f"**Protocol Performance Analysis**",
            f"🔍 Protocols: {', '.join(protocols)}",
            f"📊 Metrics: {', '.join(metric_list)}",
            f"📅 Timeframe: {timeframe}",
            ""
        ]
        
        protocol_data = {}
        
        # Fetch data for each protocol
        for protocol in protocols:
            try:
                protocol_clean = quote(protocol.lower(), safe='')
                url = f"{DEFILLAMA_API_BASE}/protocol/{protocol_clean}"
                data = await make_api_request(url)
                
                if isinstance(data, dict):
                    protocol_data[protocol] = {
                        'name': data.get('name', protocol),
                        'tvl': data.get('tvl', 0),
                        'change_1d': data.get('change_1d', 0),
                        'change_7d': data.get('change_7d', 0),
                        'mcap': data.get('mcap', 0),
                        'category': data.get('category', 'Unknown')
                    }
                else:
                    protocol_data[protocol] = {'name': protocol, 'error': 'Data not found'}
                    
            except Exception as e:
                protocol_data[protocol] = {'name': protocol, 'error': str(e)}
        
        # Generate comparison
        result_lines.append("**Protocol Comparison:**")
        
        for protocol, data in protocol_data.items():
            if 'error' in data:
                result_lines.append(f"❌ **{protocol}**: {data['error']}")
                continue
                
            name = data.get('name', protocol)
            tvl = data.get('tvl', 0)
            change_1d = data.get('change_1d', 0)
            change_7d = data.get('change_7d', 0)
            category = data.get('category', 'Unknown')
            
            result_lines.append(f"**{name}** ({category})")
            result_lines.append(f"  💰 TVL: ${format_number(tvl)}")
            result_lines.append(f"  📈 1D: {change_1d:+.2f}% | 7D: {change_7d:+.2f}%")
            result_lines.append("")
        
        # Add ranking by TVL
        valid_protocols = [(k, v) for k, v in protocol_data.items() if 'error' not in v]
        if len(valid_protocols) > 1:
            sorted_by_tvl = sorted(valid_protocols, key=lambda x: x[1].get('tvl', 0), reverse=True)
            result_lines.append("**TVL Ranking:**")
            for i, (protocol, data) in enumerate(sorted_by_tvl, 1):
                name = data.get('name', protocol)
                tvl = data.get('tvl', 0)
                result_lines.append(f"{i}. {name}: ${format_number(tvl)}")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error analyzing protocol performance: {e}")
        return f"❌ Error analyzing protocol performance: {str(e)}"


@mcp.tool()
async def find_arbitrage_opportunities(
    tokens: str,
    chains: Optional[str] = None,
    min_price_diff: float = 1.0
) -> str:
    """
    Find potential arbitrage opportunities across chains.
    
    Args:
        tokens: Comma-separated list of token symbols or addresses
        chains: Comma-separated list of chains to check (optional)
        min_price_diff: Minimum price difference percentage to report
        
    Returns:
        Formatted arbitrage opportunities report
    """
    try:
        token_list = [t.strip() for t in tokens.split(',')]
        
        result_lines = [
            f"**Arbitrage Opportunities Scanner**",
            f"🪙 Tokens: {', '.join(token_list)}",
            f"📊 Min Price Diff: {min_price_diff}%",
            ""
        ]
        
        # This is a simplified example - in practice, you'd need to:
        # 1. Get current prices from multiple DEXs/chains
        # 2. Calculate price differences
        # 3. Account for transaction costs
        # 4. Consider liquidity depth
        
        result_lines.extend([
            "**Note**: This is a basic implementation.",
            "For real arbitrage analysis, consider:",
            "• Transaction costs and gas fees",
            "• Liquidity depth on each chain",
            "• Bridge costs and time delays",
            "• Slippage impact",
            "",
            "**Recommended approach:**",
            "1. Use get_current_prices() for each token",
            "2. Compare prices across different chains",
            "3. Calculate net profit after all costs"
        ])
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error finding arbitrage opportunities: {e}")
        return f"❌ Error finding arbitrage opportunities: {str(e)}"


@mcp.tool()
async def optimize_yield_strategy(
    capital_usd: float,
    risk_tolerance: str = "medium",
    min_apy: float = 5.0,
    preferred_chains: Optional[str] = None,
    exclude_il_risk: bool = False
) -> str:
    """
    Optimize yield farming strategy based on criteria.
    
    Args:
        capital_usd: Available capital in USD
        risk_tolerance: Risk level (low, medium, high)
        min_apy: Minimum APY requirement
        preferred_chains: Comma-separated list of preferred chains
        exclude_il_risk: Exclude pools with impermanent loss risk
        
    Returns:
        Formatted yield optimization strategy
    """
    try:
        result_lines = [
            f"**Yield Strategy Optimization**",
            f"💰 Capital: ${format_number(capital_usd)}",
            f"⚖️ Risk Tolerance: {risk_tolerance}",
            f"📈 Min APY: {min_apy}%",
            ""
        ]
        
        # Get yield pools with filters
        pools_data = await make_api_request(f"{DEFILLAMA_YIELDS_API}/pools")
        
        if isinstance(pools_data, dict) and "data" in pools_data:
            pools = pools_data["data"]
        elif isinstance(pools_data, list):
            pools = pools_data
        else:
            return "❌ Unable to fetch yield pools data"
        
        # Apply filters
        filtered_pools = []
        for pool in pools:
            if not isinstance(pool, dict):
                continue
                
            apy = pool.get('apy', 0)
            tvl = pool.get('tvlUsd', 0)
            il7d = pool.get('il7d', 0)
            chain = pool.get('chain', '')
            
            # Filter by minimum APY
            if apy < min_apy:
                continue
                
            # Filter by risk tolerance
            if risk_tolerance == "low" and (apy > 15 or abs(il7d) > 5):
                continue
            elif risk_tolerance == "medium" and (apy > 50 or abs(il7d) > 15):
                continue
                
            # Filter by IL risk
            if exclude_il_risk and abs(il7d) > 1:
                continue
                
            # Filter by preferred chains
            if preferred_chains:
                chain_list = [c.strip().lower() for c in preferred_chains.split(',')]
                if chain.lower() not in chain_list:
                    continue
                    
            # Filter by minimum TVL (for safety)
            if tvl < 1000000:  # $1M minimum
                continue
                
            filtered_pools.append(pool)
        
        if not filtered_pools:
            result_lines.append("❌ No pools found matching your criteria.")
            result_lines.append("Consider adjusting your parameters:")
            result_lines.append("• Lower minimum APY")
            result_lines.append("• Higher risk tolerance")
            result_lines.append("• Include more chains")
            return "\n".join(result_lines)
        
        # Sort by risk-adjusted return (APY / risk factor)
        def risk_factor(pool):
            base_risk = 1.0
            apy = pool.get('apy', 0)
            il7d = abs(pool.get('il7d', 0))
            
            # Higher APY = higher risk
            if apy > 50:
                base_risk *= 3
            elif apy > 20:
                base_risk *= 2
            elif apy > 10:
                base_risk *= 1.5
                
            # IL risk factor
            base_risk *= (1 + il7d / 100)
            
            return base_risk
        
        scored_pools = []
        for pool in filtered_pools:
            apy = pool.get('apy', 0)
            risk = risk_factor(pool)
            score = apy / risk
            scored_pools.append((pool, score))
        
        # Sort by score (higher is better)
        scored_pools.sort(key=lambda x: x[1], reverse=True)
        
        result_lines.append(f"**Recommended Pools ({len(scored_pools)} found):**")
        result_lines.append("")
        
        # Show top 5 recommendations
        for i, (pool, score) in enumerate(scored_pools[:5], 1):
            project = pool.get('project', 'Unknown')
            symbol = pool.get('symbol', 'Unknown')
            apy = pool.get('apy', 0)
            tvl = pool.get('tvlUsd', 0)
            chain = pool.get('chain', 'Unknown')
            il7d = pool.get('il7d', 0)
            
            # Calculate suggested allocation
            allocation_pct = max(10, min(40, 100 / len(scored_pools[:5])))
            allocation_usd = capital_usd * allocation_pct / 100
            
            result_lines.append(f"**{i}. {project} - {symbol}**")
            result_lines.append(f"   📈 APY: {apy:.2f}% | 💰 TVL: ${format_number(tvl)}")
            result_lines.append(f"   ⛓️ Chain: {chain} | 📉 IL 7D: {il7d:.2f}%")
            result_lines.append(f"   💡 Suggested Allocation: {allocation_pct:.1f}% (${format_number(allocation_usd)})")
            result_lines.append(f"   🏆 Risk Score: {score:.2f}")
            result_lines.append("")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error optimizing yield strategy: {e}")
        return f"❌ Error optimizing yield strategy: {str(e)}"


# =============================================================================
# RESOURCES AND PROMPTS  
# =============================================================================

@mcp.resource("chains://supported")
def get_supported_chains() -> str:
    """List of supported blockchain networks in DefiLlama."""
    chains = [
        "Ethereum", "BSC", "Polygon", "Avalanche", "Fantom", "Arbitrum", "Optimism",
        "Solana", "Terra", "Heco", "xDai", "Harmony", "Moonriver", "Cronos",
        "Aurora", "Fuse", "KCC", "OKExChain", "Celo", "Moonbeam", "Metis",
        "Kava", "Klaytn", "Iotex", "Milkomeda", "DFK", "REI", "Astar", "Emerald",
        "Palm", "Kardia", "TomoChain", "Velas", "Syscoin", "Ubiq", "Energi",
        "Step", "Godwoken", "Callisto", "CSC", "Ergo", "Liquidchain", "Nahmii",
        "ThunderCore", "Telos", "EOS", "WAX", "Hive", "Kujira", "Cosmos"
    ]
    
    return f"**Supported Blockchain Networks ({len(chains)} total)**\n\n" + \
           "\n".join(f"• {chain}" for chain in chains)


@mcp.resource("api://endpoints")
def get_api_endpoints() -> str:
    """Available DefiLlama API endpoints and tools."""
    endpoints = {
        "Protocol APIs": [
            "get_protocols - List all DeFi protocols with filtering",
            "get_protocol_details - Detailed protocol information",
            "get_protocol_tvl - Protocol TVL data",
            "analyze_protocol_performance - Compare multiple protocols"
        ],
        "Chain APIs": [
            "get_chains - List all supported chains",
            "get_chain_tvl_history - Historical chain TVL data",
            "get_all_chains_tvl - Total DeFi TVL across all chains"
        ],
        "Price APIs": [
            "get_current_prices - Current token prices",
            "get_historical_prices - Historical price data",
            "get_batch_historical_prices - Batch historical data",
            "get_price_chart - Price chart data with statistics",
            "get_price_percentage_changes - Price change percentages",
            "get_first_prices - First recorded prices",
            "get_block_info - Block information for chains"
        ],
        "Yield APIs": [
            "get_yield_pools - Comprehensive yield pool data",
            "get_pool_chart - Pool historical performance",
            "optimize_yield_strategy - AI-powered yield optimization"
        ],
        "Stablecoin APIs": [
            "get_stablecoins - Stablecoin market data",
            "get_stablecoin_charts - Circulation charts",
            "get_stablecoin_chains - Supported chains",
            "get_stablecoin_prices - Current stablecoin prices"
        ],
        "DEX APIs": [
            "get_dex_overview - DEX volume overview",
            "get_dex_chain_overview - Chain-specific DEX data",
            "get_dex_protocol_summary - Protocol DEX summary"
        ],
        "Advanced Analytics": [
            "find_arbitrage_opportunities - Cross-chain arbitrage scanner",
            "get_options_overview - Options trading data",
            "get_fees_overview - Protocol fees analysis"
        ]
    }
    
    result_lines = ["**DefiLlama MCP Server - Available Tools**\n"]
    
    for category, tool_list in endpoints.items():
        result_lines.append(f"**{category}:**")
        for tool in tool_list:
            result_lines.append(f"  • {tool}")
        result_lines.append("")
    
    return "\n".join(result_lines)


@mcp.prompt()
def analyze_defi_portfolio(tokens: str, analysis_type: str = "comprehensive") -> str:
    """Generate a prompt for comprehensive DeFi portfolio analysis."""
    return f"""Please analyze this DeFi portfolio using the DefiLlama tools:

**Portfolio Tokens:** {tokens}
**Analysis Type:** {analysis_type}

**Analysis Framework:**

1. **Current Market Analysis**
   - Use get_current_prices() to get latest token prices
   - Calculate current portfolio value and allocation
   - Identify price trends and momentum

2. **Risk Assessment**
   - Analyze price volatility using get_price_chart()
   - Check for smart contract risks via protocol analysis
   - Evaluate concentration risk and diversification
   - Use get_protocol_details() for protocol-specific risks

3. **Yield Optimization**
   - Use get_yield_pools() to find opportunities for each token
   - Apply optimize_yield_strategy() for capital allocation
   - Consider impermanent loss risks and APY sustainability

4. **Market Context**
   - Use get_protocols() to understand sector performance
   - Analyze chain distribution with get_chains()
   - Check stablecoin exposure with get_stablecoins()

5. **Recommendations**
   - Suggest rebalancing strategies
   - Identify yield farming opportunities
   - Recommend risk mitigation measures
   - Propose portfolio improvements

**Deliverables:**
- Current portfolio valuation
- Risk score and analysis
- Yield optimization suggestions
- Specific action items with reasoning

Use multiple DefiLlama tools to gather comprehensive data for your analysis."""


@mcp.prompt()
def find_yield_opportunities(
    capital_usd: float = 10000,
    risk_level: str = "medium",
    min_apy: float = 5.0,
    chains: str = "ethereum,polygon,arbitrum"
) -> str:
    """Generate a prompt for finding optimal yield farming opportunities."""
    return f"""Find and analyze the best yield farming opportunities with these parameters:

**Investment Parameters:**
- Capital: ${capital_usd:,.0f}
- Risk Tolerance: {risk_level}
- Minimum APY: {min_apy}%
- Preferred Chains: {chains}

**Analysis Process:**

1. **Pool Discovery**
   - Use get_yield_pools() with comprehensive filtering
   - Apply risk and return criteria
   - Focus on chains: {chains}

2. **Risk Analysis**
   - Evaluate impermanent loss risks
   - Assess protocol security and audit status
   - Check TVL stability and trends using get_pool_chart()

3. **Strategy Optimization**
   - Use optimize_yield_strategy() for portfolio allocation
   - Consider correlation between different pools
   - Factor in gas costs and transaction complexity

4. **Due Diligence**
   - Use get_protocol_details() for each recommended protocol
   - Check recent performance trends
   - Analyze token pair fundamentals

5. **Implementation Plan**
   - Provide step-by-step execution strategy
   - Suggest position sizing and diversification
   - Include monitoring and exit criteria

**Expected Output:**
- Top 5 yield opportunities ranked by risk-adjusted returns
- Detailed analysis of each opportunity
- Suggested capital allocation strategy
- Risk mitigation recommendations
- Implementation timeline and steps

Use the DefiLlama tools to gather real-time data for your analysis."""


# =============================================================================
# SERVER LIFECYCLE
# =============================================================================

def cleanup_sync():
    """Synchronous cleanup function for atexit."""
    global http_client, response_cache
    
    # Clear cache
    response_cache.clear()
    
    if http_client:
        try:
            # Try to close in a new event loop if none exists
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, schedule cleanup
                    loop.create_task(http_client.aclose())
                else:
                    loop.run_until_complete(http_client.aclose())
            except RuntimeError:
                # No event loop, create one
                asyncio.run(http_client.aclose())
            logger.info("HTTP client closed successfully")
        except Exception as e:
            logger.debug(f"Error closing HTTP client: {e}")
        finally:
            http_client = None


@lru_cache(maxsize=100)
def get_cached_chain_info(chain_name: str) -> str:
    """Get cached chain information."""
    return f"Chain: {chain_name} - Cached info would be retrieved from DefiLlama API"


def main():
    """Run the comprehensive DefiLlama MCP server."""
    # Register cleanup function
    atexit.register(cleanup_sync)
    
    logger.info("Starting DefiLlama Comprehensive MCP Server...")
    
    try:
        # Run the server - it manages its own event loop
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        logger.info("DefiLlama Comprehensive MCP Server stopped")


if __name__ == "__main__":
    main()
                
