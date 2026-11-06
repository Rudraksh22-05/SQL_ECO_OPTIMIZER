
def analyze_plan(plan: dict):
    """
    Analyze a PostgreSQL execution plan recursively.

    Detects:
    - Sequential scans
    - Filtered rows
    - Nested execution-plan nodes
    """

    if not isinstance(plan, dict) or "Plan" not in plan:
        raise ValueError("Invalid execution plan.")

    root_plan = plan["Plan"]

    findings = []
    analyzed_nodes = []

    def visit_node(node: dict, path: str = "Plan"):
        if not isinstance(node, dict):
            return

        node_type = node.get("Node Type")
        relation_name = node.get("Relation Name")

        analyzed_nodes.append({
            "node_type": node_type,
            "relation_name": relation_name,
            "path": path
        })

        # Detect sequential scans.
        if node_type == "Seq Scan":
            findings.append({
                "type": "SEQUENTIAL_SCAN",
                "severity": "INFO",
                "node_type": node_type,
                "relation_name": relation_name,
                "path": path,
                "message": (
                    "PostgreSQL used a sequential scan. "
                    "An index may help if the table becomes large."
                )
            })

        # Detect rows removed by filters.
        rows_removed = node.get("Rows Removed by Filter", 0)

        if rows_removed and rows_removed > 0:
            findings.append({
                "type": "FILTERED_ROWS",
                "severity": "INFO",
                "node_type": node_type,
                "relation_name": relation_name,
                "path": path,
                "rows_removed": rows_removed,
                "message": (
                    f"{rows_removed} rows were removed "
                    "by the query filter."
                )
            })

        # Recursively analyze child plan nodes.
        child_plans = node.get("Plans", [])

        if isinstance(child_plans, list):
            for index, child in enumerate(child_plans):
                visit_node(
                    child,
                    path=f"{path}.Plans[{index}]"
                )

    visit_node(root_plan)

    return {
        "node_type": root_plan.get("Node Type"),
        "findings": findings,
        "analyzed_nodes": analyzed_nodes
    }