#!/usr/bin/env python3
"""
Smithery-compatible MCP server using Streamable HTTP transport.
Implements proper MCP protocol over HTTP as required by Smithery.
"""
import asyncio
import json
import os
import uuid
from typing import Dict, Any
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse
import uvicorn
from defillama import mcp

# Static tool definitions for lazy loading without full MCP initialization
STATIC_TOOLS = [
    {
        "name": "get_protocols",
        "description": "Retrieve a list of all DeFi protocols from DeFi Llama, limited to the first 20 results",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_protocol_tvl", 
        "description": "Get Total Value Locked (TVL) information for a specific DeFi protocol",
        "inputSchema": {
            "type": "object",
            "properties": {
                "protocol": {
                    "type": "string",
                    "description": "Protocol name (e.g., 'aave', 'uniswap')"
                }
            },
            "required": ["protocol"]
        }
    },
    {
        "name": "get_chain_tvl",
        "description": "Retrieve historical Total Value Locked (TVL) data for a specific blockchain", 
        "inputSchema": {
            "type": "object",
            "properties": {
                "chain": {
                    "type": "string",
                    "description": "Chain name (e.g., 'ethereum', 'bsc')"
                }
            },
            "required": ["chain"]
        }
    },
    {
        "name": "get_token_prices",
        "description": "Get current price information for a specific token",
        "inputSchema": {
            "type": "object", 
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Token identifier (e.g., 'ethereum:0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2')"
                }
            },
            "required": ["token"]
        }
    },
    {
        "name": "get_pools",
        "description": "Retrieve a list of all liquidity pools from DeFi Llama, limited to the first 30 results",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_pool_tvl",
        "description": "Get detailed information about a specific liquidity pool by its ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pool": {
                    "type": "string", 
                    "description": "Pool ID (e.g., '747c1d2a-c668-4682-b9f9-296708a3dd90')"
                }
            },
            "required": ["pool"]
        }
    },
    {
        "name": "get_pools_enriched",
        "description": "Get enriched pools data with predictions and additional metadata",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_pool_chart",
        "description": "Get historical APY and TVL data for a specific pool",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pool": {
                    "type": "string",
                    "description": "Pool ID"
                }
            },
            "required": ["pool"]
        }
    },
    {
        "name": "get_multiple_token_prices",
        "description": "Get current prices for multiple tokens at once",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tokens": {
                    "type": "string",
                    "description": "Comma-separated list of token identifiers"
                }
            },
            "required": ["tokens"]
        }
    },
    {
        "name": "get_token_price_history",
        "description": "Get historical prices for a token over time",
        "inputSchema": {
            "type": "object",
            "properties": {
                "token": {
                    "type": "string", 
                    "description": "Token identifier"
                },
                "span": {
                    "type": "integer",
                    "description": "Number of days of history (default: 30, max: 365)",
                    "default": 30
                }
            },
            "required": ["token"]
        }
    },
    {
        "name": "get_all_chains_tvl",
        "description": "Get TVL data for all chains",
        "inputSchema": {
            "type": "object", 
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_protocol_details",
        "description": "Get detailed information about a specific protocol including all metadata",
        "inputSchema": {
            "type": "object",
            "properties": {
                "protocol": {
                    "type": "string",
                    "description": "Protocol slug/name"
                }
            },
            "required": ["protocol"]
        }
    },
    {
        "name": "get_top_protocols",
        "description": "Get top protocols by TVL with optional category filtering",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Optional category filter (e.g., 'DEXes', 'Lending', 'Liquid Staking')",
                    "default": ""
                }
            },
            "required": []
        }
    },
    {
        "name": "search_protocols",
        "description": "Search for protocols by name or symbol", 
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term (protocol name, symbol, or partial match)"
                }
            },
            "required": ["query"]
        }
    }
]

app = FastAPI(title="DeFi Llama MCP Server")

# Store active MCP sessions
sessions: Dict[str, Any] = {}

@app.get("/mcp")
@app.post("/mcp") 
@app.delete("/mcp")
async def mcp_endpoint(request: Request):
    """
    Streamable HTTP endpoint for MCP protocol as required by Smithery.
    Handles GET, POST, and DELETE methods with configuration via query parameters.
    """
    try:
        # Parse configuration from query parameters (Smithery uses dot-notation)
        query_params = dict(request.query_params)
        
        # Handle different HTTP methods
        if request.method == "GET":
            # Return server capabilities and tool list for discovery using static definitions
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": "discovery",
                "result": {
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"listChanged": False},
                        "prompts": {"listChanged": False}
                    },
                    "serverInfo": {
                        "name": "defillama_mcp",
                        "version": "1.0.0"
                    },
                    "tools": STATIC_TOOLS
                }
            })
        
        elif request.method == "POST":
            # Handle JSON-RPC requests
            try:
                body = await request.json()
            except:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                })
            
            if body.get("method") == "initialize":
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "result": {
                        "protocolVersion": "1.0.0",
                        "capabilities": {
                            "tools": {"listChanged": False},
                            "resources": {"listChanged": False},
                            "prompts": {"listChanged": False}
                        },
                        "serverInfo": {
                            "name": "defillama_mcp",
                            "version": "1.0.0"
                        }
                    }
                })
            
            elif body.get("method") == "tools/list":
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "result": {"tools": STATIC_TOOLS}
                })
            
            elif body.get("method") == "tools/call":
                tool_name = body.get("params", {}).get("name")
                tool_args = body.get("params", {}).get("arguments", {})
                
                try:
                    result = await mcp.call_tool(tool_name, tool_args)
                    
                    # Handle the result properly
                    if hasattr(result, 'content') and result.content:
                        content_items = []
                        for item in result.content:
                            if hasattr(item, 'text'):
                                content_items.append({
                                    "type": "text",
                                    "text": item.text
                                })
                            else:
                                content_items.append({
                                    "type": "text", 
                                    "text": str(item)
                                })
                        result_data = {"content": content_items}
                    elif hasattr(result, 'model_dump'):
                        result_data = result.model_dump()
                    else:
                        result_data = {
                            "content": [
                                {
                                    "type": "text",
                                    "text": str(result)
                                }
                            ]
                        }
                    
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": result_data
                    })
                except Exception as e:
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "error": {
                            "code": -32603,
                            "message": f"Tool execution failed: {str(e)}"
                        }
                    })
            
            else:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {body.get('method')}"
                    }
                })
        
        elif request.method == "DELETE":
            # Handle cleanup/reset requests
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": "cleanup",
                "result": {"status": "ok", "message": "Cleanup completed"}
            })
        
        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32601,
                    "message": f"Method {request.method} not supported"
                }
            })
            
    except Exception as e:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        })

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "server": "defillama_mcp"}

if __name__ == "__main__":
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8090"))
    
    print("🚀 Starting DeFi Llama MCP Server for Smithery...")
    print(f"📡 Server will be available at http://{HOST}:{PORT}")
    print("🔧 Smithery endpoint: /mcp")
    print("💰 Available tools: 14 DeFi functions")
    
    uvicorn.run(app, host=HOST, port=PORT)