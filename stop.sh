#!/bin/bash
echo "🛑 Stopping DeepCore Services..."

lsof -ti :8000 | xargs kill -9 2>/dev/null
lsof -ti :5173 | xargs kill -9 2>/dev/null

echo "✅ DeepCore services stopped."
