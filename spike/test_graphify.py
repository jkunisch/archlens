"""
ArchLens Spike — Graphify Go/No-Go Validation

Tests:
1. Python import path for Graphify
2. AST extraction on dummy_repo
3. Graph building + JSON export
4. Boundary violation detection via graph_diff
"""
import json
import sys
from pathlib import Path

# ── Step 1: Test Python Import Paths ─────────────────────────────────────────

print("=" * 70)
print("STEP 1: Testing Graphify Python Import Paths")
print("=" * 70)

import_results = {}

# Test 1a: from graphify.analyze import graph_diff
try:
    from graphify.analyze import graph_diff
    import_results["from graphify.analyze import graph_diff"] = "✅ SUCCESS"
    print("✅ from graphify.analyze import graph_diff — WORKS")
except ImportError as e:
    import_results["from graphify.analyze import graph_diff"] = f"❌ FAIL: {e}"
    print(f"❌ from graphify.analyze import graph_diff — FAIL: {e}")

# Test 1b: from graphify.extract import extract, collect_files
try:
    from graphify.extract import extract, collect_files
    import_results["from graphify.extract import extract, collect_files"] = "✅ SUCCESS"
    print("✅ from graphify.extract import extract, collect_files — WORKS")
except ImportError as e:
    import_results["from graphify.extract import extract, collect_files"] = f"❌ FAIL: {e}"
    print(f"❌ from graphify.extract import extract, collect_files — FAIL: {e}")

# Test 1c: from graphify.build import build_from_json
try:
    from graphify.build import build_from_json
    import_results["from graphify.build import build_from_json"] = "✅ SUCCESS"
    print("✅ from graphify.build import build_from_json — WORKS")
except ImportError as e:
    import_results["from graphify.build import build_from_json"] = f"❌ FAIL: {e}"
    print(f"❌ from graphify.build import build_from_json — FAIL: {e}")

# Test 1d: from graphify.cluster import cluster
try:
    from graphify.cluster import cluster
    import_results["from graphify.cluster import cluster"] = "✅ SUCCESS"
    print("✅ from graphify.cluster import cluster — WORKS")
except ImportError as e:
    import_results["from graphify.cluster import cluster"] = f"❌ FAIL: {e}"
    print(f"❌ from graphify.cluster import cluster — FAIL: {e}")

# Test 1e: from graphify.export import to_json
try:
    from graphify.export import to_json
    import_results["from graphify.export import to_json"] = "✅ SUCCESS"
    print("✅ from graphify.export import to_json — WORKS")
except ImportError as e:
    import_results["from graphify.export import to_json"] = f"❌ FAIL: {e}"
    print(f"❌ from graphify.export import to_json — FAIL: {e}")

# Test 1f: graphify top-level lazy imports
try:
    import graphify
    _ = graphify.extract  # triggers lazy import
    import_results["import graphify (lazy)"] = "✅ SUCCESS"
    print("✅ import graphify (lazy attrs) — WORKS")
except Exception as e:
    import_results["import graphify (lazy)"] = f"❌ FAIL: {e}"
    print(f"❌ import graphify (lazy attrs) — FAIL: {e}")


# ── Step 2: Build Base Graph (BEFORE violations) ────────────────────────────

print("\n" + "=" * 70)
print("STEP 2: Building Base Graph (clean architecture)")
print("=" * 70)

dummy_repo = Path(__file__).parent / "dummy_repo"
spike_dir = Path(__file__).parent

# Collect all Python files
files = collect_files(dummy_repo)
print(f"\nCollected {len(files)} files:")
for f in sorted(files):
    print(f"  {f}")

# Extract AST
print("\nRunning AST extraction...")
extraction = extract(files)
n_nodes = len(extraction.get("nodes", []))
n_edges = len(extraction.get("edges", []))
print(f"Extraction result: {n_nodes} nodes, {n_edges} edges")

# Build NetworkX graph
base_graph = build_from_json(extraction)
print(f"NetworkX graph: {base_graph.number_of_nodes()} nodes, {base_graph.number_of_edges()} edges")

# Cluster
communities = cluster(base_graph)
print(f"Communities: {len(communities)}")
for cid, members in communities.items():
    print(f"  [{cid}] Community {cid}: {len(members)} nodes")

# Save base_graph.json
base_json_path = spike_dir / "base_graph.json"
to_json(base_graph, communities, str(base_json_path))
print(f"\n✅ Base graph saved to {base_json_path}")

# Print all edges for inspection
print("\nBase graph edges:")
for u, v, data in base_graph.edges(data=True):
    src_label = base_graph.nodes[u].get("label", u)
    tgt_label = base_graph.nodes[v].get("label", v)
    relation = data.get("relation", "?")
    confidence = data.get("confidence", "?")
    print(f"  {src_label} --[{relation}]--> {tgt_label}  ({confidence})")


# ── Step 3: Introduce Violations ─────────────────────────────────────────────

print("\n" + "=" * 70)
print("STEP 3: Introducing Boundary Violations")
print("=" * 70)

# Read original views.py
views_path = dummy_repo / "frontend" / "views.py"
original_views = views_path.read_text(encoding="utf-8")

# Add violation: frontend imports directly from database
violation_views = '''"""Frontend views - renders pages by calling the API layer."""
from api.routes import OrderRoutes, AuthRoutes

# VIOLATION: Frontend greift direkt auf Database zu (sollte ueber api/ gehen)
from database.models import User


def render_template(template_name: str, data: dict) -> str:
    """Render an HTML template with data."""
    return f"<div class=\'{template_name}\'>{data}</div>"


class DashboardView:
    """Dashboard page view."""

    def __init__(self, order_routes: OrderRoutes):
        self.order_routes = order_routes

    def render(self, request: dict) -> str:
        """Render the dashboard page."""
        orders = self.order_routes.get_orders(request)
        return render_template("dashboard", {"orders": orders})


class LoginView:
    """Login page view."""

    def __init__(self, auth_routes: AuthRoutes):
        self.auth_routes = auth_routes

    def render(self, request: dict) -> str:
        """Render the login page."""
        return render_template("login", {"action": "/login"})


class UserProfileView:
    """VIOLATION: Directly accesses database models from frontend."""

    def render(self, user_id: str) -> str:
        """Render user profile - BAD: uses DB model directly."""
        user = User(name="test", email="test@test.com")
        return render_template("profile", {"user": user.name})
'''

# Read original components.py
components_path = dummy_repo / "frontend" / "components.py"
original_components = components_path.read_text(encoding="utf-8")

# Add violation: frontend imports from services
violation_components = '''"""Frontend UI components."""
from frontend.views import render_template

# VIOLATION: Frontend importiert aus services/ (sollte ueber api/ gehen)
from services.payment import PaymentService


class ProductCard:
    """Renders a product card in the UI."""

    def __init__(self, name: str, price: str, image_url: str):
        self.name = name
        self.price = price
        self.image_url = image_url

    def render(self) -> str:
        """Render the product card as HTML."""
        template_data = {
            "name": self.name,
            "price": self.price,
            "image": self.image_url,
        }
        return render_template("product_card", template_data)


class NavigationBar:
    """Top navigation bar component."""

    def __init__(self, items: list[str]):
        self.items = items

    def render(self) -> str:
        """Render navigation bar."""
        links = " | ".join(self.items)
        return f"<nav>{links}</nav>"


class PaymentWidget:
    """VIOLATION: Directly uses PaymentService from frontend."""

    def __init__(self, payment_service: PaymentService):
        self.payment_service = payment_service

    def render_payment_form(self) -> str:
        """Render payment form - BAD: uses service directly."""
        return render_template("payment_form", {"methods": ["card", "paypal"]})
'''

# Write violated files
views_path.write_text(violation_views, encoding="utf-8")
components_path.write_text(violation_components, encoding="utf-8")
print("✅ Violation 1: frontend/views.py → database/models.py (from database.models import User)")
print("✅ Violation 2: frontend/components.py → services/payment.py (from services.payment import PaymentService)")


# ── Step 4: Build Head Graph (AFTER violations) ──────────────────────────────

print("\n" + "=" * 70)
print("STEP 4: Building Head Graph (with violations)")
print("=" * 70)

# Re-collect and extract
files_head = collect_files(dummy_repo)
extraction_head = extract(files_head)
n_nodes_head = len(extraction_head.get("nodes", []))
n_edges_head = len(extraction_head.get("edges", []))
print(f"Extraction result: {n_nodes_head} nodes, {n_edges_head} edges")

head_graph = build_from_json(extraction_head)
print(f"NetworkX graph: {head_graph.number_of_nodes()} nodes, {head_graph.number_of_edges()} edges")

communities_head = cluster(head_graph)

# Save head_graph.json
head_json_path = spike_dir / "head_graph.json"
to_json(head_graph, communities_head, str(head_json_path))
print(f"✅ Head graph saved to {head_json_path}")

# Print all edges
print("\nHead graph edges:")
for u, v, data in head_graph.edges(data=True):
    src_label = head_graph.nodes[u].get("label", u)
    tgt_label = head_graph.nodes[v].get("label", v)
    relation = data.get("relation", "?")
    confidence = data.get("confidence", "?")
    print(f"  {src_label} --[{relation}]--> {tgt_label}  ({confidence})")


# ── Step 5: Graph Diff ────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("STEP 5: Graph Diff — Signal-to-Noise Analysis")
print("=" * 70)

diff = graph_diff(base_graph, head_graph)

print(f"\nSummary: {diff['summary']}")

print(f"\n--- NEW NODES ({len(diff['new_nodes'])}) ---")
for node in diff["new_nodes"]:
    print(f"  + {node['label']} (id: {node['id']})")

print(f"\n--- REMOVED NODES ({len(diff['removed_nodes'])}) ---")
for node in diff["removed_nodes"]:
    print(f"  - {node['label']} (id: {node['id']})")

print(f"\n--- NEW EDGES ({len(diff['new_edges'])}) ---")
for edge in diff["new_edges"]:
    src_label = head_graph.nodes.get(edge['source'], {}).get('label', edge['source'])
    tgt_label = head_graph.nodes.get(edge['target'], {}).get('label', edge['target'])
    print(f"  + {src_label} --[{edge['relation']}]--> {tgt_label}  ({edge['confidence']})")

print(f"\n--- REMOVED EDGES ({len(diff['removed_edges'])}) ---")
for edge in diff["removed_edges"]:
    src_label = base_graph.nodes.get(edge['source'], {}).get('label', edge['source'])
    tgt_label = base_graph.nodes.get(edge['target'], {}).get('label', edge['target'])
    print(f"  - {src_label} --[{edge['relation']}]--> {tgt_label}  ({edge['confidence']})")

# Save diff output
diff_path = spike_dir / "diff_output.json"
with open(diff_path, "w") as f:
    json.dump(diff, f, indent=2)
print(f"\n✅ Diff saved to {diff_path}")


# ── Step 6: Signal-to-Noise Evaluation ────────────────────────────────────────

print("\n" + "=" * 70)
print("STEP 6: Signal-to-Noise Evaluation")
print("=" * 70)

# Identify which new edges are the violations
violation_edges = []
noise_edges = []
expected_violation_patterns = [
    ("database", "models"),    # views.py → database.models
    ("services", "payment"),   # components.py → services.payment
]

for edge in diff["new_edges"]:
    src = edge["source"]
    tgt = edge["target"]
    src_label = head_graph.nodes.get(src, {}).get("label", src)
    tgt_label = head_graph.nodes.get(tgt, {}).get("label", tgt)
    src_file = head_graph.nodes.get(src, {}).get("source_file", "")
    tgt_file = head_graph.nodes.get(tgt, {}).get("source_file", "")
    
    is_violation = False
    for pattern_pkg, pattern_mod in expected_violation_patterns:
        if (pattern_pkg in src_file or pattern_pkg in tgt_file or 
            pattern_pkg in src or pattern_pkg in tgt or
            pattern_mod in src_label.lower() or pattern_mod in tgt_label.lower()):
            # Check if this connects frontend to database or services
            if ("frontend" in src_file or "frontend" in tgt_file or
                "views" in src_label.lower() or "components" in src_label.lower() or
                "views" in src or "components" in src):
                is_violation = True
                break
    
    if is_violation:
        violation_edges.append(edge)
    else:
        noise_edges.append(edge)

print(f"\n🎯 VIOLATION EDGES (expected): {len(violation_edges)}")
for edge in violation_edges:
    src_label = head_graph.nodes.get(edge['source'], {}).get('label', edge['source'])
    tgt_label = head_graph.nodes.get(edge['target'], {}).get('label', edge['target'])
    print(f"  🔴 {src_label} --[{edge['relation']}]--> {tgt_label}")

print(f"\n📢 NOISE EDGES (unexpected): {len(noise_edges)}")
for edge in noise_edges:
    src_label = head_graph.nodes.get(edge['source'], {}).get('label', edge['source'])
    tgt_label = head_graph.nodes.get(edge['target'], {}).get('label', edge['target'])
    print(f"  ⚪ {src_label} --[{edge['relation']}]--> {tgt_label}")


# ── Restore original files ───────────────────────────────────────────────────

views_path.write_text(original_views, encoding="utf-8")
components_path.write_text(original_components, encoding="utf-8")
print("\n✅ Original files restored")


# ── Final Summary ─────────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("FINAL SUMMARY")
print("=" * 70)

signal_count = len(violation_edges)
noise_count = len(noise_edges)
total_new = len(diff["new_edges"])

print(f"\nImport Tests: {sum(1 for v in import_results.values() if '✅' in v)}/{len(import_results)} passed")
print(f"Base Graph:   {base_graph.number_of_nodes()} nodes, {base_graph.number_of_edges()} edges")
print(f"Head Graph:   {head_graph.number_of_nodes()} nodes, {head_graph.number_of_edges()} edges")
print(f"Diff:         {diff['summary']}")
print(f"Signal:       {signal_count} violation edges detected")
print(f"Noise:        {noise_count} non-violation edges")
print(f"New Nodes:    {len(diff['new_nodes'])}")
print(f"Removed:      {len(diff['removed_nodes'])} nodes, {len(diff['removed_edges'])} edges")

if signal_count >= 1 and noise_count <= 5:
    verdict = "✅ GO"
    reason = f"Clear signal ({signal_count} violations detected), acceptable noise ({noise_count} extra edges)"
elif signal_count >= 1 and noise_count <= 10:
    verdict = "🟡 GO WITH CONDITIONS"
    reason = f"Signal present ({signal_count}) but noise needs filtering ({noise_count} extra edges)"
elif signal_count == 0:
    verdict = "❌ NO-GO"
    reason = "Violations not detected as new edges — graph_diff doesn't surface boundary violations"
else:
    verdict = "❌ NO-GO"
    reason = f"Noise overwhelms signal: {noise_count} noise vs {signal_count} signal"

print(f"\n{'='*70}")
print(f"  GO/NO-GO VERDICT: {verdict}")
print(f"  Reason: {reason}")
print(f"{'='*70}")
