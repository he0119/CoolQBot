import pytest
from nonebug import App


@pytest.fixture
async def app(app: App, default_user):
    yield app
