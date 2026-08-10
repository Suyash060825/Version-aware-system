"""
blueprints/knowledge_graph.py
Module: Real Interactive Policy Knowledge Graph

The chatbot can claim policies are "connected" in prose, but that's just an
LLM assertion — this builds an actual, clickable graph straight from the
existing SQLAlchemy relationships:

  Department -> Policy -> PolicyVersion -> ApprovalWorkflow
  Meeting -> MeetingDecision -> Policy   (a meeting "led to" a policy)

so people can literally trace "why does this policy exist" back through
the meetings and decisions that produced it, and through to who approved
which version. Purely relational — zero LLM needed.

Routes:
  GET /admin/knowledge-graph          page (vis-network canvas)
  GET /admin/knowledge-graph/data     JSON {nodes, edges} for the canvas
"""
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required

from models import Policy, Department, ApprovalWorkflow, UserRole
from utils import role_required

knowledge_graph_bp = Blueprint("knowledge_graph", __name__, url_prefix="/admin")

NODE_COLORS = {
    "department": "#2a4a38",
    "policy": "#1d5c8a",
    "version": "#6b7280",
    "approval": "#8a6d1d",
    "meeting": "#7a2a8a",
    "decision": "#b1442e",
}

# Plain-language explanations shown in the "how to read this" guide and in
# each node's detail panel — the whole point of this graph is that someone
# with zero technical background should be able to look at a node and know
# in one sentence what it means.
NODE_KIND_INFO = {
    "department": {
        "plain_name": "Department",
        "explains": "A team in the company (like HR or IT) that owns and is responsible for a policy.",
    },
    "policy": {
        "plain_name": "Policy",
        "explains": "An official company rule or guideline that employees are expected to follow.",
    },
    "version": {
        "plain_name": "Policy version",
        "explains": "A specific draft or edition of a policy. Policies change over time, and each change creates a new version.",
    },
    "approval": {
        "plain_name": "Approval step",
        "explains": "A sign-off a policy version needed before it became official, and who gave it.",
    },
    "meeting": {
        "plain_name": "Meeting",
        "explains": "A real meeting where people talked about a policy — this is where the paper trail starts.",
    },
    "decision": {
        "plain_name": "Decision",
        "explains": "A specific choice made in a meeting that directly caused a policy to be created or changed.",
    },
}


def _build_graph(limit_policies: int = 60) -> dict:
    nodes, edges = [], []
    seen = set()

    def add_node(node_id, label, group, **extra):
        if node_id in seen:
            return
        seen.add(node_id)
        info = NODE_KIND_INFO.get(group, {})
        nodes.append({
            "id": node_id, "label": label, "group": group,
            "color": NODE_COLORS.get(group, "#999"),
            "kind_label": info.get("plain_name", group.title()),
            "explains": info.get("explains", ""),
            **extra,
        })

    def add_edge(a, b, label=None):
        edges.append({"from": a, "to": b, **({"label": label} if label else {})})

    for d in Department.query.all():
        add_node(f"dept-{d.id}", d.name, "department")

    policies = Policy.query.order_by(Policy.updated_at.desc()).limit(limit_policies).all()
    for p in policies:
        pid = f"policy-{p.id}"
        add_node(pid, p.title, "policy", policy_id=p.id, url=f"/policies/{p.id}")
        if p.department_id:
            add_edge(f"dept-{p.department_id}", pid, "manages")

        for v in p.versions.limit(5).all():
            vid = f"version-{v.id}"
            add_node(vid, v.version_label, "version")
            add_edge(pid, vid, "has this version")

            for appr in ApprovalWorkflow.query.filter_by(version_id=v.id).all():
                aid = f"approval-{appr.id}"
                actor_label = appr.actor.name if appr.actor else "unassigned"
                add_node(aid, f"{appr.stage.replace('_', ' ').title()} — {actor_label}", "approval",
                         status=appr.status)
                add_edge(vid, aid, "approved by")

        for meeting in p.related_meetings.all():
            mid = f"meeting-{meeting.id}"
            add_node(mid, meeting.title, "meeting", meeting_code=meeting.meeting_code)
            add_edge(mid, pid, "was discussed at")

            for dec in meeting.decisions.limit(5).all():
                did = f"decision-{dec.id}"
                add_node(did, (dec.description or "")[:60], "decision")
                add_edge(mid, did, "led to the decision")
                add_edge(did, pid, "which produced")

    return {"nodes": nodes, "edges": edges}


@knowledge_graph_bp.route("/knowledge-graph")
@login_required
@role_required(UserRole.ADMIN, UserRole.HR)
def graph_page():
    return render_template("admin/knowledge_graph.html")


@knowledge_graph_bp.route("/knowledge-graph/data")
@login_required
@role_required(UserRole.ADMIN, UserRole.HR)
def graph_data():
    limit = request.args.get("limit", 60, type=int)
    return jsonify(_build_graph(limit_policies=limit))
