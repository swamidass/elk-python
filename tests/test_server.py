"""Tests for the ELK server layout computation."""

import pytest

from elk.server import compute_layout, shutdown_server


def test_valid_layout():
    """Test computing layout for a valid graph."""
    # Simple graph with two nodes and one edge
    graph = {
        "id": "root",
        "layoutOptions": {"elk.algorithm": "layered"},
        "children": [
            {"id": "n1", "width": 30, "height": 30},
            {"id": "n2", "width": 30, "height": 30},
        ],
        "edges": [{"id": "e1", "sources": ["n1"], "targets": ["n2"]}],
    }

    try:
        # Compute layout
        layout = compute_layout(graph)

        # Verify the layout contains all expected elements
        assert "root" in layout
        assert "n1" in layout
        assert "n2" in layout
        assert "e1" in layout

        # Verify root has position and size
        assert "position" in layout["root"]
        assert "size" in layout["root"]
        assert "x" in layout["root"]["position"]
        assert "y" in layout["root"]["position"]
        assert "width" in layout["root"]["size"]
        assert "height" in layout["root"]["size"]

        # Verify nodes have positions and sizes
        for node_id in ["n1", "n2"]:
            assert "position" in layout[node_id]
            assert "size" in layout[node_id]
            assert layout[node_id]["size"]["width"] == 30
            assert layout[node_id]["size"]["height"] == 30

        # Verify edge has route points
        assert "route" in layout["e1"]
        assert len(layout["e1"]["route"]) >= 2  # At least start and end points

        # Verify layout places n1 to the left of n2 (layered algorithm)
        assert layout["n1"]["position"]["x"] < layout["n2"]["position"]["x"]

    finally:
        shutdown_server()


def test_invalid_layout():
    """Test computing layout for an invalid graph."""
    # Invalid graph missing required fields
    invalid_graph = {
        "id": "root",
        "children": [
            # Missing width and height
            {"id": "n1"},
            {"id": "n2"},
        ],
        "edges": [
            {
                "id": "e1",
                # Invalid: missing sources and targets
            }
        ],
    }

    with pytest.raises(RuntimeError) as exc_info:
        compute_layout(invalid_graph)

    # Verify error message indicates the problem
    error = str(exc_info.value)
    assert "ELK server" in error

    # Clean up
    shutdown_server()


def test_multiple_layouts():
    """Test computing multiple layouts reuses the same server process."""
    simple_graph = {"id": "root", "children": [{"id": "n1", "width": 30, "height": 30}]}

    try:
        # First layout should start the server
        layout1 = compute_layout(simple_graph)
        assert layout1["n1"]["size"]["width"] == 30

        # Second layout should reuse the server
        layout2 = compute_layout(simple_graph)
        assert layout2["n1"]["size"]["width"] == 30

        # Both layouts should be valid but potentially different
        assert layout1 == layout2  # Same input should give same output

    finally:
        shutdown_server()
