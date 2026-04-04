#!/bin/bash
# install_railway.sh
# Script to install the Railway CLI dependency for automated log fetching

echo "Installing Railway CLI..."

# Check if npm is installed (required for the official railway/cli package)
if command -v npm &> /dev/null; then
    npm i -g @railway/cli
    echo "Railway CLI installed successfully via npm."
else
    echo "npm not found. Falling back to bash installer."
    bash <(curl -fsSL cli.new)
fi

echo ""
echo "Installation complete!"
echo "Make sure to add your RAILWAY_TOKEN to the .env file in the ai_engine directory."
echo "Format: RAILWAY_TOKEN=your_token_here"
