import pytest
from app import app


@pytest.fixture
# 创建 Flask 测试客户端
def client():
    app.config.update(TESTING=True)

    with app.test_client() as client:
        yield client