"""
report_exporter.py — Export pipeline reports to PDF.

Converts the final_report markdown string + risk flags + citations into
a styled HTML document, then uses weasyprint to render it as a PDF.

Architecture position: called from Streamlit frontend/pages/03_report.py.
"""
import logging
import os
import tempfile
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def export_report_pdf(
    target_name: str,
    final_report: str,
    risk_flags: list,
    citations: list,
    run_id: str,
) -> bytes:
    """
    Generate a PDF report from pipeline results.

    Returns:
        PDF as bytes (for Streamlit st.download_button)

    Raises:
        RuntimeError if weasyprint is not installed or PDF generation fails
    """
    try:
        from weasyprint import HTML as WeasyprintHTML
    except ImportError:
        raise RuntimeError(
            "weasyprint is required for PDF export. "
            "Install with: pip install weasyprint"
        )

    html_content = _build_pdf_html(target_name, final_report, risk_flags, citations, run_id)

    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False) as f:
        f.write(html_content)
        tmp_path = f.name

    try:
        pdf_bytes = WeasyprintHTML(filename=tmp_path).write_pdf()
        return pdf_bytes
    finally:
        os.unlink(tmp_path)


def _severity_color(severity: str) -> str:
    colors = {
        "CRITICAL": "#E74C3C",
        "HIGH": "#E8813A",
        "MEDIUM": "#F39C12",
        "LOW": "#50C878",
    }
    return colors.get(severity, "#7F8C8D")


def _build_pdf_html(target_name, final_report, risk_flags, citations, run_id) -> str:
    """Build styled HTML string for PDF rendering."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    try:
        import markdown
        report_html = markdown.markdown(final_report or "", extensions=["tables"])
    except ImportError:
        report_html = f"<pre>{final_report or ''}</pre>"

    flags_html = ""
    if risk_flags:
        rows = ""
        for flag in risk_flags:
            sev = flag.get("severity", "LOW") if isinstance(flag, dict) else getattr(flag, "severity", "LOW")
            title = flag.get("title", "") if isinstance(flag, dict) else getattr(flag, "title", "")
            desc = flag.get("description", "") if isinstance(flag, dict) else getattr(flag, "description", "")
            conf = flag.get("confidence", 0) if isinstance(flag, dict) else getattr(flag, "confidence", 0)
            color = _severity_color(sev)
            rows += f"""<tr>
              <td><span style="background:{color};color:white;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:bold">{sev}</span></td>
              <td style="font-weight:600">{title}</td>
              <td>{desc}</td>
              <td>{int(conf*100)}%</td>
            </tr>"""
        flags_html = f"""
        <h2>Risk Flags</h2>
        <table>
          <thead><tr><th>Severity</th><th>Title</th><th>Description</th><th>Confidence</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>"""

    citations_html = ""
    if citations:
        items = ""
        for c in citations[:20]:
            url = c.get("url", "") if isinstance(c, dict) else getattr(c, "url", "")
            title = c.get("title", url) if isinstance(c, dict) else getattr(c, "title", url)
            snip = c.get("snippet", "") if isinstance(c, dict) else getattr(c, "snippet", "")
            conf = c.get("confidence", 0) if isinstance(c, dict) else getattr(c, "confidence", 0)
            items += f"""<div class="citation">
              <a href="{url}">{title}</a>
              <div class="citation-snippet">{snip[:200]}</div>
              <div class="citation-meta">Source confidence: {int(conf*100)}% · <a href="{url}">{url[:60]}</a></div>
            </div>"""
        citations_html = f"<h2>Source References</h2>{items}"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #1A2D45; font-size: 12px; line-height: 1.6; }}
  h1 {{ color: #0D1B2A; font-size: 22px; border-bottom: 3px solid #4A90D9; padding-bottom: 8px; }}
  h2 {{ color: #0D1B2A; font-size: 16px; margin-top: 28px; border-bottom: 1px solid #DEE5ED; padding-bottom: 4px; }}
  h3 {{ color: #2A4A6A; font-size: 13px; }}
  .meta {{ color: #7A9AB5; font-size: 10px; margin-bottom: 24px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 11px; }}
  th {{ background: #1A2D45; color: white; padding: 8px 10px; text-align: left; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #DEE5ED; vertical-align: top; }}
  tr:nth-child(even) td {{ background: #F5F8FC; }}
  .citation {{ margin: 12px 0; padding: 10px; border-left: 3px solid #4A90D9; background: #F5F8FC; }}
  .citation a {{ color: #4A90D9; font-weight: 600; text-decoration: none; }}
  .citation-snippet {{ color: #4A6A8A; font-size: 10px; margin: 4px 0; }}
  .citation-meta {{ color: #7A9AB5; font-size: 10px; }}
  ul {{ padding-left: 20px; }}
  li {{ margin: 4px 0; }}
  p {{ margin: 8px 0; }}
  .page-break {{ page-break-before: always; }}
</style>
</head>
<body>
  <h1>DeepTrace Intelligence Report</h1>
  <div class="meta">
    Target: <strong>{target_name}</strong> ·
    Generated: {now} ·
    Run ID: {run_id}
  </div>

  {report_html}
  {flags_html}
  <div class="page-break"></div>
  {citations_html}
</body>
</html>"""
