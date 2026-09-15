import subprocess
from types import SimpleNamespace

import app as app_module


# 取默认时间戳图（等价类）
def test_get_timestamp_ok(client):
    resp = client.get("/api/graph/timestamp")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "nodes" in body and "links" in body

# 时间戳图点边数量（等价类）
def test_get_timestamp_size(client):
    body = client.get("/api/graph/timestamp").get_json()
    assert len(body["nodes"]) == 3
    assert len(body["links"]) == 5

# 节点字段是否齐全（等价类）
def test_get_timestamp_node_fields(client):
    node = client.get("/api/graph/timestamp").get_json()["nodes"][0]
    assert "id" in node and "degree" in node
    assert "pagerank" in node and "group" in node

# 取默认快照图（等价类）
def test_get_snapshot_ok(client):
    resp = client.get("/api/graph/snapshot")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)
    assert len(resp.get_json()) == 2

# 快照一条的结构（等价类）
def test_get_snapshot_item_fields(client):
    item = client.get("/api/graph/snapshot").get_json()[0]
    assert "snapshot_id" in item and "timestamp" in item
    assert "nodes" in item and "links" in item

# 第二张快照节点变多（等价类）
def test_get_snapshot_grows(client):
    data = client.get("/api/graph/snapshot").get_json()
    assert len(data[0]["nodes"]) == 3
    assert len(data[1]["nodes"]) == 4

# POST取图应不允许（等价类）
def test_post_timestamp_not_allowed(client):
    resp = client.post("/api/graph/timestamp")
    assert resp.status_code == 405

# 上传后再取默认图应变为新图（场景法）
def test_get_timestamp_after_upload_should_show_new_graph(client, post_upload):
    resp_up = post_upload("tiny.csv", "source,target,timestamp\nA,B,1\n")
    assert resp_up.status_code == 200
    ids = {n["id"] for n in client.get("/api/graph/timestamp").get_json()["nodes"]}
    assert ids == {"A", "B"}


# def test_run_tests_returns_summary_when_pytest_passes(client, monkeypatch):
#     fake_subprocess = SimpleNamespace(
#         TimeoutExpired=subprocess.TimeoutExpired,
#         run=lambda *args, **kwargs: SimpleNamespace(
#             returncode=0,
#             stdout="35 passed in 1.20s",
#             stderr="",
#         ),
#     )
#     monkeypatch.setattr(app_module, "subprocess", fake_subprocess, raising=False)

#     response = client.post("/api/run-tests")
#     body = response.get_json()

#     assert response.status_code == 200
#     assert body["success"] is True
#     assert body["passed"] == 35
#     assert body["failed"] == 0
#     assert body["errors"] == 0


# def test_run_tests_reports_failed_cases(client, monkeypatch):
#     fake_subprocess = SimpleNamespace(
#         TimeoutExpired=subprocess.TimeoutExpired,
#         run=lambda *args, **kwargs: SimpleNamespace(
#             returncode=1,
#             stdout="31 passed, 4 failed in 1.20s",
#             stderr="",
#         ),
#     )
#     monkeypatch.setattr(app_module, "subprocess", fake_subprocess, raising=False)

#     response = client.post("/api/run-tests")
#     body = response.get_json()

#     assert response.status_code == 200
#     assert body["success"] is False
#     assert body["passed"] == 31
#     assert body["failed"] == 4


# def test_run_tests_reports_timeout_without_server_error(client, monkeypatch):
#     def raise_timeout(*args, **kwargs):
#         raise subprocess.TimeoutExpired(cmd="pytest", timeout=60)

#     fake_subprocess = SimpleNamespace(
#         TimeoutExpired=subprocess.TimeoutExpired,
#         run=raise_timeout,
#     )
#     monkeypatch.setattr(app_module, "subprocess", fake_subprocess, raising=False)

#     response = client.post("/api/run-tests")
#     body = response.get_json()

#     assert response.status_code == 200
#     assert body["success"] is False
#     assert body["errors"] == 1
#     assert "超时" in body["output"]
