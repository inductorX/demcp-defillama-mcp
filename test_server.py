#!/usr/bin/env python3
"""
Minimal MCP server for testing Smithery connectivity
"""
import json
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Test MCP Server")

# Minimal tool for testing
TEST_TOOLS = [
    {
        "name": "test_tool",
        "title": "Test Tool",
        "description": "A simple test tool",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

@app.get("/")
async def root():
    return {"status": "ok", "server": "test_mcp"}

@app.get("/mcp")
async def mcp_get():
    return JSONResponse({
        "jsonrpc": "2.0",
        "id": "discovery",
        "result": {
            "capabilities": {
                "tools": {"listChanged": False}
            },
            "serverInfo": {
                "name": "test_mcp",
                "version": "1.0.0"
            },
            "tools": TEST_TOOLS
        }
    })

@app.post("/mcp")
async def mcp_post(request: Request):
    print(f"🔍 MCP POST: {request.url}")
    
    try:
        body = await request.json()
        print(f"🔍 Body: {body}")
    except:
        body = {}
    
    if body.get("method") == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "tools": TEST_TOOLS
            }
        })
    
    return JSONResponse({
        "jsonrpc": "2.0",
        "id": body.get("id"),
        "error": {
            "code": -32601,
            "message": f"Method not found: {body.get('method')}"
        }
    })

if __name__ == "__main__":
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8090"))
    
    print("🚀 Starting Test MCP Server...")
    print(f"📡 Server at http://{HOST}:{PORT}")
    
    uvicorn.run(app, host=HOST, port=PORT)