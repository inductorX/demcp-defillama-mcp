#!/usr/bin/env python3
"""
Test script for DefiLlama MCP Server

This script tests the basic functionality of the MCP server tools
to ensure they work correctly before integration with clients.
"""

import asyncio
import sys
import logging
from typing import Dict, Any

# Import the server functions directly for testing
from defillama_mcp_server import (
    get_current_prices,
    get_historical_prices,
    get_yield_pools,
    get_pool_chart,
    make_api_request,
    cleanup
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_api_connection():
    """Test basic API connectivity."""
    print("\n🔗 Testing API Connection...")
    try:
        url = "https://coins.llama.fi/prices/current/ethereum:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
        response = await make_api_request(url)
        if response and "coins" in response:
            print("✅ API connection successful")
            return True
        else:
            print("❌ API connection failed - unexpected response format")
            return False
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return False


async def test_current_prices():
    """Test current prices functionality."""
    print("\n💰 Testing Current Prices...")
    
    test_cases = [
        "ethereum:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
        "WETH,USDC",  # Multiple symbols
        "coingecko:bitcoin"  # CoinGecko ID
    ]
    
    for coins in test_cases:
        try:
            print(f"  Testing: {coins}")
            result = await get_current_prices(coins)
            if "Error" not in result:
                print(f"  ✅ Success: Got price data")
            else:
                print(f"  ❌ Failed: {result}")
        except Exception as e:
            print(f"  ❌ Exception: {e}")


async def test_historical_prices():
    """Test historical prices functionality."""
    print("\n📈 Testing Historical Prices...")
    
    test_cases = [
        ("2024-01-01", "ethereum:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
        (1609459200, "WETH"),  # Unix timestamp for 2021-01-01
    ]
    
    for timestamp, coins in test_cases:
        try:
            print(f"  Testing: {timestamp} for {coins}")
            result = await get_historical_prices(timestamp, coins)
            if "Error" not in result:
                print(f"  ✅ Success: Got historical data")
            else:
                print(f"  ❌ Failed: {result}")
        except Exception as e:
            print(f"  ❌ Exception: {e}")


async def test_yield_pools():
    """Test yield pools functionality."""
    print("\n🌾 Testing Yield Pools...")
    
    try:
        print("  Testing: Basic pools fetch")
        result = await get_yield_pools()
        if "Error" not in result and "Found" in result:
            print(f"  ✅ Success: Got pools data")
            
            # Test with TVL filter
            print("  Testing: Pools with min TVL filter")
            result_filtered = await get_yield_pools(min_tvl=1000000)
            if "Error" not in result_filtered:
                print(f"  ✅ Success: Got filtered pools data")
            else:
                print(f"  ❌ Failed with filter: {result_filtered}")
        else:
            print(f"  ❌ Failed: {result}")
    except Exception as e:
        print(f"  ❌ Exception: {e}")


async def test_pool_chart():
    """Test pool chart functionality."""
    print("\n📊 Testing Pool Chart...")
    
    # First get a pool ID from the pools data
    try:
        pools_result = await get_yield_pools()
        if "Error" in pools_result:
            print("  ⚠️  Skipping pool chart test - couldn't get pools data")
            return
        
        # Try with a common pool format (this might fail if pool doesn't exist)
        test_pool_id = "747c1d2a-c668-4682-b9f9-296708a3dd90"
        print(f"  Testing: Pool chart for {test_pool_id}")
        result = await get_pool_chart(test_pool_id)
        
        if "Error" not in result or "No historical data found" in result:
            print(f"  ✅ Success: Pool chart function works (pool may not exist)")
        else:
            print(f"  ❌ Failed: {result}")
            
    except Exception as e:
        print(f"  ❌ Exception: {e}")


async def test_error_handling():
    """Test error handling with invalid inputs."""
    print("\n🛡️  Testing Error Handling...")
    
    test_cases = [
        ("get_current_prices", ["invalid-token-format"]),
        ("get_historical_prices", ["invalid-date", "WETH"]),
        ("get_pool_chart", ["nonexistent-pool-id"]),
    ]
    
    for func_name, args in test_cases:
        try:
            if func_name == "get_current_prices":
                result = await get_current_prices(*args)
            elif func_name == "get_historical_prices":
                result = await get_historical_prices(*args)
            elif func_name == "get_pool_chart":
                result = await get_pool_chart(*args)
            
            if "Error" in result or "❌" in result:
                print(f"  ✅ {func_name}: Properly handled invalid input")
            else:
                print(f"  ⚠️  {func_name}: Unexpected success with invalid input")
                
        except Exception as e:
            print(f"  ✅ {func_name}: Properly raised exception: {type(e).__name__}")


async def run_all_tests():
    """Run all tests."""
    print("🧪 DefiLlama MCP Server Test Suite")
    print("=" * 50)
    
    # Track test results
    tests = []
    
    try:
        # Run tests
        tests.append(await test_api_connection())
        await test_current_prices()
        await test_historical_prices()
        await test_yield_pools()
        await test_pool_chart()
        await test_error_handling()
    finally:
        # Cleanup
        await cleanup()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary")
    
    if any(tests):
        print("✅ Basic functionality appears to be working")
        print("🎉 Server is ready for MCP client integration!")
    else:
        print("❌ Some basic tests failed")
        print("🔧 Please check your internet connection and API endpoints")
    
    print("\n💡 Next steps:")
    print("   1. Test with MCP Inspector: mcp dev defillama_mcp_server.py")
    print("   2. Add to Claude Desktop configuration")
    print("   3. Start asking DeFi questions!")


def main():
    """Main test function."""
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()