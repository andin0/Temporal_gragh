import json

import pandas as pd

from data_loader import (
    build_snapshot_graphs,
    build_timestamp_graph,
    detect_mode,
    graph_to_dict,
    load_from_json,
)


# 测试数据处理函数
def test_detect_timestamp_json():
    data = {
        "mode": "timestamp",
        "edges": [
            {"source": "A", "target": "B", "timestamp": 1}
        ]
    }

    assert detect_mode(data) == "timestamp"

# 测试建图与序列化
def test_build_timestamp_graph():
    data = {
        "edges": [
            {"source": "A", "target": "B", "timestamp": 1},
            {"source": "B", "target": "C", "timestamp": 2}
        ]
    }

    graph = build_timestamp_graph(data)
    result = graph_to_dict(graph)

    assert graph.number_of_nodes() == 3
    assert graph.number_of_edges() == 2
    assert len(result["nodes"]) == 3
    assert len(result["links"]) == 2


# 等价类测试
#合法快照
def test_detect_snapshot_json():
    data = {
        "mode": "snapshot",
        "snapshots": [{"timestamp": 1, "nodes": ["A"], "edges": []}],
    }

    assert detect_mode(data) == "snapshot"
#带有timestamp
def test_detect_timestamp_dataframe():
    data = pd.DataFrame(
        [{"source": "A", "target": "B", "timestamp": 1}]
    )

    assert detect_mode(data) == "timestamp"
#不带有timestamp
def test_detect_snapshot_dataframe():
    data = pd.DataFrame([{"source": "A", "target": "B"}])

    assert detect_mode(data) == "snapshot"
#通过 `tmp_path` 创建并读取一份含 10 个节点的合法时间戳 JSON 文件
def test_load_ten_node_timestamp_json(tmp_path):
    edges = [
        {"source": f"N{i}", "target": f"N{i + 1}", "timestamp": i + 1}
        for i in range(9)
    ]
    expected = {"mode": "timestamp", "edges": edges}
    json_file = tmp_path / "ten_nodes_timestamp.json"
    json_file.write_text(json.dumps(expected), encoding="utf-8")

    loaded = load_from_json(json_file)
    graph = build_timestamp_graph(loaded)

    assert loaded == expected
    assert graph.number_of_nodes() == 10
    assert graph.number_of_edges() == 9
#构建并序列化一份含 20 个节点、20 条边的时间戳图
def test_twenty_node_timestamp_graph():
    data = {
        "edges": [
            {
                "source": f"N{i}",
                "target": f"N{(i + 1) % 20}",
                "timestamp": i + 1,
            }
            for i in range(20)
        ]
    }

    graph = build_timestamp_graph(data)
    result = graph_to_dict(graph)

    assert graph.number_of_nodes() == 20
    assert graph.number_of_edges() == 20
    assert {node["id"] for node in result["nodes"]} == {f"N{i}" for i in range(20)}
    assert len(result["links"]) == 20

# 边界值测试
#没有边的时间戳图
def test_timestamp_zero_edges():
    graph = build_timestamp_graph({"edges": []})

    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0
#一条边的时间戳图
def test_timestamp_one_edge():
    graph = build_timestamp_graph(
        {"edges": [{"source": "A", "target": "B", "timestamp": 1}]}
    )

    assert graph.number_of_nodes() == 2
    assert graph.number_of_edges() == 1
    assert graph["A"]["B"][0]["timestamp"] == 1
#时间戳为0
def test_zero_timestamp():
    graph = build_timestamp_graph(
        {"edges": [{"source": "A", "target": "B", "timestamp": 0}]}
    )
    result = graph_to_dict(graph)

    assert len(result["links"]) == 1
    assert result["links"][0]["timestamp"] == 0
#没有快照
def test_zero_snapshots():
    graphs = build_snapshot_graphs({"snapshots": []})

    assert graphs == []
#仅有一个孤立节点且边数为0
def test_one_isolated_node():
    graphs = build_snapshot_graphs(
        {
            "snapshots": [
                {"timestamp": 1, "nodes": ["Solo"], "edges": []}
            ]
        }
    )
    result = graph_to_dict(graphs[0])

    assert len(graphs) == 1
    assert graphs[0].number_of_nodes() == 1
    assert graphs[0].number_of_edges() == 0
    assert result["nodes"][0]["id"] == "Solo"
    assert result["links"] == []
