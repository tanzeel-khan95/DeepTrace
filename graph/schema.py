"""
schema.py — Neo4j node constraints and allowed types for DeepTrace identity graph.

Run setup_schema() once on first startup to create uniqueness constraints.
Architecture position: called by neo4j_manager.py on connection init.
"""

# Node uniqueness constraint Cypher statements
CONSTRAINT_STATEMENTS = [
    "CREATE CONSTRAINT person_id    IF NOT EXISTS FOR (n:Person)       REQUIRE n.entity_id IS UNIQUE",
    "CREATE CONSTRAINT org_id       IF NOT EXISTS FOR (n:Organization) REQUIRE n.entity_id IS UNIQUE",
    "CREATE CONSTRAINT fund_id      IF NOT EXISTS FOR (n:Fund)         REQUIRE n.entity_id IS UNIQUE",
    "CREATE CONSTRAINT filing_id     IF NOT EXISTS FOR (n:Filing)       REQUIRE n.entity_id IS UNIQUE",
    "CREATE CONSTRAINT event_id     IF NOT EXISTS FOR (n:Event)        REQUIRE n.entity_id IS UNIQUE",
    "CREATE CONSTRAINT location_id  IF NOT EXISTS FOR (n:Location)     REQUIRE n.entity_id IS UNIQUE",
]

# Allowed entity types — must match Entity.entity_type Literal
ENTITY_TYPES = ["Person", "Organization", "Fund", "Location", "Event", "Filing"]

# Allowed relationship types — must match Relationship.rel_type Literal
RELATIONSHIP_TYPES = [
    "WORKS_AT", "INVESTED_IN", "CONNECTED_TO",
    "FILED_WITH", "FOUNDED", "AFFILIATED_WITH",
    "BOARD_MEMBER", "MANAGED", "CONTROLS",
]

def entity_to_cypher_merge(entity: dict) -> str:
    """Generate a MERGE Cypher statement for one Entity dict."""
    label = entity["entity_type"]
    attrs = ", ".join(
        f'n.{k} = "{v}"' for k, v in entity.get("attributes", {}).items()
    )
    set_clause = f", SET {attrs}" if attrs else ""
    return (
        f'MERGE (n:{label} {{entity_id: "{entity["entity_id"]}"}}) '
        f'SET n.name = "{entity["name"]}", n.confidence = {entity["confidence"]}'
        f'{set_clause}'
    )

def relationship_to_cypher_merge(rel: dict) -> str:
    """Generate a MERGE Cypher statement for one Relationship dict."""
    return (
        f'MATCH (a {{entity_id: "{rel["from_id"]}"}}), (b {{entity_id: "{rel["to_id"]}"}})'
        f' MERGE (a)-[r:{rel["rel_type"]}]->(b)'
        f' SET r.confidence = {rel["confidence"]}, r.source_fact_id = "{rel["source_fact_id"]}"'
    )
