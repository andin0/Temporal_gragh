from io import BytesIO

import pytest
from app import app


@pytest.fixture
# 创建 Flask 测试客户端
def client():
    app.config.update(TESTING=True)

    with app.test_client() as client:
        yield client


@pytest.fixture
def post_upload(client):
    """模拟网页上传：把内存里的文件 POST 到 /api/upload。"""

    def _post(filename, content):
        if isinstance(content, str):
            content = content.encode("utf-8")
        return client.post(
            "/api/upload",
            data={"file": (BytesIO(content), filename)},
            content_type="multipart/form-data",
        )

    return _post