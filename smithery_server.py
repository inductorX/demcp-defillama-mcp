#!/usr/bin/env python3
"""
Smithery-compatible HTTP wrapper for the DeFi Llama MCP server.
This provides the JSON-RPC over HTTP interface that Smithery expects.
"""
import asyncio
import json
import os
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import uvicorn
from defillama import mcp

app = FastAPI(title="DeFi Llama MCP Server")

# Store for managing MCP sessions
sessions = {}

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """JSON-RPC over HTTP endpoint for MCP protocol"""
    try:
        body = await request.json()
        
        # This is a simplified bridge - in a real implementation you'd need
        # to properly handle the MCP protocol over HTTP
        # For now, just return a basic response to show the endpoint exists
        
        if body.get("method") == "initialize":
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "protocolVersion": "1.0.0",
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"listChanged": False, "subscribe": False},
                        "prompts": {"listChanged": False}
                    },
                    "serverInfo": {
                        "name": "defillama_mcp",
                        "version": "1.0.0"
                    }
                }
            })
        
        elif body.get("method") == "tools/list":
            # Get the tools from the MCP server
            tools = []
            for tool_name, tool_func in mcp._tools.items():
                tools.append({
                    "name": tool_name,
                    "description": tool_func.description or f"Tool: {tool_name}",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                })
            
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {"tools": tools}
            })
        
        elif body.get("method") == "tools/call":
            tool_name = body.get("params", {}).get("name")
            tool_args = body.get("params", {}).get("arguments", {})
            
            if tool_name in mcp._tools:
                try:
                    result = await mcp._tools[tool_name](**tool_args)
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(result, indent=2)
                                }
                            ]
                        }
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
                        "message": f"Tool not found: {tool_name}"
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
            
    except Exception as e:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": body.get("id") if hasattr(body, 'get') else None,
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
    
    uvicorn.run(app, host=HOST, port=PORT)