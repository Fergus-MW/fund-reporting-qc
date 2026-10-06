"""Seed the local stack with the partner fixtures for one signed-in demo workspace.

Local demo only. Ingests the pack into the workspace graph that `email` would own after
Google sign-in, creates Q2 and Q3 fee-review projects, ratifies their inputs, and runs
the terms gate in both modes. Run from the repo root after `make up`:

    SURREAL_URL=http://127.0.0.1:18000 SURREAL_USER=root SURREAL_PASSWORD=local-development-only \
    SURREAL_AUTH_LEVEL=root SURREAL_PROJECT_ADMIN_USER=workflow_provisioner \
    SURREAL_PROJECT_ADMIN_PASSWORD=localProjectProvisionerOnly SURREAL_PROJECT_SECRET=localProjectCredentialKeyOnly \
    PYTHONPATH=services/ingestion .venv/bin/python scripts/demo/seed.py you@example.com /path/to/fixtures
"""
import hashlib, sys
from datetime import date
from pathlib import Path
from app.identity import current_identity
from app.connectors import Item
from app.extraction import Ingestion
from app.store import GraphStore
from app.project_store import ProjectStore
from app.projects import materialize, ratify, snapshot
from app.workflows import run_workflow

email = sys.argv[1]
root = Path(sys.argv[2])
tenant = "u-" + hashlib.sha256(email.lower().encode()).hexdigest()[:16]
current_identity.set({"tenant": tenant, "actor": email, "kind": "user"})
store = GraphStore(); graph = store.load_graph()
def ingest(f, **o):
    p = root / f
    return Ingestion(graph, store, **o).ingest(Item("drive", email, f, p.name, p.read_bytes()))
src = {l: ingest(f) for l, f in (("entity_terms", "stage0_baseline/entity_terms_v1.csv"),
    ("q2", "stage1_error_injected/q2_2026_fee_and_commitment_schedule_ADMIN_DRAFT.xlsx"),
    ("q3", "stage2_email/q3_2026_fee_and_commitment_schedule_ADMIN_DRAFT.xlsx"),
    ("letter", "stage0_baseline/side_letter_v1_Trentcombe_2024-03-15.md"))}
fund = next(e.key for e in graph.state.entities.values() if e.kind == "fund")
src["v1"] = ingest("stage0_baseline/terms_table_v1.csv", fund_id=fund, snapshot_as_of="2026-06-30")
src["v2"] = ingest("stage2_email/terms_table_v2.csv", fund_id=fund, snapshot_as_of="2026-07-01")
company = graph.upsert("company", "Kestrel Lammwick Management", src["entity_terms"])
projects = {q: graph.upsert("project", q + " fee review", src["entity_terms"], fund_id=fund,
            management_company_id=company, quarter=q, workflow_type="fee_run") for q in ("2026-Q2", "2026-Q3")}
store.save_graph(graph)
for q, draft, as_of in (("2026-Q2", "q2", date(2026, 6, 30)), ("2026-Q3", "q3", date(2026, 9, 30))):
    result = materialize(GraphStore(), projects[q], [src[l] for l in ("entity_terms", "v1", "v2", "letter", draft)])
    ps = ProjectStore(projects[q])
    orig = {sid: a["key"] for a in result["artifacts"] if a["role"] == "original" for sid in a["source_ids"]}
    arith = run_workflow(ps, "terms", "arithmetic-only", {"draft": orig[src[draft]]})
    inputs = {"draft": orig[src[draft]], "terms": snapshot(ps, as_of)["key"], "entity_terms": orig[src["entity_terms"]]}
    approvals = {r: ratify(ps, inputs[r], email, [src["letter"]], "Reviewed against the Trentcombe side letter")["key"]
                 for r in ("terms", "entity_terms")}
    run = run_workflow(ps, "terms", "terms", inputs, approvals)
    print(q, projects[q], "arithmetic:", arith["status"], arith["output"].get("summary"),
          "terms:", run["status"], run["output"].get("summary"))
print("tenant", tenant)
