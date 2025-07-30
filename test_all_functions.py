#!/usr/bin/env python3
"""
Comprehensive test of all DeFi Llama MCP functions
"""
import asyncio
import sys
import os

# Add current directory to path so we can import defillama
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_all_functions():
    """Test every single DeFi function in the MCP server"""
    
    print("🚀 Comprehensive DeFi Llama MCP Function Test")
    print("=" * 60)
    
    try:
        from defillama import (
            # Original 6 functions
            get_protocols,
            get_protocol_tvl,
            get_chain_tvl,
            get_token_prices,
            get_pools,
            get_pool_tvl,
            # New 8 functions
            get_pools_enriched,
            get_pool_chart,
            get_multiple_token_prices,
            get_token_price_history,
            get_all_chains_tvl,
            get_protocol_details,
            get_top_protocols,
            search_protocols
        )
        print("✅ Successfully imported all 14 DeFi functions")
    except ImportError as e:
        print(f"❌ Failed to import functions: {str(e)}")
        return

    test_results = []
    
    # Test 1: Original get_protocols
    print("\n" + "="*60)
    print("TESTING ORIGINAL 6 FUNCTIONS")
    print("="*60)
    
    print("\n🔄 Test 1: get_protocols()")
    try:
        protocols = await get_protocols()
        if isinstance(protocols, list) and len(protocols) > 0:
            first_protocol = protocols[0]
            name = first_protocol.get('name', 'Unknown')
            tvl = first_protocol.get('tvl', 0)
            print(f"✅ SUCCESS: Got {len(protocols)} protocols")
            print(f"   First: {name} - TVL: ${tvl:,.0f}")
            test_results.append(("get_protocols", True))
        else:
            print(f"❌ FAILED: {protocols}")
            test_results.append(("get_protocols", False))
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        test_results.append(("get_protocols", False))
    
    # Test 2: get_protocol_tvl
    print("\n🔄 Test 2: get_protocol_tvl('aave')")
    try:
        aave_tvl = await get_protocol_tvl("aave")
        if isinstance(aave_tvl, dict) and 'error' not in aave_tvl:
            chain_count = len(aave_tvl)
            print(f"✅ SUCCESS: Got Aave TVL across {chain_count} chains")
            # Show top 3 chains
            sorted_chains = sorted(aave_tvl.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0, reverse=True)[:3]
            for chain, tvl in sorted_chains:
                if isinstance(tvl, (int, float)):
                    print(f"   {chain}: ${tvl:,.0f}")
            test_results.append(("get_protocol_tvl", True))
        else:
            print(f"❌ FAILED: {aave_tvl}")
            test_results.append(("get_protocol_tvl", False))
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        test_results.append(("get_protocol_tvl", False))
    
    # Test 3: get_chain_tvl
    print("\n🔄 Test 3: get_chain_tvl('ethereum')")
    try:
        eth_tvl = await get_chain_tvl("ethereum")
        if isinstance(eth_tvl, list) and len(eth_tvl) > 0:
            latest = eth_tvl[-1] if isinstance(eth_tvl[-1], dict) else {}
            print(f"✅ SUCCESS: Got {len(eth_tvl)} historical data points")
            print(f"   Latest TVL: ${latest.get('tvl', 0):,.0f}")
            test_results.append(("get_chain_tvl", True))
        else:
            print(f"❌ FAILED: {eth_tvl}")
            test_results.append(("get_chain_tvl", False))
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        test_results.append(("get_chain_tvl", False))
    
    # Test 4: get_token_prices
    print("\n🔄 Test 4: get_token_prices('coingecko:ethereum')")
    try:
        eth_price = await get_token_prices("coingecko:ethereum")
        if isinstance(eth_price, dict) and 'coins' in eth_price:
            coins = eth_price["coins"]
            if "coingecko:ethereum" in coins:
                price_info = coins["coingecko:ethereum"]
                price = price_info.get("price", "N/A")
                symbol = price_info.get("symbol", "ETH")
                print(f"✅ SUCCESS: {symbol} Price: ${price}")
                test_results.append(("get_token_prices", True))
            else:
                print(f"❌ FAILED: No ETH price in response")
                test_results.append(("get_token_prices", False))
        else:
            print(f"❌ FAILED: {eth_price}")
            test_results.append(("get_token_prices", False))
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        test_results.append(("get_token_prices", False))
    
    # Test 5: get_pools
    print("\n🔄 Test 5: get_pools()")
    try:
        pools = await get_pools()
        if isinstance(pools, list) and len(pools) > 0:
            first_pool = pools[0]
            project = first_pool.get('project', 'Unknown')
            apy = first_pool.get('apy', 0)
            print(f"✅ SUCCESS: Got {len(pools)} pools")
            print(f"   First: {project} - APY: {apy:.2f}%")
            test_results.append(("get_pools", True))
        else:
            print(f"❌ FAILED: {pools}")
            test_results.append(("get_pools", False))
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        test_results.append(("get_pools", False))
    
    # Test 6: get_pool_tvl
    print("\n🔄 Test 6: get_pool_tvl('747c1d2a-c668-4682-b9f9-296708a3dd90')")
    try:
        pool_tvl = await get_pool_tvl("747c1d2a-c668-4682-b9f9-296708a3dd90")
        if isinstance(pool_tvl, list) and len(pool_tvl) > 0:
            print(f"✅ SUCCESS: Got {len(pool_tvl)} historical data points for pool")
            test_results.append(("get_pool_tvl", True))
        else:
            print(f"❌ FAILED: {pool_tvl}")
            test_results.append(("get_pool_tvl", False))
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        test_results.append(("get_pool_tvl", False))
    
    # Test NEW FUNCTIONS
    print("\n" + "="*60)
    print("TESTING NEW 8 FUNCTIONS")
    print("="*60)
    
    # Test 7: get_pools_enriched
    print("\n🔄 Test 7: get_pools_enriched()")
    try:
        enriched_pools = await get_pools_enriched()
        if isinstance(enriched_pools, dict) and 'pools' in enriched_pools:
            pool_list = enriched_pools['pools']
            print(f"✅ SUCCESS: Got {len(pool_list)} enriched pools")
            if pool_list:
                first_pool = pool_list[0]
                project = first_pool.get('project', 'Unknown')
                apy = first_pool.get('apy', 0)
                predictions = first_pool.get('predictions', {})
                pred_class = predictions.get('predictedClass', 'Unknown')
                print(f"   First: {project} - APY: {apy:.2f}% - Prediction: {pred_class}")
            test_results.append(("get_pools_enriched", True))
        else:
            print(f"❌ FAILED: {enriched_pools}")
            test_results.append(("get_pools_enriched", False))
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        test_results.append(("get_pools_enriched", False))
    
    # Test 8: get_pool_chart
    print("\n🔄 Test 8: get_pool_chart('747c1d2a-c668-4682-b9f9-296708a3dd90')")
    try:
        pool_chart = await get_pool_chart("747c1d2a-c668-4682-b9f9-296708a3dd90")
        if isinstance(pool_chart, dict) and 'historical_data' in pool_chart:
            data = pool_chart['historical_data']
            print(f"✅ SUCCESS: Got historical chart data with {len(data)} points")
            test_results.append(("get_pool_chart", True))
        else:
            print(f"❌ FAILED: {pool_chart}")
            test_results.append(("get_pool_chart", False))
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        test_results.append(("get_pool_chart", False))
    
    # Test 9: get_multiple_token_prices
    print("\n🔄 Test 9: get_multiple_token_prices('coingecko:ethereum,coingecko:bitcoin')")
    try:
        multi_prices = await get_multiple_token_prices('coingecko:ethereum,coingecko:bitcoin')
        if isinstance(multi_prices, dict) and 'coins' in multi_prices:
            coins = multi_prices['coins']
            print(f"✅ SUCCESS: Got prices for {len(coins)} tokens")
            for token_id, info in coins.items():
                symbol = info.get('symbol', token_id.split(':')[-1].upper())
                price = info.get('price', 'N/A')
                print(f"   {symbol}: ${price}")
            test_results.append(("get_multiple_token_prices", True))
        else:
            print(f"❌ FAILED: {multi_prices}")
            test_results.append(("get_multiple_token_prices", False))
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        test_results.append(("get_multiple_token_prices", False))
    
    # Test 10: get_token_price_history
    print("\n🔄 Test 10: get_token_price_history('coingecko:ethereum', 7)")
    try:
        price_history = await get_token_price_history('coingecko:ethereum', 7)
        if isinstance(price_history, dict) and 'coins' in price_history:
            print(f"✅ SUCCESS: Got 7-day price history for ETH")
            test_results.append(("get_token_price_history", True))
        elif 'error' not in price_history:
            print(f"✅ SUCCESS: Got price history data")
            test_results.append(("get_token_price_history", True))
        else:
            print(f"❌ FAILED: {price_history}")
            test_results.append(("get_token_price_history", False))
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        test_results.append(("get_token_price_history", False))
    
    # Test 11: get_all_chains_tvl
    print("\n🔄 Test 11: get_all_chains_tvl()")
    try:
        all_chains = await get_all_chains_tvl()
        if isinstance(all_chains, list) and len(all_chains) > 0:
            print(f"✅ SUCCESS: Got TVL data for {len(all_chains)} chains")
            for i, chain in enumerate(all_chains[:3]):
                name = chain.get('name', 'Unknown')
                tvl = chain.get('tvl', 0)
                print(f"   {i+1}. {name}: ${tvl:,.0f}")
            test_results.append(("get_all_chains_tvl", True))
        else:
            print(f"❌ FAILED: {all_chains}")
            test_results.append(("get_all_chains_tvl", False))
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        test_results.append(("get_all_chains_tvl", False))
    
    # Test 12: get_protocol_details
    print("\n🔄 Test 12: get_protocol_details('uniswap')")
    try:
        protocol_details = await get_protocol_details('uniswap')
        if isinstance(protocol_details, dict) and 'name' in protocol_details:
            name = protocol_details.get('name', 'Unknown')
            tvl = protocol_details.get('tvl', 0)
            chains = protocol_details.get('chains', [])
            print(f"✅ SUCCESS: Got details for {name}")
            print(f"   TVL: ${tvl:,.0f} across {len(chains) if isinstance(chains, list) else 0} chains")
            test_results.append(("get_protocol_details", True))
        else:
            print(f"❌ FAILED: {protocol_details}")
            test_results.append(("get_protocol_details", False))
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        test_results.append(("get_protocol_details", False))
    
    # Test 13: get_top_protocols
    print("\n🔄 Test 13: get_top_protocols('Lending')")
    try:
        top_lending = await get_top_protocols('Lending')
        if isinstance(top_lending, dict) and 'protocols' in top_lending:
            protocols = top_lending['protocols']
            category = top_lending.get('category', 'Unknown')
            print(f"✅ SUCCESS: Got {len(protocols)} top {category} protocols")
            for i, protocol in enumerate(protocols[:3]):
                name = protocol.get('name', 'Unknown')
                tvl = protocol.get('tvl', 0)
                print(f"   {i+1}. {name}: ${tvl:,.0f}")
            test_results.append(("get_top_protocols", True))
        else:
            print(f"❌ FAILED: {top_lending}")
            test_results.append(("get_top_protocols", False))
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        test_results.append(("get_top_protocols", False))
    
    # Test 14: search_protocols
    print("\n🔄 Test 14: search_protocols('uniswap')")
    try:
        search_result = await search_protocols('uniswap')
        if isinstance(search_result, dict) and 'protocols' in search_result:
            matches = search_result.get('matches', 0)
            protocols = search_result['protocols']
            query = search_result.get('query', 'uniswap')
            print(f"✅ SUCCESS: Found {matches} protocols matching '{query}'")
            for i, protocol in enumerate(protocols[:3]):
                name = protocol.get('name', 'Unknown')
                category = protocol.get('category', 'Unknown')
                tvl = protocol.get('tvl', 0)
                print(f"   {i+1}. {name} ({category}) - ${tvl:,.0f}")
            test_results.append(("search_protocols", True))
        else:
            print(f"❌ FAILED: {search_result}")
            test_results.append(("search_protocols", False))
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        test_results.append(("search_protocols", False))
    
    # SUMMARY
    print("\n" + "="*60)
    print("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
    print("="*60)
    
    passed_tests = [result for result in test_results if result[1]]
    failed_tests = [result for result in test_results if not result[1]]
    
    print(f"\n✅ PASSED: {len(passed_tests)}/{len(test_results)} tests")
    print(f"❌ FAILED: {len(failed_tests)}/{len(test_results)} tests")
    
    if passed_tests:
        print(f"\n🎉 SUCCESSFUL FUNCTIONS:")
        for func_name, _ in passed_tests:
            print(f"   ✅ {func_name}")
    
    if failed_tests:
        print(f"\n⚠️  FAILED FUNCTIONS:")
        for func_name, _ in failed_tests:
            print(f"   ❌ {func_name}")
    
    success_rate = (len(passed_tests) / len(test_results)) * 100
    print(f"\n📈 SUCCESS RATE: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("\n🚀 EXCELLENT! Your MCP server is ready for production!")
    elif success_rate >= 75:
        print("\n👍 GOOD! Most functions working, minor issues to address")
    else:
        print("\n⚠️  NEEDS WORK: Several functions need attention")
    
    print("\n🎯 Your DeFi Llama MCP server provides comprehensive access to:")
    print("• Protocol TVL data across all major DeFi protocols")
    print("• Real-time and historical token pricing")
    print("• Yield farming pool data with APY predictions")
    print("• Cross-chain TVL analytics")
    print("• Protocol search and discovery")
    print("• Enriched metadata and risk assessments")

if __name__ == "__main__":
    asyncio.run(test_all_functions())