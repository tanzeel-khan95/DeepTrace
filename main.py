"""
main.py — DeepTrace CLI entrypoint.

Usage:
  python main.py --target "Timothy Overturf" --context "CEO of Sisu Capital"
  python main.py --target "Test Person" --env dev
  python main.py --eval
  python main.py --test-connections
  python main.py --help

Architecture position: top-level CLI, imports pipeline.py and graph modules.
"""
import logging
import os
import sys
import click
from dotenv import load_dotenv
from utils.tracing import configure_langsmith

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("deeptrace")


@click.command()
@click.option("--target",  "-t", default="Timothy Overturf", help="Full name of research target")
@click.option("--context", "-c", default="CEO of Sisu Capital", help="Optional context about target")
@click.option("--env",           default=None,  help="Override ENV (dev/staging/prod)")
@click.option("--eval", "run_eval", is_flag=True,  help="Run full evaluation set instead of single target")
@click.option("--test-connections", is_flag=True, help="Test all external connections and exit")
@click.option("--stream",        is_flag=True,  help="Show streaming agent output")
def main(target, context, env, run_eval, test_connections, stream):
    """DeepTrace — Autonomous AI Research Agent."""
    from rich.console import Console
    from rich.panel   import Panel
    console = Console()

    if env:
        os.environ["ENV"] = env

    # Configure LangSmith tracing (no-op if disabled or misconfigured)
    configure_langsmith()

    from config import ENV, USE_MOCK
    console.print(Panel(
        f"[bold cyan]DeepTrace[/bold cyan] — Deep Research AI Agent\n"
        f"ENV: [yellow]{ENV}[/yellow] | USE_MOCK: [yellow]{USE_MOCK}[/yellow]",
        border_style="cyan",
    ))

    # ── Connection test ────────────────────────────────────────────────────────
    if test_connections:
        from graph.neo4j_manager import test_connection
        neo4j_ok = test_connection()
        console.print(f"Neo4j: {'[green]OK[/green]' if neo4j_ok else '[red]FAILED[/red]'}")
        console.print("Anthropic / OpenAI / Google: [yellow]Skipped in Phase 1 (USE_MOCK=true)[/yellow]")
        sys.exit(0 if neo4j_ok else 1)

    # ── Evaluation run ─────────────────────────────────────────────────────────
    if run_eval:
        console.print("[bold]Running evaluation set (3 personas)...[/bold]")
        from evaluation.eval_personas import ALL_EVAL_PERSONAS
        from pipeline import run_pipeline
        for persona in ALL_EVAL_PERSONAS:
            console.print(f"\n→ Evaluating: [cyan]{persona['name']}[/cyan]")
            state = run_pipeline(persona["name"], persona["context"])
            facts_found = len(state.get("extracted_facts", []))
            flags_found = len(state.get("risk_flags", []))
            console.print(f"  Facts: {facts_found} | Flags: {flags_found} | "
                          f"Quality: {state.get('research_quality', 0):.2f}")
        console.print("\n[green]✅ Evaluation complete[/green]")
        return

    # ── Single target run ──────────────────────────────────────────────────────
    console.print(f"\n[bold]Researching:[/bold] [cyan]{target}[/cyan]")
    console.print(f"[dim]Context: {context}[/dim]\n")

    if stream:
        from pipeline import stream_pipeline
        for node_name, node_output in stream_pipeline(target, context):
            facts = len(node_output.get("extracted_facts", []))
            flags = len(node_output.get("risk_flags", []))
            console.print(f"  [{node_name}] facts+={facts} flags+={flags}")
    else:
        from pipeline import run_pipeline
        state = run_pipeline(target, context)
        facts_found = len(state.get("extracted_facts", []))
        flags_found = len(state.get("risk_flags", []))
        quality     = state.get("research_quality", 0)
        console.print(f"\n[green]✅ Complete[/green] | Facts: {facts_found} | "
                      f"Flags: {flags_found} | Quality: {quality:.2f}")
        if state.get("final_report"):
            console.print("\n[bold]Report Preview:[/bold]")
            console.print(state["final_report"][:500] + "...")


if __name__ == "__main__":
    main()
