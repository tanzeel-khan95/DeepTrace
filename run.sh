#!/usr/bin/env bash
# DeepTrace — run commands inside the project venv.
# Usage: ./run.sh <command>   e.g.  ./run.sh pytest tests/
# Or:    ./run.sh python main.py --target "Timothy Overturf"

set -e
cd "$(dirname "$0")"

if [[ ! -d venv ]]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

source venv/bin/activate

if [[ $# -eq 0 ]]; then
  echo "Usage: ./run.sh <command> [args...]"
  echo "Examples:"
  echo "  ./run.sh pip install -r requirements.txt"
  echo "  ./run.sh pytest tests/ -v"
  echo "  ./run.sh python main.py --target \"Timothy Overturf\""
  echo "  ./run.sh python main.py --test-connections"
  echo "  ./run.sh streamlit run frontend/app.py"
  exit 0
fi

exec "$@"
