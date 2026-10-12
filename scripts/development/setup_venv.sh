#!/usr/bin/env bash
set -e

echo "Setting up canonical Python virtual environment (.venv)..."
python3 -m venv .venv

source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements-dev.txt
pip install -e .

echo "Virtual environment setup complete!"
