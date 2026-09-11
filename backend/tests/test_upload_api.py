TS_CSV = "source,target,timestamp\nA,B,1\nB,C,2\n"
TS_JSON = '{"mode":"timestamp","edges":[{"source":"A","target":"B","timestamp":1}]}'
SNAP_JSON = """
{"mode":"snapshot","snapshots":[
  {"timestamp":1,"nodes":["P","Q"],"edges":[{"source":"P","target":"Q"}]},
  {"timestamp":2,"nodes":["P","Q","R"],"edges":[{"source":"P","target":"Q"},{"source":"Q","target":"R"}]}
]}
"""

# 请求里没有file（等价类）
def test_upload_missing_file(client):
    resp = client.post("/api/upload")
    assert resp.status_code == 400
    assert "error" in resp.get_json()

# 上传txt应拒绝（等价类）
def test_upload_reject_txt(post_upload):
    resp = post_upload("a.txt", "source,target,timestamp\nA,B,1\n")
    assert resp.status_code == 400

# 合法时间戳CSV（等价类）
def test_upload_timestamp_csv(post_upload):
    resp = post_upload("t.csv", TS_CSV)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["detected_mode"] == "timestamp"
    assert "nodes" in body["data"] and "links" in body["data"]

# 合法时间戳JSON（等价类）
def test_upload_timestamp_json(post_upload):
    resp = post_upload("t.json", TS_JSON)
    assert resp.status_code == 200
    assert resp.get_json()["detected_mode"] == "timestamp"

# 合法快照JSON（等价类）
def test_upload_snapshot_json(post_upload):
    resp = post_upload("s.json", SNAP_JSON)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["detected_mode"] == "snapshot"
    assert len(body["data"]) == 2

# 只有表头没有数据行（边界值）
def test_header_only_csv_should_not_be_server_error(post_upload):
    resp = post_upload("empty.csv", "source,target,timestamp\n")
    assert resp.status_code != 500
    assert resp.status_code in (200, 400)

# 缺source列应返回400（等价类）
def test_csv_missing_source_column_should_be_client_error(post_upload):
    resp = post_upload("nosource.csv", "target,timestamp\nB,1\n")
    assert resp.status_code == 400
    assert "error" in resp.get_json()

# 内容不是JSON应返回400（等价类）
def test_invalid_json_should_be_client_error(post_upload):
    resp = post_upload("bad.json", "this is not json")
    assert resp.status_code == 400
    assert "error" in resp.get_json()

# 大写CSV扩展名应能上传（边界值）
def test_uppercase_csv_extension_should_be_accepted(post_upload):
    resp = post_upload("tiny.CSV", TS_CSV)
    assert resp.status_code == 200
    assert resp.get_json()["detected_mode"] == "timestamp"
