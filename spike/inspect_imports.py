"""Deep-dive: Inspect import edges in both graphs."""
import json

with open("spike/base_graph.json") as f:
    base = json.load(f)
with open("spike/head_graph.json") as f:
    head = json.load(f)

# Build lookup for nodes
def node_labels(graph_data):
    return {n["id"]: n.get("label", n["id"]) for n in graph_data["nodes"]}

base_labels = node_labels(base)
head_labels = node_labels(head)

print("=== BASE GRAPH: imports/imports_from edges ===")
base_imports = set()
for link in base["links"]:
    rel = link.get("relation", "")
    if rel in ("imports", "imports_from"):
        src = link["source"]
        tgt = link["target"]
        src_label = base_labels.get(src, src)
        tgt_label = base_labels.get(tgt, tgt)
        src_file = link.get("source_file", "")
        key = (src, tgt, rel)
        base_imports.add(key)
        print(f"  {src_label} --[{rel}]--> {tgt_label}  (file: {src_file})")

print(f"\nTotal import edges in base: {len(base_imports)}")

print("\n=== HEAD GRAPH: imports/imports_from edges ===")
head_imports = set()
for link in head["links"]:
    rel = link.get("relation", "")
    if rel in ("imports", "imports_from"):
        src = link["source"]
        tgt = link["target"]
        src_label = head_labels.get(src, src)
        tgt_label = head_labels.get(tgt, tgt)
        src_file = link.get("source_file", "")
        key = (src, tgt, rel)
        head_imports.add(key)
        print(f"  {src_label} --[{rel}]--> {tgt_label}  (file: {src_file})")

print(f"\nTotal import edges in head: {len(head_imports)}")

print("\n=== NEW IMPORT EDGES (in head but not base) ===")
new_imports = head_imports - base_imports
for src, tgt, rel in sorted(new_imports):
    src_label = head_labels.get(src, src)
    tgt_label = head_labels.get(tgt, tgt)
    print(f"  + {src_label} --[{rel}]--> {tgt_label}")

if not new_imports:
    print("  (none)")

print("\n=== REMOVED IMPORT EDGES ===")
removed_imports = base_imports - head_imports
for src, tgt, rel in sorted(removed_imports):
    src_label = base_labels.get(src, src)
    tgt_label = base_labels.get(tgt, tgt)
    print(f"  - {src_label} --[{rel}]--> {tgt_label}")

if not removed_imports:
    print("  (none)")

# Check: are views.py or components.py importing from database/services?
print("\n=== VIEWS.PY EDGES (source_file contains 'views') ===")
for link in head["links"]:
    src_file = link.get("source_file", "")
    if "views" in src_file and link.get("relation") in ("imports", "imports_from"):
        src = link["source"]
        tgt = link["target"]
        print(f"  {head_labels.get(src, src)} --[{link['relation']}]--> {head_labels.get(tgt, tgt)}  (file: {src_file})")

print("\n=== COMPONENTS.PY EDGES (source_file contains 'components') ===")
for link in head["links"]:
    src_file = link.get("source_file", "")
    if "components" in src_file and link.get("relation") in ("imports", "imports_from"):
        src = link["source"]
        tgt = link["target"]
        print(f"  {head_labels.get(src, src)} --[{link['relation']}]--> {head_labels.get(tgt, tgt)}  (file: {src_file})")
