"""
ArchLens Spike — Eigener Import-Aware Graph Diff

Erkenntnis: Graphify's build_from_json() filtert import-Edges heraus,
weil Target-IDs (z.B. 'database_models') nicht mit Node-IDs (z.B. 'models')
matchen. Die rohe Extraction hat aber alle Imports korrekt.

Dieser Test zeigt:
1. Signal ist im RAW extraction vorhanden
2. Wir koennen file-level imports direkt diffenFuer ArchLens ist das der relevante Ansatz.
"""
import json
from pathlib import Path
from graphify.extract import extract, collect_files

dummy_repo = Path("spike/dummy_repo")


# ── Phase 1: Base Extraction (clean architecture) ────────────────────────────

print("=" * 70)
print("PHASE 1: Base Extraction (clean)")
print("=" * 70)

files = collect_files(dummy_repo)
base_extraction = extract(files)

# Extract only import edges
base_imports = set()
for e in base_extraction["edges"]:
    if e["relation"] in ("imports", "imports_from"):
        key = (e["source"], e["target"], e["relation"])
        base_imports.add(key)

print(f"Files: {len(files)}")
print(f"Import edges: {len(base_imports)}")
for src, tgt, rel in sorted(base_imports):
    print(f"  {src} --[{rel}]--> {tgt}")


# ── Phase 2: Introduce Violations ─────────────────────────────────────────

print("\n" + "=" * 70)
print("PHASE 2: Introducing Boundary Violations")
print("=" * 70)

views_path = dummy_repo / "frontend" / "views.py"
original_views = views_path.read_text(encoding="utf-8")

components_path = dummy_repo / "frontend" / "components.py"
original_components = components_path.read_text(encoding="utf-8")

# Violation 1: frontend/views.py adds `from database.models import User`
violation_views = original_views.replace(
    '"""Frontend views - renders pages by calling the API layer."""',
    '"""Frontend views - renders pages by calling the API layer."""\n# VIOLATION: Frontend greift direkt auf Database zu\nfrom database.models import User'
)
views_path.write_text(violation_views, encoding="utf-8")

# Violation 2: frontend/components.py adds `from services.payment import PaymentService`  
violation_components = original_components.replace(
    '"""Frontend UI components."""',
    '"""Frontend UI components."""\n# VIOLATION: Frontend importiert aus services/\nfrom services.payment import PaymentService'
)
components_path.write_text(violation_components, encoding="utf-8")

print("Injected violations:")
print("  1. frontend/views.py -> database.models (from database.models import User)")
print("  2. frontend/components.py -> services.payment (from services.payment import PaymentService)")


# ── Phase 3: Head Extraction ──────────────────────────────────────────────

print("\n" + "=" * 70)
print("PHASE 3: Head Extraction (with violations)")
print("=" * 70)

files_head = collect_files(dummy_repo)
head_extraction = extract(files_head)

head_imports = set()
for e in head_extraction["edges"]:
    if e["relation"] in ("imports", "imports_from"):
        key = (e["source"], e["target"], e["relation"])
        head_imports.add(key)

print(f"Files: {len(files_head)}")
print(f"Import edges: {len(head_imports)}")
for src, tgt, rel in sorted(head_imports):
    print(f"  {src} --[{rel}]--> {tgt}")


# ── Phase 4: Diff ─────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("PHASE 4: Import Edge Diff")
print("=" * 70)

new_imports = head_imports - base_imports
removed_imports = base_imports - head_imports

print(f"\n+++ NEW IMPORT EDGES ({len(new_imports)}) +++")
for src, tgt, rel in sorted(new_imports):
    print(f"  + {src} --[{rel}]--> {tgt}")

print(f"\n--- REMOVED IMPORT EDGES ({len(removed_imports)}) ---")
for src, tgt, rel in sorted(removed_imports):
    print(f"  - {src} --[{rel}]--> {tgt}")


# ── Phase 5: ArchLens-Style Violation Check ───────────────────────────────

print("\n" + "=" * 70)
print("PHASE 5: ArchLens Violation Check (.archlens.yml simulation)")
print("=" * 70)

# Simulate .archlens.yml rules
rules = [
    {"from": "frontend", "to": "database", "severity": "FORBID", "message": "Frontend darf nicht direkt auf Database zugreifen"},
    {"from": "frontend", "to": "services", "severity": "FORBID", "message": "Frontend darf nicht direkt auf Services zugreifen. Nutze den API-Layer."},
]

violations_found = []
for src, tgt, rel in new_imports:
    for rule in rules:
        # src is the file stem (e.g. 'views', 'components')
        # We need to know which package it belongs to
        # In the extraction, source_file tells us
        src_files = [e["source_file"] for e in head_extraction["edges"]
                     if e["source"] == src and e["relation"] in ("imports", "imports_from")]
        for src_file in src_files:
            src_pkg = None
            for pkg in ("frontend", "api", "services", "database", "utils"):
                if pkg in src_file:
                    src_pkg = pkg
                    break
            
            tgt_pkg = tgt.split("_")[0] if "_" in tgt else None
            
            if src_pkg and tgt_pkg and src_pkg in rule["from"] and tgt_pkg in rule["to"]:
                violations_found.append({
                    "rule": rule,
                    "edge": (src, tgt, rel),
                    "source_file": src_file,
                    "src_pkg": src_pkg,
                    "tgt_pkg": tgt_pkg,
                })

print(f"\nViolations detected: {len(violations_found)}")
for v in violations_found:
    src, tgt, rel = v["edge"]
    print(f"\n  {'='*50}")
    print(f"  🔴 {v['rule']['severity']}: {src} -> {tgt}")
    print(f"     File: {v['source_file']}")
    print(f"     Layer: {v['src_pkg']}/ -> {v['tgt_pkg']}/")
    print(f"     Rule: {v['rule']['message']}")


# ── Restore ──────────────────────────────────────────────────────────────

views_path.write_text(original_views, encoding="utf-8")
components_path.write_text(original_components, encoding="utf-8")
print(f"\n{'='*70}")
print("Files restored to original state")


# ── Final Verdict ─────────────────────────────────────────────────────────

print(f"\n{'='*70}")
print("FINAL VERDICT")
print(f"{'='*70}")

expected_violations = 2
actual_violations = len(violations_found)
new_import_count = len(new_imports)
noise = new_import_count - actual_violations

print(f"\nExpected violations: {expected_violations}")
print(f"Detected violations: {actual_violations}")
print(f"New import edges total: {new_import_count}")
print(f"Noise (non-violation imports): {noise}")

print(f"\nViolation 1 (views.py -> database_models): ", end="")
v1 = any(v["edge"][1] == "database_models" and "views" in v["source_file"] for v in violations_found)
print("DETECTED" if v1 else "MISSED")

print(f"Violation 2 (components.py -> services_payment): ", end="")
v2 = any(v["edge"][1] == "services_payment" and "components" in v["source_file"] for v in violations_found)
print("DETECTED" if v2 else "MISSED")

if actual_violations >= 2 and noise <= 3:
    print(f"\n  >>> GO <<<")
    print(f"  Signal klar. {actual_violations} Violations erkannt. Noise: {noise}")
elif actual_violations >= 1:
    print(f"\n  >>> GO MIT EINSCHRAENKUNGEN <<<")
    print(f"  Signal teilweise vorhanden. Noise: {noise}")
else:
    print(f"\n  >>> NO-GO <<<")
    print(f"  Signal nicht erkennbar.")
