from app.services.report_generation_service import ReportGenerationService


def dashboard_payload():
    return {
        "repository_metadata": {"full_name": "owner/sample", "owner": {"login": "owner"}, "html_url": "https://github.com/owner/sample", "default_branch": "main", "primary_language": "Python", "description": "Sample repository", "stargazers_count": 4, "topics": ["python"]},
        "clone_result": {"owner": "owner", "repository": "sample", "branch": "main", "status": "cloned"},
        "static_analysis_result": {"total_files": 4, "total_directories": 1, "supported_source_files": 2, "total_lines": 30, "blank_lines": 3, "comment_lines": 2, "directory_tree": {"name": "sample", "type": "directory", "children": [{"name": "main.py", "type": "file"}]}, "ignored_directories": ["node_modules"]},
        "git_history_result": {"total_commits": 2, "contributors": [{"name": "A Developer", "commits": 2}]},
        "repository_metrics_result": {"overall_health_score": {"score": 70, "evidence": ["README detected"], "reasons": []}},
        "analytics": {"health_gauge": {"value": 70, "min": 0, "max": 100, "label": "Health", "status": "Good"}, "overview_cards": [{"label": "Files", "value": 4}]},
        "advanced_visualizations": {"summary": {"total_files": 4}, "languages": [{"name": "Python", "count": 2, "percentage": 100}], "extensions": [{"name": ".py", "count": 2, "percentage": 50}], "technologies": [], "dependency_graph": {"nodes": [], "edges": []}, "architecture": {"nodes": [], "edges": []}, "workflow": {"workflows": [{"id": "w", "name": "Sample flow", "steps": [{"id": "s", "label": "Start", "kind": "start", "path": "main.py", "line": 1}], "edges": []}]}},
        "ai_insights": None,
        "generated_at": "2026-11-17T00:00:00Z",
    }


def test_generates_valid_pdf_for_complete_dashboard_payload():
    pdf = ReportGenerationService().generate(dashboard_payload())
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 5000


def test_report_handles_missing_optional_analysis_modules():
    payload = dashboard_payload()
    payload["advanced_visualizations"] = None
    payload["ai_insights"] = None
    payload["git_history_result"] = {}
    pdf = ReportGenerationService().generate(payload)
    assert pdf.startswith(b"%PDF-")


def test_report_redacts_credentials_and_local_paths():
    payload = dashboard_payload()
    payload["static_analysis_result"]["local_path"] = "/private/workspace/repo"
    payload["repository_metadata"]["token"] = "ghp_abcdefghijklmnopqrstuv123456"
    pdf = ReportGenerationService().generate(payload)
    assert b"/private/workspace/repo" not in pdf
    assert b"ghp_abcdefghijklmnopqrstuv123456" not in pdf


def test_report_supports_unicode_repository_names_and_large_tables():
    payload = dashboard_payload()
    payload["repository_metadata"]["full_name"] = "owner/caf\u00e9-project"
    payload["advanced_visualizations"]["technologies"] = [
        {"name": f"Library {i}", "category": "dependency", "evidence": "pyproject.toml"}
        for i in range(90)
    ]
    pdf = ReportGenerationService().generate(payload)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 8000


def test_report_renders_directed_architecture_and_branching_workflow_diagrams():
    payload = dashboard_payload()
    payload["advanced_visualizations"]["architecture"] = {
        "nodes": [
            {"id": "api", "label": "API Layer"},
            {"id": "service", "label": "Service Layer"},
            {"id": "data", "label": "Data Layer"},
        ],
        "edges": [
            {"source": "api", "target": "service", "type": "imports", "evidence": "api.py"},
            {"source": "service", "target": "data", "type": "calls", "evidence": "service.py"},
        ],
    }
    payload["advanced_visualizations"]["workflow"]["workflows"][0]["steps"] = [
        {"id": "start", "label": "Start"},
        {"id": "decision", "label": "Valid input?", "kind": "decision"},
        {"id": "ok", "label": "Process request"},
        {"id": "error", "label": "Handle exception", "kind": "error"},
    ]
    payload["advanced_visualizations"]["workflow"]["workflows"][0]["edges"] = [
        {"source": "start", "target": "decision"},
        {"source": "decision", "target": "ok", "label": "True"},
        {"source": "decision", "target": "error", "label": "False"},
    ]
    pdf = ReportGenerationService().generate(payload)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 6000


def test_report_supports_cjk_repository_names():
    from io import BytesIO
    from pypdf import PdfReader

    payload = dashboard_payload()
    payload["repository_metadata"]["full_name"] = "owner/café-東京"
    pdf = ReportGenerationService().generate(payload)
    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf)).pages)
    assert "café" in text
    assert "東京" in text


def test_report_is_compact_and_excludes_commit_history_and_raw_graph_inventory():
    from io import BytesIO
    from pypdf import PdfReader

    payload = dashboard_payload()
    payload["git_history_result"] = {"total_commits": 98765, "commits": [{"message": "MUST NOT APPEAR"}] * 500}
    payload["advanced_visualizations"]["dependency_graph"] = {
        "nodes": [{"id": f"node-{i}", "label": f"Component {i}", "path": f"src/{i}.py"} for i in range(500)],
        "edges": [{"source": f"node-{i}", "target": f"node-{i+1}", "type": "imports"} for i in range(499)],
    }
    pdf = ReportGenerationService().generate(payload)
    reader = PdfReader(BytesIO(pdf))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert len(reader.pages) <= 8
    assert "MUST NOT APPEAR" not in text
    assert "98765" not in text
    assert "500 detected nodes" in text



def test_sparse_architecture_graph_keeps_component_cards_readable():
    from app.services.report_generation_service import DiagramFlowable

    nodes = [{"id": f"component-{i}", "label": f"openjarvis module group {i}"} for i in range(18)]
    edges = [
        {"source": "component-0", "target": "component-1", "type": "imports"},
        {"source": "component-3", "target": "component-4", "type": "calls"},
        {"source": "component-7", "target": "component-8", "type": "uses"},
        {"source": "component-12", "target": "component-13", "type": "imports"},
    ]
    diagram = DiagramFlowable("Architecture", nodes, edges)

    # Sparse graphs must not turn isolated components into one-pixel columns.
    assert diagram.columns == 3
    assert diagram.card_w > 45 * 2.8346  # >45 mm in points
    assert diagram.rows == 6
    assert len(diagram.valid) == 4
    assert diagram.height > 100 * 2.8346  # enough vertical room for six card rows
