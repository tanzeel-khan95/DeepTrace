# DeepTrace — Autonomous AI Research Agent

> Elile AI Technical Assessment 

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
| Phase 1 | ✅ Complete | Full mock scaffold — LangGraph pipeline, Pydantic schemas, Streamlit UI, Neo4j integration (LLMs/APIs mocked) |
| Phase 2 | ✅ Current | Complete end-to-end execution with **Claude Haiku 4.5** for the main flow (agents); **persona evaluation remains mocked** |
| Phase 3 | ⏳ Next | LangSmith evaluation + caching + staged model mix with spending caps |
| Phase 4 | ⏳ Planned | Production hardening + demo polish |

## Phase 2 notes

- **Mock toggle**: set `USE_MOCK=false` in `.env` to use real Claude Haiku 4.5 flow (requires `ANTHROPIC_API_KEY`). Keep `USE_MOCK=true` for Phase 1 mock runs.
- **Neo4j**: still the only required external service for graph writes/visualisation.

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
