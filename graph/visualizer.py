"""
visualizer.py — Convert Neo4j graph data to pyvis interactive HTML.

Generates a self-contained HTML file that renders in Streamlit via
st.components.v1.html(). Node colours match the SRS design tokens.

Architecture position: called by graph_builder agent and Streamlit page 02.
"""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# Node colours from SRS design tokens
NODE_COLORS: Dict[str, str] = {
    "Person":       "#2471A3",
    "Organization": "#1E8449",
    "Fund":         "#CA6F1E",
    "Filing":       "#C0392B",
    "Event":        "#7D3C98",
    "Location":     "#17A589",
}


def generate_pyvis_html(
    nodes: List[dict],
    edges: List[dict],
    show_edge_labels: bool = False,
    focus_node_id: str | None = None,
) -> str:
    """
    Generate a pyvis-compatible HTML string from node and edge lists.

    Phase 1: Uses inline HTML/JS with vis.js CDN (no pyvis dependency needed).
    Phase 2+: Can upgrade to pyvis library for more features.
    """
    if not nodes:
        return "<p style='color:#4A6A8A;font-family:monospace'>No graph data yet.</p>"

    # Build vis.js node and edge datasets
    vis_nodes = []
    for n in nodes:
        label = n.get("name", n.get("entity_id", "Unknown"))
        entity_type = _infer_type(n)
        color = NODE_COLORS.get(entity_type, "#2E86AB")
        conf = n.get("confidence", 0.5)
        eid = n.get("entity_id", "")
        attrs = n.get("attributes") or {}

        # Escape quotes/newlines for JSON and tooltips
        label_esc = label.replace('"', '\\"').replace("\n", " ")
        tooltip_lines = [
            f"Name: {label_esc}",
            f"Type: {entity_type}",
            f"Confidence: {conf:.0%}",
        ]
        for k, v in attrs.items():
            tooltip_lines.append(f"{k}: {v}")
        title_esc = "\\n".join(tooltip_lines).replace('"', '\\"')

        # Slightly truncate very long labels for readability
        display_label = label_esc
        if len(display_label) > 32:
            display_label = display_label[:29] + "…"

        vis_nodes.append(
            f'{{"id":"{eid}",'
            f'"label":"{display_label}",'
            f'"title":"{title_esc}",'
            f'"color":"{color}",'
            f'"size":{20 + int(conf * 15)}}}'
        )

    vis_edges = []
    for i, e in enumerate(edges):
        rel_type = e.get("rel_type", "")
        rel_conf = e.get("confidence", 0.0)
        title = f"{rel_type} ({rel_conf:.0%})" if rel_type else f"Confidence: {rel_conf:.0%}"
        title_esc = title.replace('"', '\\"')

        parts = [
            f'"id":{i}',
            f'"from":"{e.get("from_id","")}"',
            f'"to":"{e.get("to_id","")}"',
            f'"title":"{title_esc}"',
            f'"arrows":"to"',
            f'"color":{{"color":"#4A6A8A"}}',
        ]
        if show_edge_labels and rel_type:
            parts.append(f'"label":"{rel_type}"')

        vis_edges.append("{" + ",".join(parts) + "}")

    nodes_js = ",".join(vis_nodes)
    edges_js = ",".join(vis_edges)

    focus_id_js = (focus_node_id or "").replace('"', '\\"')

    return f"""<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet"/>
<style>
  body {{ background:#0D1117; margin:0; }}
  #graph {{ width:100%; height:620px; background:#0D1117; border:1px solid #1A3A5A; }}
</style>
</head>
<body>
<div id="graph"></div>
<script>
var nodes = new vis.DataSet([{nodes_js}]);
var edges = new vis.DataSet([{edges_js}]);
var options = {{
  layout: {{
    improvedLayout: true
  }},
  nodes: {{
    font: {{ color:"#C8D8E8", size:12 }},
    borderWidth: 2,
    shape: "dot"
  }},
  edges: {{
    font: {{ color:"#4A6A8A", size:9, strokeWidth:0 }},
    smooth: false,
    selectionWidth: 2,
    hoverWidth: 1.5
  }},
  physics: {{
    enabled: true,
    stabilization: {{ iterations: 250, fit: true }},
    barnesHut: {{
      gravitationalConstant: -6000,
      centralGravity: 0.3,
      springLength: 150,
      springConstant: 0.02,
      damping: 0.09,
      avoidOverlap: 0.25
    }}
  }},
  interaction: {{
    hover: true,
    tooltipDelay: 200,
    navigationButtons: true,
    keyboard: true,
    multiselect: true,
    selectConnectedEdges: true,
    zoomView: true,
    dragView: true
  }},
  background: {{ color:"#0D1117" }}
}};
var network = new vis.Network(
  document.getElementById("graph"),
  {{nodes:nodes,edges:edges}},
  options
);

network.once("stabilizationIterationsDone", function () {{
  network.setOptions({{ physics: false }});
}});

network.fit({{
  animation: {{
    duration: 600,
    easing: "easeInOutQuad"
  }}
}});

var focusId = "{focus_id_js}";
if (focusId) {{
  try {{
    if (nodes.get(focusId)) {{
      network.focus(focusId, {{
        scale: 1.3,
        animation: {{
          duration: 800,
          easing: "easeInOutQuad"
        }}
      }});
      network.selectNodes([focusId]);
    }}
  }} catch (e) {{
    console.warn("Focus node not found", e);
  }}
}}
</script>
</body>
</html>"""


def _infer_type(node: dict) -> str:
    """Infer entity type from node properties."""
    labels = node.get("labels", [])
    if labels:
        return labels[0]
    for t in ["Person", "Organization", "Fund", "Filing", "Event", "Location"]:
        if t.lower() in str(node).lower():
            return t
    return "Organization"
