import httpx
import pytest
import respx
from nonebug import App
from pytest_mock import MockerFixture

COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
THUMBNAIL_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fb/hot-pot.jpg/640px-hot-pot.jpg"
SOURCE_URL = "https://commons.wikimedia.org/wiki/File:Hot-pot.jpg"


@pytest.fixture(autouse=True)
async def clear_image_cache(app: App, mocker: MockerFixture):
    from src.plugins.what_to_eat.image_api import _IMAGE_CACHE

    mocker.patch.dict(_IMAGE_CACHE, clear=True)


def commons_response(thumbnail_url: str = THUMBNAIL_URL, mimetype: str = "image/jpeg") -> dict:
    return {
        "query": {
            "pages": [
                {
                    "index": 1,
                    "imageinfo": [
                        {
                            "thumburl": thumbnail_url,
                            "descriptionurl": SOURCE_URL,
                            "mime": mimetype,
                            "extmetadata": {
                                "Artist": {"value": '<a href="/wiki/User:Tester">测试作者</a>'},
                                "LicenseShortName": {"value": "CC BY-SA 4.0"},
                                "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0/"},
                            },
                        }
                    ],
                }
            ]
        }
    }


@respx.mock
async def test_search_food_image(app: App):
    from src.plugins.what_to_eat.image_api import COMMONS_USER_AGENT, search_food_image

    search = respx.get(url__startswith=COMMONS_API_URL).mock(return_value=httpx.Response(200, json=commons_response()))
    thumbnail = respx.get(THUMBNAIL_URL).mock(
        return_value=httpx.Response(200, content=b"image", headers={"Content-Type": "image/jpeg"})
    )

    image = await search_food_image("火锅")

    assert image is not None
    assert image.content == b"image"
    assert image.mimetype == "image/jpeg"
    assert image.creator == "测试作者"
    assert image.license_name == "CC BY-SA 4.0"
    assert image.source_url == SOURCE_URL
    assert image.license_url == "https://creativecommons.org/licenses/by-sa/4.0/"
    assert search.calls[0].request.headers["User-Agent"] == COMMONS_USER_AGENT
    assert search.calls[0].request.url.params["gsrsearch"] == "火锅"
    assert search.calls[0].request.url.params["gsrnamespace"] == "6"
    assert search.calls[0].request.url.params["iiurlwidth"] == "640"

    assert await search_food_image("火锅") is image
    assert search.call_count == 1
    assert thumbnail.call_count == 1


@respx.mock
async def test_search_food_image_rejects_untrusted_thumbnail_host(app: App):
    from src.plugins.what_to_eat.image_api import search_food_image

    search = respx.get(url__startswith=COMMONS_API_URL).mock(
        return_value=httpx.Response(200, json=commons_response("https://example.com/image.jpg"))
    )

    assert await search_food_image("火锅") is None
    assert search.called


@respx.mock
async def test_search_food_image_rejects_oversized_image(app: App):
    from src.plugins.what_to_eat.image_api import MAX_IMAGE_BYTES, search_food_image

    respx.get(url__startswith=COMMONS_API_URL).mock(return_value=httpx.Response(200, json=commons_response()))
    respx.get(THUMBNAIL_URL).mock(
        return_value=httpx.Response(
            200,
            content=b"image",
            headers={"Content-Type": "image/jpeg", "Content-Length": str(MAX_IMAGE_BYTES + 1)},
        )
    )

    assert await search_food_image("火锅") is None


@respx.mock
async def test_search_food_image_falls_back_when_api_fails(app: App):
    from src.plugins.what_to_eat.image_api import search_food_image

    respx.get(url__startswith=COMMONS_API_URL).mock(return_value=httpx.Response(503))

    assert await search_food_image("火锅") is None
