"""Analyze the diff output to understand signal vs noise."""
import json
from collections import Counter

with open("spike/diff_output.json") as f:
    diff = json.load(f)

print("=== NEW IMPORT EDGES (the signal we care about) ===")
import_edges = []
for e in diff["new_edges"]:
    if e["relation"] in ("imports", "imports_from"):
        import_edges.append(e)
        print(f"  {e['source']} -> {e['target']}  [{e['relation']}]")

if not import_edges:
    print("  (none)")

print()
print("=== ALL NEW EDGES BY RELATION TYPE ===")
relations = Counter(e["relation"] for e in diff["new_edges"])
for rel, count in relations.most_common():
    print(f"  {rel}: {count}")

print()
print("=== ALL NEW EDGES BY CONFIDENCE ===")
confidences = Counter(e["confidence"] for e in diff["new_edges"])
for conf, count in confidences.most_common():
    print(f"  {conf}: {count}")

print()
print("=== KEY EDGES: File-level imports_from (EXTRACTED) ===")
for e in diff["new_edges"]:
    if e["confidence"] == "EXTRACTED" and e["relation"] in ("imports", "imports_from"):
        print(f"  + {e['source']} -> {e['target']}  [{e['relation']}]")

print()
print("=== STRUCTURAL EDGES: contains ===")
for e in diff["new_edges"]:
    if e["relation"] == "contains":
        print(f"  + {e['source']} -> {e['target']}")

print()
print("=== REMOVED IMPORT-TYPE EDGES ===")
for e in diff["removed_edges"]:
    if e["relation"] in ("imports", "imports_from"):
        print(f"  - {e['source']} -> {e['target']}  [{e['relation']}]")

if not any(e["relation"] in ("imports", "imports_from") for e in diff["removed_edges"]):
    print("  (none)")
