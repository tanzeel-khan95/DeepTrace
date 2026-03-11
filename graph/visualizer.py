"""
visualizer.py — D3.js force-directed graph visualization.

Generates a self-contained HTML file that renders in Streamlit via
st.components.v1.html(). Node and edge colours match the Phase 3 spec.
Dark navy theme matching DeepTrace brand.

Architecture position: called by graph_builder agent and Streamlit page 02.
"""
import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

ENTITY_COLORS: Dict[str, str] = {
    "Person": "#4A90D9",
    "Organization": "#E8813A",
    "Fund": "#50C878",
    "Location": "#9B59B6",
    "Event": "#E74C3C",
    "Filing": "#F39C12",
    "default": "#95A5A6",
}

EDGE_COLORS: Dict[str, str] = {
    "WORKS_AT": "#4A90D9",
    "INVESTED_IN": "#50C878",
    "CONNECTED_TO": "#95A5A6",
    "FILED_WITH": "#F39C12",
    "FOUNDED": "#E8813A",
    "AFFILIATED_WITH": "#9B59B6",
    "BOARD_MEMBER": "#E74C3C",
    "MANAGED": "#1ABC9C",
    "CONTROLS": "#E74C3C",
    "default": "#7F8C8D",
}


def _infer_entity_type(node: dict) -> str:
    """Infer entity type from node (entity_type or labels)."""
    etype = node.get("entity_type")
    if etype:
        return etype
    labels = node.get("labels", [])
    if labels:
        return labels[0]
    for t in ["Person", "Organization", "Fund", "Filing", "Event", "Location"]:
        if t.lower() in str(node).lower():
            return t
    return "default"


def generate_d3_html(nodes: List[dict], edges: List[dict], title: str = "Identity Graph") -> str:
    """
    Generate a self-contained HTML file with an interactive D3.js force-directed graph.

    Args:
        nodes: List of entity dicts (from Neo4j or state["entities"])
        edges: List of relationship dicts (from Neo4j or state["relationships"])
        title: Graph title shown in header

    Returns:
        Complete HTML string (self-contained, no external dependencies except D3 CDN)
    """
    if not nodes:
        return _empty_graph_html(title)

    d3_nodes = []
    for node in nodes:
        etype = _infer_entity_type(node)
        d3_nodes.append({
            "id": node.get("entity_id", node.get("name", "")),
            "name": node.get("name", "Unknown"),
            "type": etype,
            "color": ENTITY_COLORS.get(etype, ENTITY_COLORS["default"]),
            "confidence": node.get("confidence", 0.5),
            "attributes": node.get("attributes", {}),
        })

    node_ids = {n["id"] for n in d3_nodes}

    d3_edges = []
    for edge in edges:
        from_id = edge.get("from_id", "")
        to_id = edge.get("to_id", "")
        rel_type = edge.get("rel_type", "CONNECTED_TO")
        if from_id in node_ids and to_id in node_ids:
            d3_edges.append({
                "source": from_id,
                "target": to_id,
                "type": rel_type,
                "color": EDGE_COLORS.get(rel_type, EDGE_COLORS["default"]),
                "confidence": edge.get("confidence", 0.5),
                "label": rel_type.replace("_", " ").title(),
            })

    graph_data = json.dumps({"nodes": d3_nodes, "links": d3_edges})
    node_count = len(d3_nodes)
    edge_count = len(d3_edges)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: #0D1B2A;
      font-family: 'Segoe UI', system-ui, sans-serif;
      color: #E8EDF2;
      overflow: hidden;
    }}
    #header {{
      position: fixed; top: 0; left: 0; right: 0;
      background: linear-gradient(135deg, #0D1B2A 0%, #1A2D45 100%);
      border-bottom: 1px solid #2A4A6A;
      padding: 12px 20px;
      display: flex; align-items: center; justify-content: space-between;
      z-index: 100;
    }}
    #header h1 {{ font-size: 16px; font-weight: 600; color: #4A90D9; }}
    #stats {{ font-size: 12px; color: #7A9AB5; }}
    #graph-container {{
      position: fixed; top: 52px; left: 0; right: 320px; bottom: 0;
    }}
    svg {{ width: 100%; height: 100%; }}
    .node circle {{
      stroke: rgba(255,255,255,0.2);
      stroke-width: 2px;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .node circle:hover {{
      stroke: #ffffff;
      stroke-width: 3px;
      filter: brightness(1.3);
    }}
    .node.selected circle {{
      stroke: #ffffff;
      stroke-width: 3px;
    }}
    .node text {{
      font-size: 11px;
      fill: #E8EDF2;
      pointer-events: none;
      text-shadow: 0 1px 3px rgba(0,0,0,0.8);
    }}
    .link {{
      stroke-opacity: 0.6;
      transition: stroke-opacity 0.2s;
    }}
    .link:hover {{ stroke-opacity: 1.0; }}
    .link-label {{
      font-size: 9px;
      fill: #7A9AB5;
      pointer-events: none;
    }}
    #tooltip {{
      position: fixed;
      background: rgba(13,27,42,0.95);
      border: 1px solid #2A4A6A;
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 12px;
      max-width: 240px;
      pointer-events: none;
      z-index: 200;
      display: none;
      backdrop-filter: blur(8px);
    }}
    #tooltip .tooltip-title {{ font-weight: 600; color: #4A90D9; margin-bottom: 6px; font-size: 13px; }}
    #tooltip .tooltip-row {{ color: #A8C0D0; margin: 3px 0; }}
    #detail-panel {{
      position: fixed; top: 52px; right: 0; width: 320px; bottom: 0;
      background: #0D1B2A;
      border-left: 1px solid #2A4A6A;
      overflow-y: auto;
      padding: 16px;
    }}
    #detail-panel h2 {{ font-size: 14px; color: #4A90D9; margin-bottom: 12px; }}
    .detail-empty {{ color: #4A6A8A; font-size: 12px; text-align: center; margin-top: 60px; }}
    .detail-card {{
      background: #1A2D45;
      border: 1px solid #2A4A6A;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 10px;
    }}
    .detail-card .card-title {{ font-weight: 600; color: #E8EDF2; font-size: 13px; margin-bottom: 6px; }}
    .detail-card .card-type {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 10px;
      font-size: 10px;
      font-weight: 600;
      margin-bottom: 8px;
    }}
    .detail-card .card-row {{ color: #A8C0D0; font-size: 11px; margin: 4px 0; }}
    .detail-card .card-attr {{ color: #7A9AB5; font-size: 10px; margin: 2px 0; }}
    .conf-bar {{
      height: 4px;
      background: #1A2D45;
      border-radius: 2px;
      margin-top: 8px;
      overflow: hidden;
    }}
    .conf-fill {{
      height: 100%;
      border-radius: 2px;
      background: linear-gradient(90deg, #E74C3C, #F39C12, #50C878);
    }}
    #legend {{
      position: fixed; bottom: 16px; left: 16px;
      background: rgba(13,27,42,0.9);
      border: 1px solid #2A4A6A;
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 11px;
    }}
    .legend-item {{ display: flex; align-items: center; margin: 3px 0; gap: 8px; color: #A8C0D0; }}
    .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
    #controls {{
      position: fixed; bottom: 16px; right: 336px;
      display: flex; gap: 8px;
    }}
    .ctrl-btn {{
      background: rgba(13,27,42,0.9);
      border: 1px solid #2A4A6A;
      color: #A8C0D0;
      padding: 6px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      transition: all 0.2s;
    }}
    .ctrl-btn:hover {{ background: #1A2D45; color: #E8EDF2; }}
  </style>
</head>
<body>
  <div id="header">
    <h1>🕵️ {title}</h1>
    <span id="stats">{node_count} entities · {edge_count} relationships</span>
  </div>

  <div id="graph-container"><svg id="graph-svg"></svg></div>

  <div id="tooltip"></div>

  <div id="detail-panel">
    <h2>Entity Details</h2>
    <div id="detail-content" class="detail-empty">Click a node to explore</div>
  </div>

  <div id="legend">
    <div style="font-weight:600;color:#4A90D9;margin-bottom:6px;font-size:11px;">Entity Types</div>
    <div class="legend-item"><div class="legend-dot" style="background:#4A90D9"></div>Person</div>
    <div class="legend-item"><div class="legend-dot" style="background:#E8813A"></div>Organization</div>
    <div class="legend-item"><div class="legend-dot" style="background:#50C878"></div>Fund</div>
    <div class="legend-item"><div class="legend-dot" style="background:#9B59B6"></div>Location</div>
    <div class="legend-item"><div class="legend-dot" style="background:#E74C3C"></div>Event</div>
    <div class="legend-item"><div class="legend-dot" style="background:#F39C12"></div>Filing</div>
  </div>

  <div id="controls">
    <button class="ctrl-btn" onclick="resetZoom()">⟳ Reset</button>
    <button class="ctrl-btn" onclick="toggleLabels()">🏷 Labels</button>
  </div>

<script>
const GRAPH_DATA = {graph_data};
let showLabels = true;

const container = document.getElementById('graph-container');
const width     = container.clientWidth;
const height    = container.clientHeight;

const svg = d3.select('#graph-svg')
  .attr('viewBox', [0, 0, width, height]);

const g = svg.append('g');

const zoom = d3.zoom()
  .scaleExtent([0.2, 4])
  .on('zoom', (event) => g.attr('transform', event.transform));

svg.call(zoom);

const defs = svg.append('defs');
const arrowTypes = [...new Set(GRAPH_DATA.links.map(l => l.type))];
arrowTypes.forEach(type => {{
  const color = GRAPH_DATA.links.find(l => l.type === type)?.color || '#7F8C8D';
  defs.append('marker')
    .attr('id', `arrow-${{type}}`)
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 22)
    .attr('refY', 0)
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', color);
}});

const nodeRadius = (type) => {{
  const sizes = {{ Person: 18, Organization: 16, Fund: 16, Location: 12, Event: 12, Filing: 12 }};
  return sizes[type] || 12;
}};

const simulation = d3.forceSimulation(GRAPH_DATA.nodes)
  .force('link', d3.forceLink(GRAPH_DATA.links).id(d => d.id).distance(120).strength(0.5))
  .force('charge', d3.forceManyBody().strength(-400))
  .force('center', d3.forceCenter(width / 2, height / 2))
  .force('collision', d3.forceCollide().radius(d => nodeRadius(d.type) + 10));

const link = g.append('g').attr('class', 'links')
  .selectAll('line')
  .data(GRAPH_DATA.links)
  .join('line')
  .attr('class', 'link')
  .attr('stroke', d => d.color)
  .attr('stroke-width', d => 1 + d.confidence * 2)
  .attr('marker-end', d => `url(#arrow-${{d.type}})`);

const linkLabel = g.append('g').attr('class', 'link-labels')
  .selectAll('text')
  .data(GRAPH_DATA.links)
  .join('text')
  .attr('class', 'link-label')
  .text(d => d.label);

const node = g.append('g').attr('class', 'nodes')
  .selectAll('g')
  .data(GRAPH_DATA.nodes)
  .join('g')
  .attr('class', 'node')
  .call(d3.drag()
    .on('start', dragStart)
    .on('drag',  dragging)
    .on('end',   dragEnd)
  )
  .on('click', (event, d) => {{
    event.stopPropagation();
    selectNode(d);
  }})
  .on('mouseover', (event, d) => showTooltip(event, d))
  .on('mouseout',  () => hideTooltip());

node.append('circle')
  .attr('r', d => nodeRadius(d.type))
  .attr('fill', d => d.color)
  .attr('fill-opacity', 0.9);

const typeIcons = {{ Person: '👤', Organization: '🏢', Fund: '💰', Location: '📍', Event: '📅', Filing: '📄' }};
node.append('text')
  .attr('text-anchor', 'middle')
  .attr('dy', '0.35em')
  .attr('font-size', d => nodeRadius(d.type) * 0.9)
  .text(d => typeIcons[d.type] || '◆');

node.append('text')
  .attr('class', 'node-label')
  .attr('text-anchor', 'middle')
  .attr('dy', d => nodeRadius(d.type) + 14)
  .attr('font-size', 10)
  .text(d => d.name.length > 18 ? d.name.substring(0, 16) + '…' : d.name);

simulation.on('tick', () => {{
  link
    .attr('x1', d => d.source.x)
    .attr('y1', d => d.source.y)
    .attr('x2', d => d.target.x)
    .attr('y2', d => d.target.y);

  linkLabel
    .attr('x', d => (d.source.x + d.target.x) / 2)
    .attr('y', d => (d.source.y + d.target.y) / 2);

  node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
}});

function dragStart(event, d) {{
  if (!event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x; d.fy = d.y;
}}
function dragging(event, d) {{ d.fx = event.x; d.fy = event.y; }}
function dragEnd(event, d) {{
  if (!event.active) simulation.alphaTarget(0);
  d.fx = null; d.fy = null;
}}

function showTooltip(event, d) {{
  const conf = Math.round(d.confidence * 100);
  const tooltip = document.getElementById('tooltip');
  tooltip.innerHTML = `
    <div class="tooltip-title">${{d.name}}</div>
    <div class="tooltip-row">Type: ${{d.type}}</div>
    <div class="tooltip-row">Confidence: ${{conf}}%</div>
    ${{Object.entries(d.attributes || {{}}).slice(0,3).map(([k,v]) =>
      `<div class="tooltip-row">${{k}}: ${{v}}</div>`).join('')}}
  `;
  tooltip.style.display = 'block';
  tooltip.style.left = (event.clientX + 16) + 'px';
  tooltip.style.top  = (event.clientY - 20) + 'px';
}}
function hideTooltip() {{
  document.getElementById('tooltip').style.display = 'none';
}}

function selectNode(d) {{
  document.querySelectorAll('.node.selected').forEach(n => n.classList.remove('selected'));
  node.filter(n => n.id === d.id).classed('selected', true);

  const conf = Math.round(d.confidence * 100);
  const attrs = Object.entries(d.attributes || {{}});
  const color = d.color;

  const connectedLinks = GRAPH_DATA.links.filter(l =>
    (typeof l.source === 'object' ? l.source.id : l.source) === d.id ||
    (typeof l.target === 'object' ? l.target.id : l.target) === d.id
  );

  const panel = document.getElementById('detail-content');
  panel.innerHTML = `
    <div class="detail-card">
      <div class="card-title">${{d.name}}</div>
      <div class="card-type" style="background:${{color}}22;color:${{color}}">${{d.type}}</div>
      <div class="card-row">Confidence: ${{conf}}%</div>
      <div class="conf-bar"><div class="conf-fill" style="width:${{conf}}%"></div></div>
      ${{attrs.length > 0 ? '<div style="margin-top:8px;font-size:10px;color:#4A6A8A;font-weight:600">ATTRIBUTES</div>' : ''}}
      ${{attrs.map(([k,v]) => `<div class="card-attr">${{k}}: ${{v}}</div>`).join('')}}
    </div>
    ${{connectedLinks.length > 0 ? `
    <div style="font-size:11px;color:#4A6A8A;font-weight:600;margin:8px 0 4px">CONNECTIONS (${{connectedLinks.length}})</div>
    ${{connectedLinks.map(l => {{
      const isSource = (typeof l.source === 'object' ? l.source.id : l.source) === d.id;
      const other = isSource ? l.target : l.source;
      const otherName = typeof other === 'object' ? other.name : other;
      const arrow = isSource ? '→' : '←';
      return `<div class="detail-card" style="padding:8px">
        <div style="font-size:11px;color:#A8C0D0">${{arrow}} ${{l.label}}</div>
        <div style="font-size:12px;color:#E8EDF2">${{otherName}}</div>
        <div style="font-size:10px;color:#7A9AB5">confidence: ${{Math.round(l.confidence*100)}}%</div>
      </div>`;
    }}).join('')}}` : ''}}
  `;
}}

svg.on('click', () => {{
  document.querySelectorAll('.node.selected').forEach(n => n.classList.remove('selected'));
  document.getElementById('detail-content').innerHTML = '<div class="detail-empty">Click a node to explore</div>';
}});

function resetZoom() {{
  svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
}}

function toggleLabels() {{
  showLabels = !showLabels;
  d3.selectAll('.node-label').style('display', showLabels ? 'block' : 'none');
  d3.selectAll('.link-label').style('display', showLabels ? 'block' : 'none');
}}
</script>
</body>
</html>"""


def _empty_graph_html(title: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>body{{background:#0D1B2A;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;font-family:sans-serif;}}</style>
</head><body>
<p style="color:#4A6A8A;font-size:14px">No entities found for "{title}"</p>
</body></html>"""
