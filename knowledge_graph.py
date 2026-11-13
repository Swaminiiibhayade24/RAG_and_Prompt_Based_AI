"""
Entity-relation knowledge graph for IntelliDB AI.

The graph combines:
1) a small, explicit DBMS ontology (curated triples with stable entity IDs), and
2) conservative relation extraction from uploaded text using explicit linguistic patterns.

It deliberately does NOT turn simple co-occurrence into a factual relationship.
"""
from pathlib import Path
from collections import defaultdict
import json
import re

from config import DATA_DIR

GRAPH_PATH = DATA_DIR / "knowledge_graph.json"
ONTOLOGY_SOURCE = "built_in_dbms_ontology"

# Stable entity IDs, human-readable labels, aliases, and broad semantic types.
ENTITY_ROWS = [
    ("database", "Database", "technology", ["database", "db"]),
    ("dbms", "Database Management System", "technology", ["dbms", "database management system"]),
    ("table", "Table", "database_object", ["table", "relation", "relational table"]),
    ("row", "Row", "database_object", ["row", "record", "tuple"]),
    ("column", "Column", "database_object", ["column", "field", "attribute"]),
    ("primary_key", "Primary Key", "key", ["primary key", "primary-key"]),
    ("foreign_key", "Foreign Key", "key", ["foreign key", "foreign-key"]),
    ("candidate_key", "Candidate Key", "key", ["candidate key"]),
    ("super_key", "Super Key", "key", ["super key"]),
    ("composite_key", "Composite Key", "key", ["composite key"]),
    ("unique_constraint", "Unique Constraint", "constraint", ["unique constraint"]),
    ("referential_integrity", "Referential Integrity", "constraint", ["referential integrity"]),
    ("normalization", "Normalization", "design_concept", ["normalization", "normalisation"]),
    ("1nf", "First Normal Form (1NF)", "normal_form", ["1nf", "first normal form"]),
    ("2nf", "Second Normal Form (2NF)", "normal_form", ["2nf", "second normal form"]),
    ("3nf", "Third Normal Form (3NF)", "normal_form", ["3nf", "third normal form"]),
    ("bcnf", "Boyce-Codd Normal Form (BCNF)", "normal_form", ["bcnf", "boyce-codd normal form"]),
    ("functional_dependency", "Functional Dependency", "dependency", ["functional dependency", "functional dependencies"]),
    ("partial_dependency", "Partial Dependency", "dependency", ["partial dependency"]),
    ("transitive_dependency", "Transitive Dependency", "dependency", ["transitive dependency"]),
    ("sql", "SQL", "language", ["sql", "structured query language"]),
    ("select", "SELECT", "sql_command", ["select statement", "select query"]),
    ("insert", "INSERT", "sql_command", ["insert statement", "insert query"]),
    ("update", "UPDATE", "sql_command", ["update statement", "update query"]),
    ("delete", "DELETE", "sql_command", ["delete statement", "delete query"]),
    ("join", "JOIN", "sql_operation", ["join", "joins"]),
    ("inner_join", "INNER JOIN", "sql_operation", ["inner join"]),
    ("left_join", "LEFT JOIN", "sql_operation", ["left join", "left outer join"]),
    ("index", "Index", "database_object", ["index", "database index", "indexing"]),
    ("transaction", "Transaction", "transaction_concept", ["transaction", "transactions"]),
    ("acid", "ACID Properties", "transaction_concept", ["acid", "acid properties"]),
    ("atomicity", "Atomicity", "acid_property", ["atomicity"]),
    ("consistency", "Consistency", "acid_property", ["consistency"]),
    ("isolation", "Isolation", "acid_property", ["isolation"]),
    ("durability", "Durability", "acid_property", ["durability"]),
    ("concurrency_control", "Concurrency Control", "transaction_concept", ["concurrency control"]),
    ("lock", "Lock", "transaction_concept", ["lock", "locking"]),
    ("deadlock", "Deadlock", "transaction_concept", ["deadlock", "deadlocks"]),
    ("view", "View", "database_object", ["view", "views"]),
    ("schema", "Schema", "database_object", ["schema", "database schema"]),
    ("entity", "Entity", "er_model", ["entity", "entities"]),
    ("relationship", "Relationship", "er_model", ["relationship", "relationships"]),
    ("er_diagram", "ER Diagram", "er_model", ["er diagram", "entity relationship diagram"]),
    ("query_optimization", "Query Optimization", "query_processing", ["query optimization", "query optimizer", "query optimiser"]),
]

# Curated, directional, meaningful DBMS facts. These are explicitly marked as
# built-in ontology facts, not as claims extracted from a user's uploaded file.
BUILTIN_TRIPLES = [
    ("dbms", "MANAGES", "database"),
    ("database", "CONTAINS", "table"),
    ("table", "CONTAINS", "row"),
    ("table", "HAS_ATTRIBUTE", "column"),
    ("table", "HAS_PRIMARY_KEY", "primary_key"),
    ("table", "MAY_HAVE", "foreign_key"),
    ("primary_key", "UNIQUELY_IDENTIFIES", "row"),
    ("foreign_key", "REFERENCES", "primary_key"),
    ("foreign_key", "ENFORCES", "referential_integrity"),
    ("candidate_key", "CAN_SERVE_AS", "primary_key"),
    ("super_key", "GENERALIZES", "candidate_key"),
    ("composite_key", "MAY_BE", "candidate_key"),
    ("unique_constraint", "ENFORCES", "referential_integrity"),
    ("normalization", "ORGANIZES", "table"),
    ("normalization", "USES", "functional_dependency"),
    ("1nf", "IS_A", "normalization"),
    ("2nf", "IS_A", "normalization"),
    ("3nf", "IS_A", "normalization"),
    ("bcnf", "IS_A", "normalization"),
    ("2nf", "ELIMINATES", "partial_dependency"),
    ("3nf", "ELIMINATES", "transitive_dependency"),
    ("functional_dependency", "DETERMINES", "column"),
    ("partial_dependency", "IS_A", "functional_dependency"),
    ("transitive_dependency", "IS_A", "functional_dependency"),
    ("sql", "QUERY_LANGUAGE_FOR", "database"),
    ("select", "IS_A", "sql"),
    ("insert", "IS_A", "sql"),
    ("update", "IS_A", "sql"),
    ("delete", "IS_A", "sql"),
    ("join", "COMBINES", "table"),
    ("inner_join", "IS_A", "join"),
    ("left_join", "IS_A", "join"),
    ("index", "ACCELERATES", "select"),
    ("transaction", "HAS_PROPERTIES", "acid"),
    ("acid", "INCLUDES", "atomicity"),
    ("acid", "INCLUDES", "consistency"),
    ("acid", "INCLUDES", "isolation"),
    ("acid", "INCLUDES", "durability"),
    ("transaction", "CONTROLLED_BY", "concurrency_control"),
    ("concurrency_control", "USES", "lock"),
    ("deadlock", "CAN_OCCUR_DURING", "concurrency_control"),
    ("view", "DERIVED_FROM", "table"),
    ("schema", "DESCRIBES", "database"),
    ("er_diagram", "MODELS", "entity"),
    ("er_diagram", "MODELS", "relationship"),
    ("query_optimization", "OPTIMIZES", "select"),
]

# Only explicit textual patterns produce document-extracted relations.
# Captures can be aliases or canonical entity labels.
TEXT_PATTERNS = [
    (r"\b(?P<a>.+?)\s+references?\s+(?P<b>.+)", "REFERENCES"),
    (r"\b(?P<a>.+?)\s+uniquely identifies?\s+(?P<b>.+)", "UNIQUELY_IDENTIFIES"),
    (r"\b(?P<a>.+?)\s+contains?\s+(?P<b>.+)", "CONTAINS"),
    (r"\b(?P<a>.+?)\s+consists of\s+(?P<b>.+)", "CONSISTS_OF"),
    (r"\b(?P<a>.+?)\s+is a type of\s+(?P<b>.+)", "IS_A"),
    (r"\b(?P<a>.+?)\s+is part of\s+(?P<b>.+)", "PART_OF"),
    (r"\b(?P<a>.+?)\s+depends on\s+(?P<b>.+)", "DEPENDS_ON"),
    (r"\b(?P<a>.+?)\s+eliminates?\s+(?P<b>.+)", "ELIMINATES"),
    (r"\b(?P<a>.+?)\s+ensures?\s+(?P<b>.+)", "ENSURES"),
    (r"\b(?P<a>.+?)\s+improves?\s+(?P<b>.+)", "IMPROVES"),
    (r"\b(?P<a>.+?)\s+accelerates?\s+(?P<b>.+)", "ACCELERATES"),
    (r"\b(?P<a>.+?)\s+is used to\s+(?P<b>.+)", "USED_TO"),
]

def _clean_phrase(value):
    value = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9)]+$", "", value.strip().lower())
    value = re.sub(r"\b(the|a|an|each|every|any|all)\s+", "", value)
    return value.strip()

class KnowledgeGraph:
    def __init__(self, path=GRAPH_PATH):
        self.path = Path(path)
        self.entities = {}
        self.alias_to_id = {}
        self.triples = {}
        self._register_entities()
        self._load()
        self._seed_builtin_graph()

    def _register_entities(self):
        for eid, label, etype, aliases in ENTITY_ROWS:
            self.entities[eid] = {"id": eid, "label": label, "type": etype}
            for alias in [label.lower(), *aliases]:
                self.alias_to_id[alias.lower()] = eid

    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.triples = data.get("triples", {})
            except (ValueError, OSError):
                self.triples = {}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({
            "schema_version": 2,
            "entities": list(self.entities.values()),
            "triples": self.triples
        }, indent=2), encoding="utf-8")

    def _add_triple(self, subject, predicate, obj, source, evidence=None, confidence=1.0):
        if subject not in self.entities or obj not in self.entities:
            return
        key = f"{subject}|{predicate}|{obj}"
        item = self.triples.setdefault(key, {
            "subject": subject, "predicate": predicate, "object": obj,
            "sources": [], "evidence": [], "confidence": confidence
        })
        if source not in item["sources"]:
            item["sources"].append(source)
        if evidence and evidence not in item["evidence"] and len(item["evidence"]) < 5:
            item["evidence"].append(evidence[:500])

    def _seed_builtin_graph(self):
        for s, p, o in BUILTIN_TRIPLES:
            self._add_triple(s, p, o, ONTOLOGY_SOURCE)
        self.save()

    def _find_entity(self, phrase):
        phrase = _clean_phrase(phrase)
        # Longest alias match avoids matching "join" inside "inner join".
        for alias in sorted(self.alias_to_id, key=len, reverse=True):
            if phrase == alias or phrase.startswith(alias + " ") or phrase.endswith(" " + alias):
                return self.alias_to_id[alias]
        # Search a phrase for an alias only when the alias is a full token phrase.
        matches = [(len(a), eid) for a, eid in self.alias_to_id.items()
                   if re.search(r"(?<!\w)" + re.escape(a) + r"(?!\w)", phrase)]
        return max(matches)[1] if matches else None

    def _extract_from_sentence(self, sentence, source):
        text = sentence.strip()
        if not text or len(text) > 1200:
            return
        for pattern, predicate in TEXT_PATTERNS:
            match = re.search(pattern, text, flags=re.I)
            if not match:
                continue
            s = self._find_entity(match.group("a"))
            o = self._find_entity(match.group("b"))
            if s and o and s != o:
                self._add_triple(s, predicate, o, source, evidence=text, confidence=0.85)
                return

    def add_document(self, chunks, source):
        extracted = 0
        for chunk in chunks:
            # Sentence-level extraction only; no co-occurrence edges are fabricated.
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", chunk):
                before = len(self.triples)
                self._extract_from_sentence(sentence, source)
                extracted += len(self.triples) - before
        self.save()
        return extracted

    def search(self, question, limit=20):
        q = question.lower()
        matched = set()
        # Match any known alias in the question.
        for alias, eid in self.alias_to_id.items():
            if re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", q):
                matched.add(eid)
        # Add entities mentioned via natural-language labels, plus connected one-hop nodes.
        if not matched:
            return []
        selected = []
        for triple in self.triples.values():
            if triple["subject"] in matched or triple["object"] in matched:
                selected.append(triple)
        # Prioritize facts from uploaded evidence, while retaining curated ontology links.
        selected.sort(key=lambda t: (
            ONTOLOGY_SOURCE in t["sources"],
            -len(t["sources"])
        ))
        return selected[:limit]

    def snapshot(self, max_edges=250):
        edges = list(self.triples.values())[:max_edges]
        used = {e["subject"] for e in edges} | {e["object"] for e in edges}
        nodes = [self.entities[eid] for eid in sorted(used)]
        return {"nodes": nodes, "edges": edges}

    def stats(self):
        return {"nodes": len(self.entities), "edges": len(self.triples)}

    def entity_label(self, entity_id):
        return self.entities.get(entity_id, {}).get("label", entity_id)
