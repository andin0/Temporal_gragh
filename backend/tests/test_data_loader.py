from data_loader import detect_mode
from data_loader import build_timestamp_graph, graph_to_dict
#测试数据处理函数
def test_detect_timestamp_json():
    data = {
        "mode": "timestamp",
        "edges": [
            {"source": "A", "target": "B", "timestamp": 1}
        ]
    }

    assert detect_mode(data) == "timestamp"

#测试建图与序列化
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