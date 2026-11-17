from app.services.advanced_visualization_service import analyze_repository


def test_architecture_uses_subsystems_and_detected_import_direction(tmp_path):
    (tmp_path / "api").mkdir()
    (tmp_path / "services").mkdir()
    (tmp_path / "api" / "__init__.py").write_text("")
    (tmp_path / "services" / "__init__.py").write_text("")
    (tmp_path / "services" / "billing.py").write_text("def charge():\n    return True\n")
    (tmp_path / "api" / "routes.py").write_text(
        "from services.billing import charge\n"
        "def create_app():\n    return None\n"
        "@router.post('/charge')\n"
        "def create_charge():\n    return charge()\n"
    )
    result = analyze_repository(str(tmp_path))
    arch = result["architecture"]
    assert arch["nodes"]
    assert any(n["name"] == "api" and n["file_count"] >= 1 for n in arch["nodes"])
    assert any(n["name"] == "services" for n in arch["nodes"])
    assert any(e["confidence"] == "detected" and e["evidence"] for e in arch["edges"])
    # Import direction is importing module -> imported module.
    api = next(n for n in arch["nodes"] if n["name"] == "api")
    services = next(n for n in arch["nodes"] if n["name"] == "services")
    assert any(e["source"] == api["id"] and e["target"] == services["id"] for e in arch["edges"])


def test_workflow_uses_real_entry_and_local_call_sequence(tmp_path):
    (tmp_path / "main.py").write_text(
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n"
        "@app.get('/items')\n"
        "def get_items():\n"
        "    result = load_items()\n"
        "    return result\n"
        "def load_items():\n"
        "    return read_store()\n"
        "def read_store():\n"
        "    return []\n"
    )
    result = analyze_repository(str(tmp_path))
    workflows = result["workflow"]["workflows"]
    route = next(w for w in workflows if "get" in w["name"])
    labels = [step["label"] for step in route["steps"]]
    assert labels[0].startswith("Start")
    assert any("get_items" in label for label in labels)
    assert any("load_items" in label for label in labels)
    assert any("read_store" in label for label in labels)
    assert any(step["kind"] == "end" for step in route["steps"])
    assert all("path" in step and "confidence" in step for step in route["steps"])


def test_dependency_graph_has_direction_and_node_metrics(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("from pkg.b import work\nimport requests\n")
    (tmp_path / "pkg" / "b.py").write_text("def work(): return 1\n")
    result = analyze_repository(str(tmp_path))
    graph = result["dependency_graph"]
    assert graph["nodes"] and graph["edges"]
    assert any(edge["type"] == "internal" and edge["source"] == "pkg/a.py" and edge["target"] == "pkg/b.py" for edge in graph["edges"])
    assert any(edge["type"] == "external-package" and edge["target"] == "external:requests" for edge in graph["edges"])
    assert all("incoming_count" in node and "outgoing_count" in node for node in graph["nodes"])
    assert graph["metrics"]["edge_count"] == len(graph["edges"])


def test_workflow_preserves_branches_and_loops(tmp_path):
    (tmp_path / "main.py").write_text(
        "def main(items):\n"
        "    for item in items:\n"
        "        if item.valid:\n"
        "            save(item)\n"
        "        else:\n"
        "            reject(item)\n"
        "    return True\n"
        "def save(item): return item\n"
        "def reject(item): return None\n"
    )
    result = analyze_repository(str(tmp_path))
    workflow = next(w for w in result["workflow"]["workflows"] if w["entry_point"]["name"] == "main")
    kinds = {step["kind"] for step in workflow["steps"]}
    assert "loop" in kinds and "decision" in kinds and "call" in kinds
    assert any(edge.get("label") == "True" for edge in workflow["edges"])
    assert any(edge.get("label") == "False" for edge in workflow["edges"])
    assert any(edge["type"] == "loop-back" for edge in workflow["edges"])
