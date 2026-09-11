# 取默认图。后面带 should 的是缺陷候选，失败正常。


def test_get_timestamp_ok(client):
    resp = client.get("/api/graph/timestamp")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "nodes" in body and "links" in body


def test_get_timestamp_size(client):
    body = client.get("/api/graph/timestamp").get_json()
    assert len(body["nodes"]) == 3
    assert len(body["links"]) == 5


def test_get_timestamp_node_fields(client):
    node = client.get("/api/graph/timestamp").get_json()["nodes"][0]
    assert "id" in node and "degree" in node
    assert "pagerank" in node and "group" in node


def test_get_snapshot_ok(client):
    resp = client.get("/api/graph/snapshot")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)
    assert len(resp.get_json()) == 2


def test_get_snapshot_item_fields(client):
    item = client.get("/api/graph/snapshot").get_json()[0]
    assert "snapshot_id" in item and "timestamp" in item
    assert "nodes" in item and "links" in item


def test_get_snapshot_grows(client):
    data = client.get("/api/graph/snapshot").get_json()
    assert len(data[0]["nodes"]) == 3
    assert len(data[1]["nodes"]) == 4


def test_post_timestamp_not_allowed(client):
    resp = client.post("/api/graph/timestamp")
    assert resp.status_code == 405


def test_get_timestamp_after_upload_should_show_new_graph(client, post_upload):
    # 上传后 GET 仍应是新图；失败则默认取图没用上上传结果
    resp_up = post_upload("tiny.csv", "source,target,timestamp\nA,B,1\n")
    assert resp_up.status_code == 200
    ids = {n["id"] for n in client.get("/api/graph/timestamp").get_json()["nodes"]}
    assert ids == {"A", "B"}
