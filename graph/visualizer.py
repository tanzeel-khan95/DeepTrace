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

def generate_pyvis_html(nodes: List[dict], edges: List[dict]) -> str:
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
        # Escape quotes in label for JSON
        label_esc = label.replace('"', '\\"').replace("\n", " ")
        vis_nodes.append(
            f'{{"id":"{eid}",'
            f'"label":"{label_esc}",'
            f'"title":"Type: {entity_type}\\nConf: {conf:.0%}",'
            f'"color":"{color}",'
            f'"size":{20 + int(conf * 15)}}}'
        )

    vis_edges = []
    for i, e in enumerate(edges):
        vis_edges.append(
            f'{{"id":{i},'
            f'"from":"{e.get("from_id","")}",'
            f'"to":"{e.get("to_id","")}",'
            f'"label":"{e.get("rel_type","")}",'
            f'"arrows":"to",'
            f'"color":{{"color":"#4A6A8A"}}}}'
        )

    nodes_js = ",".join(vis_nodes)
    edges_js = ",".join(vis_edges)

    return f"""<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet"/>
<style>
  body {{ background:#0D1117; margin:0; }}
  #graph {{ width:100%; height:500px; background:#0D1117; border:1px solid #1A3A5A; }}
</style>
</head>
<body>
<div id="graph"></div>
<script>
var nodes = new vis.DataSet([{nodes_js}]);
var edges = new vis.DataSet([{edges_js}]);
var options = {{
  nodes: {{ font: {{ color:"#C8D8E8", size:12 }}, borderWidth:2 }},
  edges: {{ font: {{ color:"#4A6A8A", size:10 }}, smooth:{{ type:"curvedCW" }} }},
  physics: {{ stabilization:true }},
  background: {{ color:"#0D1117" }}
}};
new vis.Network(document.getElementById("graph"), {{nodes:nodes,edges:edges}}, options);
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
