# DefiLlama MCP Server - Comprehensive Edition

A Model Context Protocol (MCP) server that provides complete access to DefiLlama's DeFi data APIs, enabling AI agents to perform sophisticated DeFi analysis, yield optimization, and market intelligence.

## Features

### 🚀 Core Capabilities
- **Complete API Coverage**: Access to all major DefiLlama endpoints
- **Advanced Filtering**: Comprehensive filtering and sorting for all data types
- **AI-Optimized**: Response formats designed for AI agent consumption
- **Intelligent Caching**: Built-in caching for improved performance
- **Type Safety**: Full type annotations for better development experience
- **Error Handling**: Robust error handling with descriptive messages

### 📊 Available Tools

#### Protocol Analysis
- `get_protocols` - List all DeFi protocols with advanced filtering
- `get_protocol_details` - Detailed protocol information and metrics
- `get_protocol_tvl` - Protocol TVL data
- `analyze_protocol_performance` - Compare multiple protocols

#### Chain Analytics
- `get_chains` - List all supported blockchains with TVL data
- `get_chain_tvl_history` - Historical TVL data for specific chains
- `get_all_chains_tvl` - Total DeFi TVL across all chains

#### Price Intelligence
- `get_current_prices` - Current token prices with metadata
- `get_historical_prices` - Historical price data for specific timestamps
- `get_batch_historical_prices` - Batch historical data for multiple tokens
- `get_price_chart` - Price chart data with statistical analysis
- `get_price_percentage_changes` - Price change percentages over time periods
- `get_first_prices` - First recorded prices for tokens
- `get_block_info` - Block information for chains and timestamps

#### Yield Farming
- `get_yield_pools` - Comprehensive yield pool data with filtering
- `get_pool_chart` - Historical pool performance metrics
- `optimize_yield_strategy` - AI-powered yield optimization

#### Stablecoin Analysis
- `get_stablecoins` - Stablecoin market data and peg stability
- `get_stablecoin_charts` - Circulation charts and trends
- `get_stablecoin_chains` - Supported chains for stablecoins
- `get_stablecoin_prices` - Current stablecoin prices with deviation analysis

#### DEX Intelligence
- `get_dex_overview` - DEX volume overview across all chains
- `get_dex_chain_overview` - Chain-specific DEX data
- `get_dex_protocol_summary` - Protocol DEX summary

#### Advanced Analytics
- `find_arbitrage_opportunities` - Cross-chain arbitrage scanner
- `get_options_overview` - Options trading data
- `get_fees_overview` - Protocol fees analysis

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python defillama_mcp_server.py
```

## Configuration

### Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "defillama-comprehensive": {
      "command": "python",
      "args": ["/path/to/defillama/defillama_mcp_server.py"],
      "env": {}
    }
  }
}
```

### Environment Variables

The server supports optional environment configuration:
- `DEFILLAMA_CACHE_TTL` - Cache TTL in seconds (default: 300)
- `DEFILLAMA_REQUEST_DELAY` - Rate limiting delay (default: 0.1)
- `DEFILLAMA_TIMEOUT` - Request timeout (default: 30)

## Usage Examples

### Protocol Analysis

```python
# Get top protocols by TVL
get_protocols(sort_by="tvl", limit=10, min_tvl=100000000)

# Compare specific protocols
analyze_protocol_performance("uniswap,aave,compound", metrics="tvl,volume,fees")

# Get detailed protocol information
get_protocol_details("uniswap")
```

### Yield Optimization

```python
# Find yield opportunities with filters
get_yield_pools(
    min_apy=5.0,
    min_tvl=1000000,
    chains="ethereum,polygon,arbitrum",
    sort_by="apy",
    limit=20
)

# AI-powered yield strategy optimization
optimize_yield_strategy(
    capital_usd=50000,
    risk_tolerance="medium",
    min_apy=8.0,
    preferred_chains="ethereum,arbitrum"
)
```

### Price Analysis

```python
# Get current prices with metadata
get_current_prices("ethereum:0xA0b86a33E6,coingecko:bitcoin")

# Historical price analysis
get_historical_prices("2024-01-01", "WETH,USDC,WBTC")

# Price charts with statistics
get_price_chart("ethereum:0xA0b86a33E6", period="1d", span=100)
```

### Chain Analysis

```python
# Get all chains with TVL data
get_chains()

# Historical TVL for specific chain
get_chain_tvl_history("ethereum")

# Total DeFi TVL across all chains
get_all_chains_tvl()
```

### Stablecoin Monitoring

```python
# Get stablecoin market overview
get_stablecoins(sort_by="mcap", limit=20, include_prices=True)

# Monitor stablecoin prices and peg stability
get_stablecoin_prices()

# Circulation trends
get_stablecoin_charts(chain="ethereum")
```

## Advanced Filtering

All tools support comprehensive filtering options:

### Common Filters
- `sort_by` - Sort by any numeric field (tvl, apy, volume, price, etc.)
- `ascending` - Sort order (default: False for descending)
- `limit` - Maximum number of results
- `min_*` / `max_*` - Range filters for numeric fields

### Specific Filters
- `chains` - Filter by blockchain networks
- `protocols` - Filter by protocol names
- `symbols` - Filter by token symbols
- `categories` - Filter by protocol categories
- `min_tvl` - Minimum TVL threshold
- `min_apy` / `max_apy` - APY range filters

## AI Integration

### Prompts

The server includes AI-optimized prompts:

#### Portfolio Analysis
```python
analyze_defi_portfolio("WETH,USDC,AAVE,UNI", analysis_type="comprehensive")
```

#### Yield Optimization
```python
find_yield_opportunities(
    capital_usd=25000,
    risk_level="medium",
    min_apy=6.0,
    chains="ethereum,polygon,arbitrum"
)
```

### Response Formats

All responses are formatted for optimal AI consumption:
- Structured markdown output
- Consistent formatting across tools
- Rich metadata and context
- Statistical summaries where relevant
- Clear data hierarchies

## Performance Features

### Intelligent Caching
- 5-minute default cache TTL
- Automatic cache invalidation
- Memory-efficient storage
- Hit rate optimization

### Rate Limiting
- Built-in request delays
- Respectful API usage
- Automatic retry logic
- Error recovery

### Error Handling
- Descriptive error messages
- Graceful degradation
- Input validation
- API fallback handling

## API Coverage

The server provides access to all major DefiLlama APIs:

### TVL APIs
- `/protocols` - All protocol data
- `/protocol/{protocol}` - Specific protocol details
- `/tvl/{protocol}` - Protocol TVL
- `/v2/chains` - Chain data
- `/v2/historicalChainTvl` - Historical chain TVL

### Price APIs
- `/prices/current/{coins}` - Current prices
- `/prices/historical/{timestamp}/{coins}` - Historical prices
- `/batchHistorical` - Batch historical data
- `/chart/{coins}` - Price charts
- `/percentage/{coins}` - Price changes
- `/prices/first/{coins}` - First prices

### Yield APIs
- `/pools` - All yield pools
- `/chart/{pool}` - Pool historical data

### Stablecoin APIs
- `/stablecoins` - Stablecoin data
- `/stablecoincharts/all` - All stablecoin charts
- `/stablecoincharts/{chain}` - Chain-specific charts
- `/stablecoin/{asset}` - Specific stablecoin
- `/stablecoinprices` - Current prices

### DEX APIs
- `/overview/dexs` - DEX overview
- `/overview/dexs/{chain}` - Chain DEX data
- `/summary/dexs/{protocol}` - Protocol summary

### Additional APIs
- `/overview/options` - Options data
- `/overview/fees` - Fee data
- `/block/{chain}/{timestamp}` - Block info

## Development

### Project Structure
```
defillama/
├── defillama_mcp_server.py    # Main server implementation
├── requirements.txt           # Python dependencies
├── README.md                 # Documentation
├── ProjectSpec.md            # Product requirements
└── APISpec.json             # API specification
```

### Code Organization
- **Base Infrastructure**: HTTP client, caching, error handling
- **Data Processing**: Formatting, filtering, sorting utilities
- **Tool Categories**: Protocol, Price, Chain, Yield, Stablecoin, DEX
- **Advanced Analytics**: AI-powered analysis tools
- **Resources & Prompts**: AI integration helpers

### Type Safety
Full type annotations for:
- Function parameters and return types
- API response structures
- Internal data structures
- Error handling

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
   ```bash
   pip install -r requirements.txt
   ```

2. **API Rate Limits**: The server includes built-in rate limiting
   - Adjust `REQUEST_DELAY` if needed
   - Check API status at status.defillama.com

3. **Cache Issues**: Clear cache if data seems stale
   - Restart the server to clear memory cache
   - Adjust `CACHE_TTL` for different caching behavior

4. **Network Errors**: Check internet connectivity
   - The server includes automatic retry logic
   - Error messages include specific failure details

### Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

1. Follow the existing code structure
2. Add type annotations for all new functions
3. Include comprehensive error handling
4. Update documentation for new features
5. Test with various filter combinations

## License

This project is released under the MIT License. See the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Test with simpler queries first
4. Check DefiLlama API status

## Changelog

### v2.0.0 - Comprehensive Edition
- Complete API coverage for all DefiLlama endpoints
- Advanced filtering and sorting for all tools
- AI-optimized response formats
- Intelligent caching system
- Enhanced error handling
- Type safety improvements
- Performance optimizations

### v1.0.0 - Initial Release
- Basic protocol and price tools
- Simple yield pool access
- Basic error handling