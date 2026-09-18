"""模块二 sakiko2 独立一轮：AI 生成后经人工核对的 pytest。

编号对应 讨论/模块二-sakiko2/用例草稿.md 中的 TG-M2-PJJ-xxx。
不替代模块一已有测试文件。
"""

from types import SimpleNamespace
from unittest.mock import patch
import subprocess

from data_loader import (
    build_timestamp_graph,
    detect_mode,
    graph_to_dict,
)
import pandas as pd
import pytest


# TG-M2-PJJ-001 CSV 使用 time 列时应被识别为时间戳模式
def test_detect_mode_accepts_time_column():
    df = pd.DataFrame([{"source": "A", "target": "B", "time": 1}])
    assert detect_mode(df) == "timestamp"


# TG-M2-PJJ-002 仅有 time 列的 CSV 上传后应能构图，不应 500
def test_upload_csv_time_column_should_build_graph(post_upload):
    resp = post_upload("t.csv", "source,target,time\nA,B,1\n")
    body = resp.get_json()
    assert resp.status_code == 200
    assert body["detected_mode"] == "timestamp"
    ids = {n["id"] for n in body["data"]["nodes"]}
    assert ids == {"A", "B"}


# TG-M2-PJJ-003 快照模式 CSV 上传
def test_upload_snapshot_csv(post_upload):
    content = (
        "timestamp,nodes,edges\n"
        '1,"[""A"",""B""]","[{""source"":""A"",""target"":""B""}]"\n'
    )
    resp = post_upload("snap.csv", content)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["detected_mode"] == "snapshot"
    assert len(body["data"]) == 1
    assert {n["id"] for n in body["data"][0]["nodes"]} == {"A", "B"}


# TG-M2-PJJ-004 自环边应保留
def test_timestamp_self_loop_kept():
    graph = build_timestamp_graph(
        {"edges": [{"source": "A", "target": "A", "timestamp": 1}]}
    )
    assert graph.number_of_nodes() == 1
    assert graph.number_of_edges() == 1


# TG-M2-PJJ-005 同一对节点两条边应建成多重图
def test_parallel_edges_kept_as_multigraph():
    graph = build_timestamp_graph(
        {
            "edges": [
                {"source": "A", "target": "B", "timestamp": 1},
                {"source": "A", "target": "B", "timestamp": 2},
            ]
        }
    )
    assert graph.number_of_edges() == 2
    result = graph_to_dict(graph)
    assert len(result["links"]) == 2


# TG-M2-PJJ-006 中文节点 id 上传 JSON 应成功
def test_upload_json_chinese_node_ids(post_upload):
    content = (
        '{"mode":"timestamp","edges":'
        '[{"source":"甲","target":"乙","timestamp":1}]}'
    )
    resp = post_upload("cn.json", content)
    assert resp.status_code == 200
    ids = {n["id"] for n in resp.get_json()["data"]["nodes"]}
    assert ids == {"甲", "乙"}


# TG-M2-PJJ-007 数字节点在 CSV 里应保持可查询
def test_upload_csv_numeric_node_ids(post_upload):
    resp = post_upload("num.csv", "source,target,timestamp\n1,2,1\n")
    assert resp.status_code == 200
    ids = {n["id"] for n in resp.get_json()["data"]["nodes"]}
    assert ids == {1, 2}


# TG-M2-PJJ-008 最短路径 links 为前端 D3 对象格式
def test_shortest_path_accepts_d3_link_objects(client):
    resp = client.post(
        "/api/shortest-path",
        json={
            "source": "A",
            "target": "C",
            "links": [
                {"source": {"id": "A"}, "target": {"id": "B"}},
                {"source": {"id": "B"}, "target": {"id": "C"}},
            ],
        },
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"path": ["A", "B", "C"]}


# TG-M2-PJJ-009 缺 target 列应返回 400
def test_csv_missing_target_column_should_be_client_error(post_upload):
    resp = post_upload("notarget.csv", "source,timestamp\nA,1\n")
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "'target'"}


# TG-M2-PJJ-010 大写 JSON 扩展名应能上传
def test_uppercase_json_extension_should_be_accepted(post_upload):
    content = '{"mode":"timestamp","edges":[{"source":"A","target":"B","timestamp":1}]}'
    resp = post_upload("tiny.JSON", content)
    assert resp.status_code == 200
    assert resp.get_json()["detected_mode"] == "timestamp"


# TG-M2-PJJ-011 上传快照后 GET 时间戳图不应被快照覆盖成非法结构
def test_upload_snapshot_should_not_break_timestamp_get(client, post_upload):
    before = client.get("/api/graph/timestamp")
    assert before.status_code == 200
    snap = """
    {"mode":"snapshot","snapshots":[
      {"timestamp":1,"nodes":["P","Q"],"edges":[{"source":"P","target":"Q"}]}
    ]}
    """
    up = post_upload("s.json", snap)
    assert up.status_code == 200
    after = client.get("/api/graph/timestamp")
    assert after.status_code == 200
    body = after.get_json()
    assert "nodes" in body and "links" in body


# TG-M2-PJJ-012 上传时间戳后 GET 快照不应变成时间戳结构
def test_upload_timestamp_should_not_break_snapshot_get(client, post_upload):
    up = post_upload("t.csv", "source,target,timestamp\nA,B,1\n")
    assert up.status_code == 200
    resp = client.get("/api/graph/snapshot")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert data, "快照接口不应返回空列表"
    assert "snapshot_id" in data[0]


# TG-M2-PJJ-013 空边集合走 graph_to_dict 不应抛异常
def test_graph_to_dict_on_empty_timestamp_graph():
    result = graph_to_dict(build_timestamp_graph({"edges": []}))
    assert result["nodes"] == []
    assert result["links"] == []


# TG-M2-PJJ-014 JSON 有 edges 但第一条没有 timestamp，detect_mode 行为应可预期
def test_detect_mode_edges_without_timestamp_field():
    data = {"edges": [{"source": "A", "target": "B"}]}
    assert detect_mode(data) == "snapshot"


# TG-M2-PJJ-015 一键测试接口应返回摘要字段（打桩，避免套娃跑整套 pytest）
def test_run_tests_endpoint_returns_summary(client):
    fake = SimpleNamespace(
        returncode=0,
        stdout="2 passed in 0.10s",
        stderr="",
    )
    with patch("app.subprocess.run", return_value=fake):
        resp = client.post("/api/run-tests")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["passed"] == 2
    assert body["failed"] == 0
    assert body["errors"] == 0
    assert body["output"] == "2 passed in 0.10s"


# TG-M2-PJJ-016 缺 links 参数应 400
def test_shortest_path_missing_links_is_client_error(client):
    resp = client.post(
        "/api/shortest-path",
        json={"source": "A", "target": "B"},
    )
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "缺少必要参数"}


# TG-M2-PJJ-017 负时间戳应能建边
def test_negative_timestamp_kept():
    graph = build_timestamp_graph(
        {"edges": [{"source": "A", "target": "B", "timestamp": -1}]}
    )
    result = graph_to_dict(graph)
    assert result["links"][0]["timestamp"] == -1


# TG-M2-PJJ-018 损坏的 JSON 上传应是客户端错误，而非服务器错误
def test_upload_invalid_json_is_client_error(post_upload):
    resp = post_upload("broken.json", '{"mode":')

    assert resp.status_code == 400
    assert "error" in resp.get_json()


# TG-M2-PJJ-019 快照 CSV 中的 edges 字段不是 JSON 时应返回 400
def test_upload_snapshot_csv_with_invalid_edges_json_is_client_error(post_upload):
    content = 'timestamp,nodes,edges\n1,"[""A""]","not-json"\n'
    resp = post_upload("broken-snapshot.csv", content)

    assert resp.status_code == 400
    assert "error" in resp.get_json()


# TG-M2-PJJ-020 一键测试接口应能解析 Pytest 失败摘要（打桩，不启动子进程）
def test_run_tests_endpoint_reports_failed_pytest_summary(client):
    fake = SimpleNamespace(
        returncode=1,
        stdout="16 passed, 1 failed in 0.20s",
        stderr="",
    )
    with patch("app.subprocess.run", return_value=fake):
        resp = client.post("/api/run-tests")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is False
    assert body["passed"] == 16
    assert body["failed"] == 1
    assert body["errors"] == 0


# TG-M2-PJJ-021 一键测试超时时应返回可展示的失败摘要
def test_run_tests_endpoint_reports_timeout(client):
    with patch(
        "app.subprocess.run",
        side_effect=subprocess.TimeoutExpired("pytest", 60),
    ):
        resp = client.post("/api/run-tests")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is False
    assert body["errors"] == 1
    assert "超时" in body["output"]


# TG-M2-PJJ-022 一键测试进程无法启动时应返回可展示的失败摘要
def test_run_tests_endpoint_reports_process_start_failure(client):
    with patch("app.subprocess.run", side_effect=OSError("missing executable")):
        resp = client.post("/api/run-tests")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is False
    assert body["errors"] == 1
    assert "无法启动" in body["output"]
