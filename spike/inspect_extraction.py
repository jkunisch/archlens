"""Inspect raw extraction output to see what edges are created."""
import json
from pathlib import Path
from graphify.extract import extract, collect_files

dummy_repo = Path("spike/dummy_repo")
files = collect_files(dummy_repo)

extraction = extract(files)

# Save raw extraction for inspection
with open("spike/raw_extraction.json", "w") as f:
    json.dump(extraction, f, indent=2, default=str)

# Count edge types
from collections import Counter
edge_types = Counter()
import_edges = []
for e in extraction.get("edges", []):
    edge_types[e.get("relation", "unknown")] += 1
    if e.get("relation") in ("imports", "imports_from"):
        import_edges.append(e)

print("=== EXTRACTION EDGE TYPES ===")
for rel, count in edge_types.most_common():
    print(f"  {rel}: {count}")

print(f"\n=== IMPORT EDGES IN EXTRACTION ({len(import_edges)}) ===")
for e in import_edges:
    print(f"  {e['source']} --[{e['relation']}]--> {e['target']}  (file: {e.get('source_file', '?')})")

# Check if import edge targets match any node IDs
node_ids = {n["id"] for n in extraction.get("nodes", [])}
print(f"\n=== IMPORT EDGE TARGET MATCHING ===")
print(f"Total nodes: {len(node_ids)}")
for e in import_edges:
    src_match = e["source"] in node_ids
    tgt_match = e["target"] in node_ids
    print(f"  {e['source']}({src_match}) -> {e['target']}({tgt_match})")
