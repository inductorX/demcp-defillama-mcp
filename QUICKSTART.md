# 🚀 DefiLlama MCP Server - Quick Start Guide

Get up and running with the DefiLlama MCP Server in under 5 minutes!

## 📦 Installation

### Method 1: Direct Setup (Recommended)

```bash
# 1. Clone or download the repository
git clone https://github.com/bhanusanghi/Defillama-mcp.git
cd defillama

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Test the server
python test_server.py
```

### Method 2: Package Installation

```bash
# Install as a Python package
pip install -e .

# Run using console command
defillama-mcp
```

## 🖥️ Claude Desktop Integration

### Step 1: Find Your Configuration File

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### Step 2: Add DefiLlama Server

Replace `/absolute/path/to/` with your actual path:

```json
{
  "mcpServers": {
    "defillama": {
      "command": "python",
      "args": ["/absolute/path/to/defillama_mcp_server.py"]
    }
  }
}
```

### Step 3: Restart Claude Desktop

Completely quit and restart Claude Desktop. You should see the DefiLlama tools appear in the tools menu.

## 🎯 Quick Test

Once integrated with Claude Desktop, try these example queries:

### Token Prices
```
"What's the current price of WETH and USDC?"
```

### Historical Data
```
"What was the price of ETH on January 1st, 2024?"
```

### Yield Farming
```
"Show me yield farming pools with over $10 million TVL"
```

### DeFi Analysis
```
"Find the best yield opportunities for stablecoins"
```

## 🔧 Troubleshooting

### Server Not Appearing in Claude Desktop

1. **Check file path**: Ensure you're using the absolute path
2. **Verify JSON syntax**: Use a JSON validator
3. **Restart Claude**: Completely quit and restart the application
4. **Check logs**: Look at `~/Library/Logs/Claude/mcp*.log`

### Tool Calls Failing

1. **Test server directly**: Run `python test_server.py`
2. **Check internet connection**: APIs require network access
3. **Verify dependencies**: Run `pip install -r requirements.txt`

### Common Errors

- **"Server not found"**: Check the absolute path in config
- **"Module not found"**: Activate virtual environment first
- **"API timeout"**: Check internet connection and try again

## 🎉 Success Indicators

You'll know it's working when:

- ✅ Test script passes all checks
- ✅ Claude Desktop shows DefiLlama in tools menu
- ✅ Price queries return current market data
- ✅ Yield pool queries show farming opportunities

## 📚 Next Steps

1. **Explore Tools**: Try all 4 available tools
2. **Use Resources**: Access blockchain and API information
3. **Try Prompts**: Use AI-assisted DeFi analysis
4. **Customize**: Add your own DefiLlama endpoints

## 🆘 Need Help?

- **Check logs**: `~/Library/Logs/Claude/mcp*.log`
- **Run tests**: `python test_server.py`
- **Verify setup**: `python defillama_mcp_server.py --help`

---

**You're now ready to analyze DeFi data with AI! 🚀**