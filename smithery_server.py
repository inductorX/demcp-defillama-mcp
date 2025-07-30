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
            # Return server capabilities and tool list for discovery
            try:
                tools_list = await mcp.list_tools()
                tools = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    } 
                    for tool in tools_list
                ]
                
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
                        "tools": tools
                    }
                })
            except Exception as e:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": "discovery",
                    "error": {
                        "code": -32603,
                        "message": f"Failed to get server info: {str(e)}"
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
                try:
                    tools_list = await mcp.list_tools()
                    tools = [tool.model_dump() for tool in tools_list]
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {"tools": tools}
                    })
                except Exception as e:
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "error": {
                            "code": -32603,
                            "message": f"Failed to list tools: {str(e)}"
                        }
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