#!/bin/bash
# LLM CLI Agent Setup Script

echo "🧠 Setting up LLM CLI Agent..."

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "🐍 Python version: $python_version"

if (( $(echo "$python_version < 3.8" | bc -l) )); then
    echo "❌ Python 3.8+ required"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install aiohttp

# Check for OpenAI package (optional)
if pip3 show openai > /dev/null 2>&1; then
    echo "✅ OpenAI package already installed"
else
    echo "💡 Optional: Install OpenAI package with 'pip3 install openai'"
fi

# Make scripts executable
chmod +x start_agent.py

echo "✅ Setup complete!"
echo ""
echo "🚀 Quick start:"
echo "1. Set your API key: export OPENAI_API_KEY='your-key'"
echo "2. Start MCP server: cd ../mcp-server && python3 server_sse.py"
echo "3. Start agent: python3 start_agent.py"
echo ""
echo "📚 See README.md for full documentation"
