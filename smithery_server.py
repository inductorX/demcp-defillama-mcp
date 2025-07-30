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
            # Get the tools from the MCP server using the proper API
            try:
                tools_list = await mcp.list_tools()
                # Convert Tool objects to dictionaries
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
                # Use the proper FastMCP call_tool method
                result = await mcp.call_tool(tool_name, tool_args)
                
                # Handle the result properly - call_tool returns a CallToolResult with content
                if hasattr(result, 'content') and result.content:
                    # It's a CallToolResult with content
                    content_items = []
                    for item in result.content:
                        if hasattr(item, 'text'):
                            # It's a TextContent
                            content_items.append({
                                "type": "text",
                                "text": item.text
                            })
                        else:
                            # Convert to string
                            content_items.append({
                                "type": "text", 
                                "text": str(item)
                            })
                    result_data = {"content": content_items}
                elif hasattr(result, 'model_dump'):
                    # It's a pydantic model
                    result_data = result.model_dump()
                else:
                    # It's something else, convert to text
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