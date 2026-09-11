# 等价类测试
def test_shortest_path_returns_reachable_directed_path(client):
    response = client.post(
        "/api/shortest-path",
        json={
            "source": "A",
            "target": "C",
            "links": [
                {"source": "A", "target": "B"},
                {"source": "B", "target": "C"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"path": ["A", "B", "C"]}


def test_shortest_path_returns_404_when_no_directed_path(client):
    response = client.post(
        "/api/shortest-path",
        json={
            "source": "B",
            "target": "A",
            "links": [{"source": "A", "target": "B"}],
        },
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "两节点之间不存在有向路径"}


def test_shortest_path_returns_404_for_node_outside_current_view(client):
    response = client.post(
        "/api/shortest-path",
        json={
            "source": "A",
            "target": "C",
            "links": [{"source": "A", "target": "B"}],
        },
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "当前视图中不存在该节点"}


# 边界值测试
def test_shortest_path_returns_single_node_when_source_equals_target(client):
    response = client.post(
        "/api/shortest-path",
        json={
            "source": "A",
            "target": "A",
            "links": [{"source": "A", "target": "B"}],
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"path": ["A"]}


def test_shortest_path_returns_path_for_minimum_nonempty_graph(client):
    response = client.post(
        "/api/shortest-path",
        json={
            "source": "A",
            "target": "B",
            "links": [{"source": "A", "target": "B"}],
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"path": ["A", "B"]}


def test_shortest_path_returns_404_for_empty_links_boundary(client):
    response = client.post(
        "/api/shortest-path",
        json={"source": "A", "target": "B", "links": []},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "当前视图中不存在该节点"}
