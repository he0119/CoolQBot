import asyncio

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
    from src.plugins.what_to_eat.image_api import _IMAGE_CACHE, _IMAGE_LOCKS

    mocker.patch.dict(_IMAGE_CACHE, clear=True)
    mocker.patch.dict(_IMAGE_LOCKS, clear=True)


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
async def test_get_food_image(app: App):
    import nonebot_plugin_localstore as store

    from src.plugins.what_to_eat.image_api import COMMONS_USER_AGENT, _disk_cache_paths, get_food_image

    search = respx.get(url__startswith=COMMONS_API_URL).mock(return_value=httpx.Response(200, json=commons_response()))
    thumbnail = respx.get(THUMBNAIL_URL).mock(
        return_value=httpx.Response(200, content=b"image", headers={"Content-Type": "image/jpeg"})
    )

    image = await get_food_image("File:Hot pot dinner.jpg")

    assert image is not None
    assert image.content == b"image"
    assert image.mimetype == "image/jpeg"
    assert image.creator == "测试作者"
    assert image.license_name == "CC BY-SA 4.0"
    assert image.source_url == SOURCE_URL
    assert image.license_url == "https://creativecommons.org/licenses/by-sa/4.0/"
    assert search.calls[0].request.headers["User-Agent"] == COMMONS_USER_AGENT
    assert search.calls[0].request.url.params["titles"] == "File:Hot pot dinner.jpg"
    assert search.calls[0].request.url.params["redirects"] == "1"
    assert search.calls[0].request.url.params["iiurlwidth"] == "640"

    assert await get_food_image("File:Hot pot dinner.jpg") is image
    metadata_file, image_file = _disk_cache_paths("File:Hot pot dinner.jpg")
    assert metadata_file.parent == store.BASE_CACHE_DIR / "what_to_eat" / "images"
    assert metadata_file.is_file()
    assert image_file.read_bytes() == b"image"

    from src.plugins.what_to_eat.image_api import _IMAGE_CACHE

    _IMAGE_CACHE.clear()
    assert await get_food_image("File:Hot pot dinner.jpg") == image
    assert search.call_count == 1
    assert thumbnail.call_count == 1


@respx.mock
async def test_get_food_image_coalesces_concurrent_requests(app: App):
    from src.plugins.what_to_eat.image_api import get_food_image

    search = respx.get(url__startswith=COMMONS_API_URL).mock(return_value=httpx.Response(200, json=commons_response()))
    thumbnail = respx.get(THUMBNAIL_URL).mock(
        return_value=httpx.Response(200, content=b"image", headers={"Content-Type": "image/jpeg"})
    )

    images = await asyncio.gather(*(get_food_image("File:Hot pot dinner.jpg") for _ in range(5)))

    assert all(image is images[0] for image in images)
    assert search.call_count == 1
    assert thumbnail.call_count == 1


@respx.mock
async def test_get_food_image_replaces_corrupted_disk_cache(app: App):
    from src.plugins.what_to_eat.image_api import _IMAGE_CACHE, _disk_cache_paths, get_food_image

    search = respx.get(url__startswith=COMMONS_API_URL).mock(return_value=httpx.Response(200, json=commons_response()))
    thumbnail = respx.get(THUMBNAIL_URL).mock(
        return_value=httpx.Response(200, content=b"image", headers={"Content-Type": "image/jpeg"})
    )
    assert await get_food_image("File:Hot pot dinner.jpg") is not None

    _IMAGE_CACHE.clear()
    _, image_file = _disk_cache_paths("File:Hot pot dinner.jpg")
    image_file.write_bytes(b"corrupted")

    image = await get_food_image("File:Hot pot dinner.jpg")

    assert image is not None
    assert image.content == b"image"
    assert search.call_count == 2
    assert thumbnail.call_count == 2


@respx.mock
async def test_get_food_image_rejects_untrusted_thumbnail_host(app: App):
    from src.plugins.what_to_eat.image_api import get_food_image

    search = respx.get(url__startswith=COMMONS_API_URL).mock(
        return_value=httpx.Response(200, json=commons_response("https://example.com/image.jpg"))
    )

    assert await get_food_image("File:Hot pot dinner.jpg") is None
    assert search.called


@respx.mock
async def test_get_food_image_rejects_oversized_image(app: App):
    from src.plugins.what_to_eat.image_api import MAX_IMAGE_BYTES, get_food_image

    respx.get(url__startswith=COMMONS_API_URL).mock(return_value=httpx.Response(200, json=commons_response()))
    respx.get(THUMBNAIL_URL).mock(
        return_value=httpx.Response(
            200,
            content=b"image",
            headers={"Content-Type": "image/jpeg", "Content-Length": str(MAX_IMAGE_BYTES + 1)},
        )
    )

    assert await get_food_image("File:Hot pot dinner.jpg") is None


@respx.mock
async def test_get_food_image_falls_back_when_api_fails(app: App):
    from src.plugins.what_to_eat.image_api import get_food_image

    respx.get(url__startswith=COMMONS_API_URL).mock(return_value=httpx.Response(503))

    assert await get_food_image("File:Hot pot dinner.jpg") is None
