#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip3 install --upgrade pip

# Install requirements
pip3 install -r requirements.txt


echo "Setup complete! Virtual environment is activated."
