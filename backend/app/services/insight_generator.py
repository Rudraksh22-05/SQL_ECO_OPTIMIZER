from typing import Any


def extract_plan_details(plan: dict[str, Any]) -> dict[str, Any]:
    """
    Extract important execution-plan information from PostgreSQL EXPLAIN JSON.
    """

    root_plan = plan.get("Plan", {})

    node_types = []
    index_names = []
    rows_removed = 0

    def traverse(node: dict[str, Any]) -> None:
        node_type = node.get("Node Type")

        if node_type:
            node_types.append(node_type)

        index_name = node.get("Index Name")

        if index_name:
            index_names.append(index_name)


        if node.get("Rows Removed by Filter"):
            nonlocal_rows_removed[0] += node["Rows Removed by Filter"]

        if node.get("Rows Removed by Index Recheck"):
            nonlocal_rows_removed[0] += node["Rows Removed by Index Recheck"]

        for child in node.get("Plans", []):
            traverse(child)

    nonlocal_rows_removed = [0]

    traverse(root_plan)

    return {
        "node_types": node_types,
        "index_names": index_names,
        "rows_removed": nonlocal_rows_removed[0]
    }


def generate_benchmark_insights(
    baseline_plan: dict[str, Any],
    optimized_plan: dict[str, Any],
    baseline_time_ms: float,
    optimized_time_ms: float,
    improvement_percent: float | None,
    recommendation: dict[str, Any],
    environmental_impact: dict[str, Any],
    cleanup_information: dict[str, Any] | None
) -> dict[str, Any]:
    """
    Generate structured insights comparing baseline and optimized benchmarks.
    """

    baseline_details = extract_plan_details(baseline_plan)
    optimized_details = extract_plan_details(optimized_plan)

    baseline_nodes = baseline_details["node_types"]
    optimized_nodes = optimized_details["node_types"]

    insights = []

    # 1. Execution-time comparison
    if optimized_time_ms < baseline_time_ms:
        insights.append(
            f"Execution time decreased from "
            f"{baseline_time_ms:.3f} ms to "
            f"{optimized_time_ms:.3f} ms."
        )
    elif optimized_time_ms > baseline_time_ms:
        insights.append(
            f"Execution time increased from "
            f"{baseline_time_ms:.3f} ms to "
            f"{optimized_time_ms:.3f} ms."
        )
    else:
        insights.append("Execution time remained unchanged.")

    # 2. Execution-plan comparison
    if baseline_nodes != optimized_nodes:
        insights.append(
            f"Execution plan changed from "
            f"{', '.join(baseline_nodes)} to "
            f"{', '.join(optimized_nodes)}."
        )
    else:
        insights.append("Execution plan node types remained unchanged.")

    # 3. Index usage
    if optimized_details["index_names"]:
        insights.append(
            "The optimized query used an index: "
            + ", ".join(optimized_details["index_names"])
        )
    else:
        insights.append("No index usage was detected in the optimized plan.")

    # 4. Rows removed by filtering
    baseline_removed = baseline_details["rows_removed"]
    optimized_removed = optimized_details["rows_removed"]

    if baseline_removed > optimized_removed:
        insights.append(
            f"Rows removed during filtering decreased from "
            f"{baseline_removed} to {optimized_removed}."
        )
    elif baseline_removed < optimized_removed:
        insights.append(
            f"Rows removed during filtering increased from "
            f"{baseline_removed} to {optimized_removed}."
        )

    # 5. Improvement threshold
    threshold_met = recommendation.get(
        "meets_improvement_threshold",
        False
    )

    if threshold_met:
        insights.append(
            "The measured performance improvement exceeds "
            "the configured improvement threshold."
        )
    else:
        insights.append(
            "The measured performance improvement does not "
            "exceed the configured improvement threshold."
        )

    # 6. Environmental comparison
    baseline_environment = environmental_impact.get("baseline", {})
    optimized_environment = environmental_impact.get("optimized", {})

    baseline_energy = baseline_environment.get("energy_kwh", 0)
    optimized_energy = optimized_environment.get("energy_kwh", 0)

    baseline_carbon = baseline_environment.get("carbon_grams_co2e", 0)
    optimized_carbon = optimized_environment.get("carbon_grams_co2e", 0)

    if optimized_energy < baseline_energy:
        insights.append(
            "The optimized query has lower estimated energy consumption "
            "and carbon emissions."
        )
    elif optimized_energy > baseline_energy:
        insights.append(
            "The optimized query has higher estimated energy consumption "
            "and carbon emissions."
        )

    # 7. Cleanup verification
    cleanup_success = (
        cleanup_information is not None
        and cleanup_information.get("success", False)
    )

    if cleanup_success:
        insights.append(
            "Temporary benchmark indexes were successfully cleaned up."
        )
    else:
        insights.append(
            "Temporary index cleanup was not confirmed."
        )

    return {
        "summary": (
            f"Performance improvement: "
            f"{improvement_percent:.2f}%"
            if improvement_percent is not None
            else "Performance improvement could not be calculated."
        ),
        "baseline": {
            "execution_time_ms": baseline_time_ms,
            "node_types": baseline_nodes,
            "rows_removed": baseline_removed,
            "estimated_energy_kwh": baseline_energy,
            "estimated_carbon_grams_co2e": baseline_carbon
        },
        "optimized": {
            "execution_time_ms": optimized_time_ms,
            "node_types": optimized_nodes,
            "index_names": optimized_details["index_names"],
            "rows_removed": optimized_removed,
            "estimated_energy_kwh": optimized_energy,
            "estimated_carbon_grams_co2e": optimized_carbon
        },
        "improvement_percent": improvement_percent,
        "threshold_met": threshold_met,
        "insights": insights,
        "cleanup_success": cleanup_success
    }