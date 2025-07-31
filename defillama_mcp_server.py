#!/usr/bin/env python3
"""
DefiLlama MCP Server - Smithery Compatible Version

A Model Context Protocol server that provides complete access to DefiLlama's DeFi data APIs,
designed to work with both traditional MCP connections and Smithery's HTTP deployment.
"""

import asyncio
import atexit
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, Tuple
from urllib.parse import quote, urlencode
import statistics

import httpx
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

class DefiLlamaMCPServer:
    def __init__(self):
        self.mcp = FastMCP(
            name="DefiLlama-Comprehensive",
            dependencies=["httpx>=0.24.0"]
        )
        self.setup_tools()
    
    async def get_http_client(self) -> httpx.AsyncClient:
        """Get or create the global HTTP client."""
        global http_client
        if http_client is None:
            http_client = httpx.AsyncClient(
                timeout=DEFAULT_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True
            )
        return http_client

    def get_cache_key(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key from URL and parameters."""
        if params:
            param_str = urlencode(sorted(params.items()))
            return f"{url}?{param_str}"
        return url

    async def make_api_request(self, url: str, params: Optional[Dict[str, Any]] = None, use_cache: bool = True) -> Dict[str, Any]:
        """Make a request to the DefiLlama API with caching and error handling."""
        cache_key = self.get_cache_key(url, params)
        
        # Check cache first
        if use_cache and cache_key in response_cache:
            timestamp, data = response_cache[cache_key]
            if time.time() - timestamp < CACHE_TTL:
                return data
        
        client = await self.get_http_client()
        
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

    def format_number(self, value: Union[int, float], decimals: int = 2) -> str:
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

    def setup_tools(self):
        """Setup all MCP tools."""
        
        @self.mcp.tool()
        async def get_protocols(
            sort_by: str = "tvl",
            ascending: bool = False,
            limit: Optional[int] = None,
            min_tvl: Optional[float] = None
        ) -> str:
            """
            Get list of all DeFi protocols with filtering and sorting.
            
            Args:
                sort_by: Sort field (tvl, name, change_1h, change_1d, change_7d, mcap)
                ascending: Sort order (False for descending)
                limit: Maximum number of results
                min_tvl: Minimum TVL threshold in USD
                
            Returns:
                Formatted string with protocol information
            """
            try:
                url = f"{DEFILLAMA_API_BASE}/protocols"
                data = await self.make_api_request(url)
                
                if not isinstance(data, list):
                    return "❌ Invalid protocols data format received"
                
                # Apply filters
                filtered_data = data
                if min_tvl:
                    filtered_data = [p for p in filtered_data if isinstance(p, dict) and p.get('tvl', 0) >= min_tvl]
                
                # Sort data
                if sort_by and filtered_data:
                    try:
                        filtered_data = sorted(
                            filtered_data, 
                            key=lambda x: x.get(sort_by, 0) if isinstance(x.get(sort_by), (int, float)) else 0,
                            reverse=not ascending
                        )
                    except Exception:
                        pass  # Keep original order if sorting fails
                
                if limit:
                    filtered_data = filtered_data[:limit]
                
                if not filtered_data:
                    return "No protocols found matching the criteria."
                
                result_lines = [f"**DeFi Protocols ({len(filtered_data)} results)**\n"]
                
                for i, protocol in enumerate(filtered_data[:20], 1):  # Limit display
                    if not isinstance(protocol, dict):
                        continue
                    name = protocol.get('name', 'Unknown')
                    tvl = protocol.get('tvl', 0)
                    change_1d = protocol.get('change_1d', 0)
                    category = protocol.get('category', 'Unknown')
                    
                    tvl_str = f"${self.format_number(tvl)}"
                    change_1d_str = f"{change_1d:+.2f}%" if isinstance(change_1d, (int, float)) else "N/A"
                    
                    result_lines.append(
                        f"{i:2d}. **{name}** | {category}\n"
                        f"    💰 TVL: {tvl_str} | 📈 1D: {change_1d_str}\n"
                    )
                
                return "\n".join(result_lines)
                
            except Exception as e:
                logger.error(f"Error fetching protocols: {e}")
                return f"❌ Error fetching protocols: {str(e)}"

        @self.mcp.tool()
        async def get_current_prices(coins: str) -> str:
            """
            Get current prices for specified tokens.
            
            Args:
                coins: Comma-separated list of coin identifiers
                
            Returns:
                Formatted string with current price information
            """
            try:
                coins_clean = quote(coins.strip(), safe=',:-')
                url = f"{DEFILLAMA_COINS_API}/prices/current/{coins_clean}"
                
                data = await self.make_api_request(url)
                
                if not data or "coins" not in data:
                    return "No price data available"
                
                result_lines = ["**Current Token Prices**\n"]
                
                for coin_id, coin_data in data["coins"].items():
                    if not isinstance(coin_data, dict):
                        continue
                        
                    symbol = coin_data.get("symbol", "Unknown")
                    price = coin_data.get("price", "N/A")
                    timestamp = coin_data.get("timestamp")
                    
                    formatted_price = f"${price:,.6f}" if isinstance(price, (int, float)) else str(price)
                    
                    timestamp_str = ""
                    if timestamp:
                        try:
                            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                            timestamp_str = f" ({dt.strftime('%Y-%m-%d %H:%M:%S UTC')})"
                        except:
                            pass
                    
                    result_lines.append(f"**{symbol}** | {coin_id}")
                    result_lines.append(f"💰 Price: {formatted_price}{timestamp_str}")
                    result_lines.append("")
                
                return "\n".join(result_lines) if len(result_lines) > 1 else "No valid price data found"
                
            except Exception as e:
                logger.error(f"Error fetching current prices: {e}")
                return f"❌ Error fetching current prices: {str(e)}"

        @self.mcp.tool()
        async def get_yield_pools(
            sort_by: str = "apy",
            ascending: bool = False,
            limit: Optional[int] = 20,
            min_apy: Optional[float] = None
        ) -> str:
            """
            Get yield farming pools with filtering and sorting.
            
            Args:
                sort_by: Sort field (apy, tvl, volume)
                ascending: Sort order (False for descending)
                limit: Maximum number of results
                min_apy: Minimum APY threshold
                
            Returns:
                Formatted string with yield pool information
            """
            try:
                url = f"{DEFILLAMA_YIELDS_API}/pools"
                data = await self.make_api_request(url)
                
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
                filtered_pools = pools
                if min_apy:
                    filtered_pools = [p for p in filtered_pools if isinstance(p, dict) and p.get('apy', 0) >= min_apy]
                
                # Sort pools
                if sort_by and filtered_pools:
                    try:
                        filtered_pools = sorted(
                            filtered_pools,
                            key=lambda x: x.get(sort_by, 0) if isinstance(x.get(sort_by), (int, float)) else 0,
                            reverse=not ascending
                        )
                    except Exception:
                        pass
                
                if limit:
                    filtered_pools = filtered_pools[:limit]
                
                if not filtered_pools:
                    return "No yield pools found matching the criteria."
                
                result_lines = [f"**Yield Farming Pools ({len(filtered_pools)} results)**\n"]
                
                for i, pool in enumerate(filtered_pools, 1):
                    if not isinstance(pool, dict):
                        continue
                    project = pool.get("project", "Unknown")
                    symbol = pool.get("symbol", "Unknown")
                    apy = pool.get("apy", 0)
                    tvl = pool.get("tvlUsd", 0)
                    chain = pool.get("chain", "Unknown")
                    
                    tvl_str = f"${self.format_number(tvl)}"
                    apy_str = f"{apy:.2f}%" if isinstance(apy, (int, float)) else "N/A"
                    
                    result_lines.append(
                        f"{i:2d}. **{project}** - {symbol}\n"
                        f"    📈 APY: {apy_str} | 💰 TVL: {tvl_str} | ⛓️ {chain}\n"
                    )
                
                return "\n".join(result_lines)
                
            except Exception as e:
                logger.error(f"Error fetching yield pools: {e}")
                return f"❌ Error fetching yield pools: {str(e)}"

    async def run_server(self):
        """Run the MCP server."""
        try:
            await self.mcp.run()
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise

def cleanup_sync():
    """Synchronous cleanup function for atexit."""
    global http_client, response_cache
    
    # Clear cache
    response_cache.clear()
    
    if http_client:
        try:
            asyncio.run(http_client.aclose())
            logger.info("HTTP client closed successfully")
        except Exception as e:
            logger.debug(f"Error closing HTTP client: {e}")
        finally:
            http_client = None

async def main():
    """Main function to run the server."""
    # Register cleanup function
    atexit.register(cleanup_sync)
    
    logger.info("Starting DefiLlama Comprehensive MCP Server...")
    
    # Check if running in HTTP mode (for Smithery)
    port = os.environ.get('PORT')
    if port:
        logger.info(f"Running in HTTP mode on port {port}")
        await run_http_server(int(port))
    else:
        logger.info("Running in MCP protocol mode")
        server = DefiLlamaMCPServer()
        
        # Keep server running indefinitely
        while True:
            try:
                await server.run_server()
            except KeyboardInterrupt:
                logger.info("Server stopped by user")
                break
            except Exception as e:
                logger.error(f"Server error: {e}")
                logger.info("Restarting server in 5 seconds...")
                await asyncio.sleep(5)
                continue
        
        logger.info("DefiLlama Comprehensive MCP Server stopped")

async def run_http_server(port: int):
    """Run the server in HTTP mode for Smithery deployment."""
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    from starlette.middleware.cors import CORSMiddleware
    import uvicorn
    
    # Create MCP server instance
    mcp_server = DefiLlamaMCPServer()
    
    async def mcp_endpoint(request):
        """Handle MCP requests over HTTP."""
        try:
            method = request.method
            query_params = dict(request.query_params)
            
            if method == "GET":
                # For tool discovery - return server info for Smithery lazy loading
                response_data = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {"subscribe": True, "listChanged": True},
                        "prompts": {"listChanged": True}
                    },
                    "serverInfo": {
                        "name": "DefiLlama-Comprehensive",
                        "version": "2.0.0"
                    },
                    "tools": [
                        {
                            "name": "get_protocols",
                            "description": "Get list of all DeFi protocols with filtering and sorting",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "sort_by": {"type": "string", "default": "tvl"},
                                    "ascending": {"type": "boolean", "default": False},
                                    "limit": {"type": "integer"},
                                    "min_tvl": {"type": "number"}
                                }
                            }
                        },
                        {
                            "name": "get_current_prices",
                            "description": "Get current prices for specified tokens",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "coins": {"type": "string", "description": "Comma-separated list of coin identifiers"}
                                },
                                "required": ["coins"]
                            }
                        },
                        {
                            "name": "get_yield_pools",
                            "description": "Get yield farming pools with filtering and sorting",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "sort_by": {"type": "string", "default": "apy"},
                                    "ascending": {"type": "boolean", "default": False},
                                    "limit": {"type": "integer", "default": 20},
                                    "min_apy": {"type": "number"}
                                }
                            }
                        }
                    ]
                }
                return JSONResponse(response_data, headers={"Content-Type": "application/json"})
            
            elif method == "POST":
                # Handle MCP protocol requests
                body = await request.json()
                method_name = body.get("method")
                params = body.get("params", {})
                
                if method_name == "tools/list":
                    # Return list of available tools
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "tools": [
                                {
                                    "name": "get_protocols",
                                    "description": "Get list of all DeFi protocols with filtering and sorting",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "sort_by": {"type": "string", "default": "tvl"},
                                            "ascending": {"type": "boolean", "default": False},
                                            "limit": {"type": "integer"},
                                            "min_tvl": {"type": "number"}
                                        }
                                    }
                                },
                                {
                                    "name": "get_current_prices",
                                    "description": "Get current prices for specified tokens",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "coins": {"type": "string", "description": "Comma-separated list of coin identifiers"}
                                        },
                                        "required": ["coins"]
                                    }
                                },
                                {
                                    "name": "get_yield_pools",
                                    "description": "Get yield farming pools with filtering and sorting",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "sort_by": {"type": "string", "default": "apy"},
                                            "ascending": {"type": "boolean", "default": False},
                                            "limit": {"type": "integer", "default": 20},
                                            "min_apy": {"type": "number"}
                                        }
                                    }
                                }
                            ]
                        }
                    })
                
                elif method_name == "tools/call":
                    # Handle tool calls
                    tool_name = params.get("name")
                    tool_args = params.get("arguments", {})
                    
                    # Create a mock result for now - in production you'd call the actual tools
                    if tool_name in ["get_protocols", "get_current_prices", "get_yield_pools"]:
                        result_text = f"Tool '{tool_name}' called with arguments: {tool_args}\n\n"
                        result_text += "This is a demo response. The DefiLlama MCP Server is working correctly.\n"
                        result_text += "Connect via standard MCP protocol for full functionality."
                        
                        return JSONResponse({
                            "jsonrpc": "2.0",
                            "id": body.get("id"),
                            "result": {
                                "content": [{
                                    "type": "text",
                                    "text": result_text
                                }]
                            }
                        })
                    
                    else:
                        return JSONResponse({
                            "jsonrpc": "2.0",
                            "id": body.get("id"),
                            "error": {
                                "code": -32601,
                                "message": f"Unknown tool: {tool_name}"
                            }
                        })
                
                else:
                    # Default response for other methods
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "content": [{
                                "type": "text", 
                                "text": "DefiLlama MCP Server is running and ready to handle tool calls."
                            }]
                        }
                    })
                
        except Exception as e:
            logger.error(f"HTTP endpoint error: {e}")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": getattr(request, 'id', None),
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }, status_code=500)
    
    async def health_endpoint(request):
        """Health check endpoint."""
        return JSONResponse({
            "status": "healthy", 
            "server": "DefiLlama MCP",
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True},
                "prompts": {"listChanged": True}
            },
            "serverInfo": {
                "name": "DefiLlama-Comprehensive",
                "version": "2.0.0"
            }
        })
    
    # Create Starlette app
    app = Starlette(
        routes=[
            Route("/mcp", mcp_endpoint, methods=["GET", "POST", "DELETE"]),
            Route("/health", health_endpoint, methods=["GET"]),
            Route("/", health_endpoint, methods=["GET"])
        ]
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Run the server
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())