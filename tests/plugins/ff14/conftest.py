import pytest
from nonebug import App


@pytest.fixture()
async def app(app: App, _default_user):
    return app
