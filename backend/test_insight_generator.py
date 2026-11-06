from app.services.insight_generator import generate_benchmark_insights


baseline_plan = {
    "Plan": {
        "Node Type": "Seq Scan",
        "Rows Removed by Filter": 8743
    }
}

optimized_plan = {
    "Plan": {
        "Node Type": "Bitmap Heap Scan",
        "Plans": [
            {
                "Node Type": "Bitmap Index Scan",
                "Index Name": "eco_test_idx_employees_dept_id"
            }
        ]
    }
}

recommendation = {
    "meets_improvement_threshold": True
}

environmental_impact = {
    "baseline": {
        "energy_kwh": 1.9e-8,
        "carbon_grams_co2e": 9.6e-6
    },
    "optimized": {
        "energy_kwh": 8e-9,
        "carbon_grams_co2e": 4e-6
    }
}

cleanup_information = {
    "success": True
}

result = generate_benchmark_insights(
    baseline_plan=baseline_plan,
    optimized_plan=optimized_plan,
    baseline_time_ms=1.383,
    optimized_time_ms=0.576,
    improvement_percent=58.35,
    recommendation=recommendation,
    environmental_impact=environmental_impact,
    cleanup_information=cleanup_information
)

print(result)