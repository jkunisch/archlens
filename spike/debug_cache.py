"""Debug: check if extraction cache interferes."""
from pathlib import Path
from graphify.extract import extract, collect_files
from graphify.cache import load_cached
import shutil

dummy = Path("spike/dummy_repo")

# Clear any cache
cache_dir = dummy / ".graphify_cache"
if cache_dir.exists():
    shutil.rmtree(cache_dir)
    print("Cleared .graphify_cache")

# Check current views.py content
views = (dummy / "frontend" / "views.py").read_text()
has_db_import = "database.models" in views
print(f"views.py has database import: {has_db_import}")
print(f"First 200 chars: {views[:200]}")
print()

# Extract
files = collect_files(dummy)
ext = extract(files)

print("Import edges from 'views' source:")
for e in ext["edges"]:
    if e["source"] == "views" and e["relation"] in ("imports", "imports_from"):
        print(f"  {e['source']} -> {e['target']} [{e['relation']}] (file: {e['source_file']})")

print("\nImport edges from 'components' source:")
for e in ext["edges"]:
    if e["source"] == "components" and e["relation"] in ("imports", "imports_from"):
        print(f"  {e['source']} -> {e['target']} [{e['relation']}] (file: {e['source_file']})")
