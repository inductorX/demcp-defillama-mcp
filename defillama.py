from typing import Any
import httpx
import json
import os
from mcp.server.fastmcp import FastMCP

# Initialize Defillama mcp server  
# Use environment variables for host and port configuration for deployment platforms
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8090"))
mcp = FastMCP("defillama_mcp", host=HOST, port=PORT)

# Constants
DEFI_API_BASE = "https://api.llama.fi"
COIN_API_BASE = "https://coins.llama.fi"
YIELDS_API_BASE = "https://yields.llama.fi"
USER_AGENT = "DEFI-MCP/1.0"

@mcp.tool(
    description="Retrieve a list of all DeFi protocols from DeFi Llama, limited to the first 20 results"
)
async def get_protocols() -> dict[Any, Any]:
    """Get all protocols from defillama.
    """
    url = f"{DEFI_API_BASE}/protocols"
    data = await make_request(url)
    
    if data is None:
        return {"error": "Failed to fetch protocols data"}
    return data[:20]

@mcp.tool(
    description="Get Total Value Locked (TVL) information for a specific DeFi protocol"
)
async def get_protocol_tvl(protocol: str) -> dict[Any, Any]:
    """Get a defi protocol tvl from defillama
    
    Args:
        protocol: protocol name
        
    Example:
        - protocol="aave" - Returns TVL data for Aave protocol across different chains
        - protocol="uniswap" - Returns TVL data for Uniswap protocol across different chains
    """
    url = f"{DEFI_API_BASE}/protocol/{protocol}"
    data = await make_request(url)
    
    if data is None:
        return {"error": f"Failed to fetch TVL data for protocol {protocol}"}
    return data.get("currentChainTvls", {})

@mcp.tool(
    description="Retrieve historical Total Value Locked (TVL) data for a specific blockchain"
)
async def get_chain_tvl(chain: str) -> dict[Any, Any]:
    """Get a chain's tvl

    Args:
        chain: chain name
        
    Example:
        - chain="ethereum" - Returns historical TVL data for Ethereum blockchain
        - chain="bsc" - Returns historical TVL data for Binance Smart Chain
    """
    url = f"{DEFI_API_BASE}/v2/historicalChainTvl/{chain}"
    data = await make_request(url)
    
    if data is None:
        return {"error": f"Failed to fetch TVL data for chain {chain}"}
    return data[:30]

@mcp.tool(
    description="Get current price information for a specific token, for example token=ethereum:0xdF574c24545E5FfEcb9a659c229253D4111d87e1 token=coingecko:ethereum"
)
async def get_token_prices(token: str) -> dict[Any, Any]:
    """Get a token's price
    
    Args:
        token: token name
    Example:
        - token="ethereum:0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2" - Returns price information for WETH token
        - token="bsc:0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c" - Returns price information for WBNB token
    """
    url = f"{COIN_API_BASE}/prices/current/{token}"
    data = await make_request(url)
    
    if data is None:
        return {"error": f"Failed to fetch price data for token {token}"}
    return data

@mcp.tool(
    description="Retrieve a list of all liquidity pools from DeFi Llama, limited to the first 30 results"
)
async def get_pools() -> dict[str, Any]:
    """Get all pools from defillama.
    """
    url = f"{YIELDS_API_BASE}/pools"
    data = await make_request(url)
    
    if data is None:
        return {"error": "Failed to fetch pools data"}
    if isinstance(data, dict) and 'data' in data:
        return data['data'][:30]
    return data[:30] if isinstance(data, list) else {"error": "Unexpected data format"}


@mcp.tool(
    description="Get detailed information about a specific liquidity pool by its ID")
async def get_pool_tvl(pool: str) -> dict[str, Any]:
    """Get a pool's tvl from defillama.
    
    Args:
        pool: pool id
        
    Example:
        - pool="747c1d2a-c668-4682-b9f9-296708a3dd90" - Returns detailed data for the specified pool
        - pool="2cbc5e8f-b7ef-4568-8e8e-1a7543af4e5f" - Returns detailed data for the specified pool
    """
    url = f"{YIELDS_API_BASE}/chart/{pool}"
    data = await make_request(url)
    
    if data is None:
        return {"error": f"Failed to fetch TVL data for pool {pool}"}
    if isinstance(data, dict) and 'data' in data:
        return data['data'][:30]
    return data[:30] if isinstance(data, list) else {"error": "Unexpected data format"}

@mcp.tool(
    description="Get enriched pools data with predictions and additional metadata")
async def get_pools_enriched() -> dict[str, Any]:
    """Get all pools with enriched data including predictions.
    Returns pools with additional metadata like predictions, APY breakdowns, and risk metrics.
    """
    url = f"{YIELDS_API_BASE}/pools"
    data = await make_request(url)
    
    if data is None:
        return {"error": "Failed to fetch enriched pools data"}
    if isinstance(data, dict) and 'data' in data:
        # Return more pools since this is enriched data
        return {"pools": data['data'][:50], "status": data.get('status', 'success')}
    return data[:50] if isinstance(data, list) else {"error": "Unexpected data format"}

@mcp.tool(
    description="Get historical APY and TVL data for a specific pool")
async def get_pool_chart(pool: str) -> dict[str, Any]:
    """Get historical APY and TVL data for a specific pool.
    
    Args:
        pool: pool id (can be retrieved from get_pools)
        
    Example:
        - pool="747c1d2a-c668-4682-b9f9-296708a3dd90" - Returns historical data for the pool
    """
    url = f"{YIELDS_API_BASE}/chart/{pool}"
    data = await make_request(url)
    
    if data is None:
        return {"error": f"Failed to fetch chart data for pool {pool}"}
    if isinstance(data, dict) and 'data' in data:
        return {"historical_data": data['data'], "status": data.get('status', 'success')}
    return data if isinstance(data, list) else {"error": "Unexpected data format"}

@mcp.tool(
    description="Get current prices for multiple tokens at once")
async def get_multiple_token_prices(tokens: str) -> dict[str, Any]:
    """Get prices for multiple tokens in a single request.
    
    Args:
        tokens: comma-separated list of token identifiers
        
    Example:
        - tokens="coingecko:ethereum,coingecko:bitcoin" - Returns prices for ETH and BTC
        - tokens="ethereum:0xA0b86a33E6f5b7aDBC5eD84c0e7BD75ac8c30c0d,coingecko:usd-coin" - Multiple formats
    """
    url = f"{COIN_API_BASE}/prices/current/{tokens}"
    data = await make_request(url)
    
    if data is None:
        return {"error": f"Failed to fetch prices for tokens: {tokens}"}
    return data

@mcp.tool(
    description="Get historical prices for a token over time")
async def get_token_price_history(token: str, span: int = 30) -> dict[str, Any]:
    """Get historical price data for a token.
    
    Args:
        token: token identifier (e.g., coingecko:ethereum)
        span: number of days of history (default: 30, max: 365)
        
    Example:
        - token="coingecko:ethereum", span=7 - Returns 7 days of ETH price history
        - token="ethereum:0xA0b86a33E6f5b7aDBC5eD84c0e7BD75ac8c30c0d", span=90 - 90 days of token history
    """
    # Limit span to reasonable range
    span = max(1, min(span, 365))
    url = f"{COIN_API_BASE}/prices/historical/{span}/{token}"
    data = await make_request(url)
    
    if data is None:
        return {"error": f"Failed to fetch price history for token {token}"}
    return data

@mcp.tool(
    description="Get TVL data for all chains")
async def get_all_chains_tvl() -> dict[str, Any]:
    """Get current TVL data for all supported blockchains.
    Returns TVL information for all chains tracked by DeFi Llama.
    """
    url = f"{DEFI_API_BASE}/chains"
    data = await make_request(url)
    
    if data is None:
        return {"error": "Failed to fetch chains TVL data"}
    return data[:50] if isinstance(data, list) else data

@mcp.tool(
    description="Get detailed information about a specific protocol including all metadata")
async def get_protocol_details(protocol: str) -> dict[str, Any]:
    """Get comprehensive protocol information including TVL, chains, tokens, and metadata.
    
    Args:
        protocol: protocol slug/name
        
    Example:
        - protocol="aave" - Returns complete Aave protocol information
        - protocol="uniswap" - Returns complete Uniswap protocol information
    """
    url = f"{DEFI_API_BASE}/protocol/{protocol}"
    data = await make_request(url)
    
    if data is None:
        return {"error": f"Failed to fetch details for protocol {protocol}"}
    return data

@mcp.tool(
    description="Get top protocols by TVL with optional category filtering")
async def get_top_protocols(category: str = "") -> dict[str, Any]:
    """Get top DeFi protocols ranked by TVL, optionally filtered by category.
    
    Args:
        category: optional category filter (e.g., "DEXes", "Lending", "Liquid Staking")
        
    Example:
        - category="" - Returns top 50 protocols across all categories
        - category="DEXes" - Returns top DEX protocols only
        - category="Lending" - Returns top lending protocols only
    """
    if category:
        url = f"{DEFI_API_BASE}/protocols?category={category}"
    else:
        url = f"{DEFI_API_BASE}/protocols"
    
    data = await make_request(url)
    
    if data is None:
        return {"error": "Failed to fetch top protocols data"}
    
    # Sort by TVL and return top 50
    if isinstance(data, list):
        # Filter out protocols with None or invalid TVL values
        valid_protocols = [p for p in data if isinstance(p.get('tvl'), (int, float))]
        sorted_protocols = sorted(valid_protocols, key=lambda x: x.get('tvl', 0), reverse=True)
        return {"protocols": sorted_protocols[:50], "category": category or "all"}
    return data

@mcp.tool(
    description="Search for protocols by name or symbol")
async def search_protocols(query: str) -> dict[str, Any]:
    """Search for DeFi protocols by name or symbol.
    
    Args:
        query: search term (protocol name, symbol, or partial match)
        
    Example:
        - query="aave" - Finds protocols matching "aave"
        - query="UNI" - Finds protocols with "UNI" symbol
        - query="lending" - Finds protocols with "lending" in name/description
    """
    url = f"{DEFI_API_BASE}/protocols"
    data = await make_request(url)
    
    if data is None:
        return {"error": f"Failed to search protocols for query: {query}"}
    
    if not isinstance(data, list):
        return {"error": "Unexpected data format"}
    
    # Search through protocols
    query_lower = query.lower()
    matching_protocols = []
    
    for protocol in data:
        name = (protocol.get('name') or '').lower()
        symbol = (protocol.get('symbol') or '').lower()
        description = (protocol.get('description') or '').lower()
        category = (protocol.get('category') or '').lower()
        
        if (query_lower in name or 
            query_lower in symbol or 
            query_lower in description or
            query_lower in category):
            matching_protocols.append(protocol)
    
    return {
        "query": query,
        "matches": len(matching_protocols),
        "protocols": matching_protocols[:20]  # Limit to 20 results
    }


async def make_request(url: str) -> dict[str, Any] | None:
    """Make a request to the API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error making request to {url}: {str(e)}")
            return None


if __name__ == "__main__":
    # Use SSE transport for Smithery compatibility
    # This provides streaming HTTP endpoints that Smithery can auto-detect
    print("🚀 Starting DeFi Llama MCP Server with SSE transport...")
    print(f"📡 Server will be available at http://{HOST}:{PORT}")
    print("🔧 SSE endpoints: /sse/ and /messages/")
    mcp.run(transport='sse')
