
import pytest

from app.services.analyzer import analyze_plan


def test_analyze_root_sequential_scan():
    plan = {
        "Plan": {
            "Node Type": "Seq Scan",
            "Relation Name": "employees",
            "Rows Removed by Filter": 100
        }
    }

    result = analyze_plan(plan)

    assert result["node_type"] == "Seq Scan"

    finding_types = [
        finding["type"]
        for finding in result["findings"]
    ]

    assert "SEQUENTIAL_SCAN" in finding_types
    assert "FILTERED_ROWS" in finding_types


def test_analyze_nested_bitmap_index_scan():
    plan = {
        "Plan": {
            "Node Type": "Bitmap Heap Scan",
            "Relation Name": "employees",
            "Plans": [
                {
                    "Node Type": "Bitmap Index Scan",
                    "Index Name": "idx_employees_dept_id"
                }
            ]
        }
    }

    result = analyze_plan(plan)

    assert result["node_type"] == "Bitmap Heap Scan"

    node_types = [
        node["node_type"]
        for node in result["analyzed_nodes"]
    ]

    assert "Bitmap Heap Scan" in node_types
    assert "Bitmap Index Scan" in node_types


def test_analyze_nested_sequential_scan():
    plan = {
        "Plan": {
            "Node Type": "Nested Loop",
            "Plans": [
                {
                    "Node Type": "Seq Scan",
                    "Relation Name": "employees",
                    "Rows Removed by Filter": 50
                },
                {
                    "Node Type": "Index Scan",
                    "Relation Name": "departments"
                }
            ]
        }
    }

    result = analyze_plan(plan)

    finding_types = [
        finding["type"]
        for finding in result["findings"]
    ]

    assert "SEQUENTIAL_SCAN" in finding_types
    assert "FILTERED_ROWS" in finding_types

    assert len(result["analyzed_nodes"]) == 3


def test_analyze_plan_without_findings():
    plan = {
        "Plan": {
            "Node Type": "Index Scan",
            "Relation Name": "employees"
        }
    }

    result = analyze_plan(plan)

    assert result["node_type"] == "Index Scan"
    assert result["findings"] == []


def test_analyze_invalid_plan():
    with pytest.raises(ValueError):
        analyze_plan({})


def test_analyze_multiple_nested_nodes():
    plan = {
        "Plan": {
            "Node Type": "Hash Join",
            "Plans": [
                {
                    "Node Type": "Seq Scan",
                    "Relation Name": "employees",
                    "Rows Removed by Filter": 20
                },
                {
                    "Node Type": "Hash",
                    "Plans": [
                        {
                            "Node Type": "Seq Scan",
                            "Relation Name": "departments",
                            "Rows Removed by Filter": 5
                        }
                    ]
                }
            ]
        }
    }

    result = analyze_plan(plan)

    sequential_scans = [
        finding
        for finding in result["findings"]
        if finding["type"] == "SEQUENTIAL_SCAN"
    ]

    assert len(sequential_scans) == 2
    assert len(result["analyzed_nodes"]) == 4