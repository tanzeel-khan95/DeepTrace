# DeepTrace — Autonomous AI Research Agent

> Elile AI Technical Assessment · Phase 1 (Mock Scaffold)

## Quick Start

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
#  or: venv\Scripts\activate  # Windows

# 2. Copy environment file
cp .env.example .env

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Start Neo4j (optional for mock; required for graph writes)
docker compose up -d neo4j

# 5. Run smoke test
python main.py --test-connections

# 6. Run full pipeline (mock mode)
python main.py --target "Timothy Overturf" --context "CEO of Sisu Capital"

# 7. Launch Streamlit UI
streamlit run frontend/app.py

# 8. Run evaluation set
python main.py --eval
```

## Phase Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Current | Full mock scaffold — all structure, zero API cost |
| Phase 2 | ⏳ Next | Haiku integration — real LLMs, dev cost ~$10 |
| Phase 3 | ⏳ | Staging — real models, capped runs |
| Phase 4 | ⏳ | Production + demo polish |

## Virtual environment

Always activate the venv before running commands:

```bash
source venv/bin/activate   # Linux/macOS
# or: venv\Scripts\activate  # Windows
```

Or use the helper script (activates venv and runs any command):

```bash
./run.sh pytest tests/ -v
./run.sh python main.py --target "Timothy Overturf"
./run.sh python main.py --test-connections
./run.sh streamlit run frontend/app.py
```

## Key Commands

```bash
python main.py --help
python main.py --target "Name" --stream      # streaming output
python main.py --eval                         # run all 3 personas
python main.py --test-connections             # check Neo4j
pytest tests/                                  # run all tests
```
