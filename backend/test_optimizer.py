
from app.services.optimizer import generate_suggestions


def test_nested_sequential_scan_gets_index_recommendation():
    plan = {
        "Plan": {
            "Node Type": "Hash Join",
            "Plans": [
                {
                    "Node Type": "Seq Scan",
                    "Relation Name": "employees",
                    "Filter": "(dept_id = 5)",
                    "Actual Rows": 100,
                    "Rows Removed by Filter": 1900
                },
                {
                    "Node Type": "Seq Scan",
                    "Relation Name": "departments",
                    "Filter": "(dept_id = 5)",
                    "Actual Rows": 300,
                    "Rows Removed by Filter": 700
                }
            ]
        }
    }

    result = generate_suggestions(plan, "SELECT * FROM employees")

    assert len(result) == 2

    assert result[0]["type"] == "INDEX_RECOMMENDATION"
    assert result[0]["table"] == "employees"
    assert result[0]["column"] == "dept_id"

    assert result[1]["type"] == "SEQUENTIAL_SCAN_ACCEPTABLE"
    assert result[1]["table"] == "departments"


def test_deeply_nested_sequential_scan():
    plan = {
        "Plan": {
            "Node Type": "Aggregate",
            "Plans": [
                {
                    "Node Type": "Hash Join",
                    "Plans": [
                        {
                            "Node Type": "Seq Scan",
                            "Relation Name": "employees",
                            "Filter": "(salary > 50000)",
                            "Actual Rows": 100,
                            "Rows Removed by Filter": 1900
                        }
                    ]
                }
            ]
        }
    }

    result = generate_suggestions(plan, "SELECT * FROM employees")

    assert len(result) == 1
    assert result[0]["type"] == "INDEX_RECOMMENDATION"
    assert result[0]["column"] == "salary"


def test_no_suggestion_for_non_scan_node():
    plan = {
        "Plan": {
            "Node Type": "Index Scan",
            "Relation Name": "employees"
        }
    }

    result = generate_suggestions(plan, "SELECT * FROM employees")

    assert result == []


def test_invalid_plan_raises_error():
    plan = {}

    try:
        generate_suggestions(plan, "SELECT * FROM employees")
        assert False
    except ValueError as error:
        assert str(error) == "Invalid execution plan."