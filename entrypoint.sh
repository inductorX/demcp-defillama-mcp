#!/bin/bash

# Entrypoint script for DefiLlama MCP Server
# Handles graceful shutdown and signal forwarding

set -e

# Function to handle shutdown
shutdown() {
    echo "🛑 Received shutdown signal, cleaning up..."
    if [ ! -z "$MCP_PID" ]; then
        kill -TERM "$MCP_PID" 2>/dev/null || true
        wait "$MCP_PID" 2>/dev/null || true
    fi
    echo "✅ Cleanup completed"
    exit 0
}

# Trap signals
trap shutdown SIGTERM SIGINT

echo "🚀 Starting DefiLlama MCP Server..."
echo "📊 Environment: ${ENVIRONMENT:-production}"
echo "⚙️ Cache TTL: ${DEFILLAMA_CACHE_TTL:-300}s"
echo "⏱️ Request Delay: ${DEFILLAMA_REQUEST_DELAY:-0.1}s"
echo "⏰ Timeout: ${DEFILLAMA_TIMEOUT:-30}s"

# Start the MCP server in background
python -u defillama_mcp_server.py &
MCP_PID=$!

echo "✅ MCP Server started with PID: $MCP_PID"

# Wait for the process
wait "$MCP_PID"

echo "🛑 MCP Server stopped"