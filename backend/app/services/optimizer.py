
import re


def generate_suggestions(plan: dict, query: str, existing_indexes=None):
    """
    Generate optimization suggestions by recursively
    analyzing PostgreSQL execution-plan nodes.
    """

    if not isinstance(plan, dict) or "Plan" not in plan:
        raise ValueError("Invalid execution plan.")

    suggestions = []

    existing_indexes = existing_indexes or []

    existing_index_pairs = {
        (
            index.get("table"),
            index.get("column")
        )
        for index in existing_indexes
    }
    
    def visit_node(node: dict, path: str = "Plan"):
        if not isinstance(node, dict):
            return

        node_type = node.get("Node Type")
        relation_name = node.get("Relation Name")
        filter_condition = node.get("Filter")

        # Analyze sequential scans at any nesting level
        if (
            node_type == "Seq Scan"
            and relation_name
            and filter_condition
        ):
            column_match = re.search(
                r"\(?(\w+)\s*(?:>=|<=|=|>|<|LIKE|IS)\s*",
                filter_condition,
                re.IGNORECASE
            )

            if column_match:
                column_name = column_match.group(1)

                actual_rows = node.get("Actual Rows", 0)
                rows_removed = node.get(
                    "Rows Removed by Filter",
                    0
                )

                total_rows_examined = (
                    actual_rows + rows_removed
                )

                selectivity = (
                    actual_rows / total_rows_examined
                    if total_rows_examined > 0
                    else 1
                )

                # Recommend an index for selective scans
                if (
                    total_rows_examined >= 1000
                    and selectivity <= 0.20
                ):
                    index_exists = (
                        relation_name,
                        column_name
                    ) in existing_index_pairs

                    if index_exists:
                        suggestions.append({
                            "type": "INDEX_ALREADY_EXISTS",
                            "priority": "LOW",
                            "table": relation_name,
                            "column": column_name,
                            "path": path,
                            "message": (
                                f"An index already exists on "
                                f"'{relation_name}({column_name})'."
                            ),
                            "reason": (
                                "No additional index is recommended "
                                "for this column."
                            )
                        })

                    else:                        
                        suggestions.append({
                            "type": "INDEX_RECOMMENDATION",
                            "priority": "MEDIUM",
                            "table": relation_name,
                            "column": column_name,
                            "path": path,
                            "message": (
                                f"Consider creating an index on "
                                f"'{relation_name}({column_name})'."
                            ),
                            "reason": (
                                "The query scans many rows but "
                                "returns a small percentage of them."
                            )
                        })

                # Explain why an index may not be necessary
                else:
                    suggestions.append({
                        "type": "SEQUENTIAL_SCAN_ACCEPTABLE",
                        "priority": "LOW",
                        "table": relation_name,
                        "column": column_name,
                        "path": path,
                        "message": (
                            "A sequential scan may be appropriate "
                            "because the filter returns a relatively "
                            "large portion of the table or the query "
                            "may not benefit significantly from an index."
                        ),
                        "reason": (
                            f"Approximately {total_rows_examined} "
                            "rows were examined."
                        )
                    })

        # Recursively inspect child nodes
        child_plans = node.get("Plans", [])

        if isinstance(child_plans, list):
            for index, child in enumerate(child_plans):
                visit_node(
                    child,
                    path=f"{path}.Plans[{index}]"
                )

    visit_node(plan["Plan"])

    return suggestions