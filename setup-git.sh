#!/bin/bash
# Setup Git configuration for this repository only
# This won't affect your global Git settings

set -e

echo "Setting up Git configuration for C2Nv2 repository..."
echo ""

# Prompt for email if not provided
read -p "Enter your email for karst10607 account: " EMAIL

if [ -z "$EMAIL" ]; then
    echo "Error: Email is required"
    exit 1
fi

# Set local Git config (only for this repo)
git config --local user.name "karst10607"
git config --local user.email "$EMAIL"
git config --local commit.gpgsign false

echo ""
echo "✓ Git configuration set for this repository:"
echo "  Name:  $(git config --local user.name)"
echo "  Email: $(git config --local user.email)"
echo "  GPG Signing: $(git config --local commit.gpgsign)"
echo ""
echo "✓ Your global Git settings remain unchanged:"
echo "  Global Name:  $(git config --global user.name)"
echo "  Global Email: $(git config --global user.email)"
echo ""
echo "You can now commit and push with the karst10607 account!"
echo "Run: git add -A && git commit -m 'your message' && git push origin main --tags"
