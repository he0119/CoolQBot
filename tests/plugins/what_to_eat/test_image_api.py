import asyncio
import json

import httpx
import pytest
import respx
from nonebug import App
from pytest_mock import MockerFixture

COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
THUMBNAIL_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fb/hot-pot.jpg/640px-hot-pot.jpg"
SOURCE_URL = "https://commons.wikimedia.org/wiki/File:Hot-pot.jpg"
OPENVERSE_ID = "274f3029-f595-40d0-ad68-2edff610f4af"
OPENVERSE_DETAIL_URL = f"https://api.openverse.org/v1/images/{OPENVERSE_ID}/"
OPENVERSE_THUMBNAIL_URL = f"https://api.openverse.org/v1/images/{OPENVERSE_ID}/thumb/"
OPENVERSE_SOURCE_URL = "https://www.flickr.com/photos/33347924@N06/8359654127"


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


def openverse_response(*, license_code: str = "by", image_id: str = OPENVERSE_ID) -> dict:
    return {
        "id": image_id,
        "creator": "测试作者",
        "license": license_code,
        "license_version": "2.0",
        "license_url": f"https://creativecommons.org/licenses/{license_code}/2.0/",
        "foreign_landing_url": OPENVERSE_SOURCE_URL,
    }


@respx.mock
async def test_get_commons_food_image(app: App):
    import nonebot_plugin_localstore as store

    from src.plugins.what_to_eat.data_source import FoodImageRef
    from src.plugins.what_to_eat.image_api import IMAGE_USER_AGENT, _disk_cache_paths, get_food_image

    source = FoodImageRef("commons", "File:Hot pot dinner.jpg")

    search = respx.get(url__startswith=COMMONS_API_URL).mock(return_value=httpx.Response(200, json=commons_response()))
    thumbnail = respx.get(THUMBNAIL_URL).mock(
        return_value=httpx.Response(200, content=b"image", headers={"Content-Type": "image/jpeg"})
    )

    image = await get_food_image(source)

    assert image is not None
    assert image.content == b"image"
    assert image.mimetype == "image/jpeg"
    assert image.creator == "测试作者"
    assert image.license_name == "CC BY-SA 4.0"
    assert image.source_url == SOURCE_URL
    assert image.license_url == "https://creativecommons.org/licenses/by-sa/4.0/"
    assert search.calls[0].request.headers["User-Agent"] == IMAGE_USER_AGENT
    assert search.calls[0].request.url.params["titles"] == "File:Hot pot dinner.jpg"
    assert search.calls[0].request.url.params["redirects"] == "1"
    assert search.calls[0].request.url.params["iiurlwidth"] == "640"

    assert await get_food_image(source) is image
    metadata_file, image_file = _disk_cache_paths(source)
    assert metadata_file.parent == store.BASE_CACHE_DIR / "what_to_eat" / "images"
    assert metadata_file.is_file()
    assert image_file.read_bytes() == b"image"

    from src.plugins.what_to_eat.image_api import _IMAGE_CACHE

    _IMAGE_CACHE.clear()
    assert await get_food_image(source) == image
    assert search.call_count == 1
    assert thumbnail.call_count == 1


@respx.mock
async def test_get_food_image_coalesces_concurrent_requests(app: App):
    from src.plugins.what_to_eat.data_source import FoodImageRef
    from src.plugins.what_to_eat.image_api import get_food_image

    source = FoodImageRef("commons", "File:Hot pot dinner.jpg")

    search = respx.get(url__startswith=COMMONS_API_URL).mock(return_value=httpx.Response(200, json=commons_response()))
    thumbnail = respx.get(THUMBNAIL_URL).mock(
        return_value=httpx.Response(200, content=b"image", headers={"Content-Type": "image/jpeg"})
    )

    images = await asyncio.gather(*(get_food_image(source) for _ in range(5)))

    assert all(image is images[0] for image in images)
    assert search.call_count == 1
    assert thumbnail.call_count == 1


@respx.mock
async def test_get_food_image_replaces_corrupted_disk_cache(app: App):
    from src.plugins.what_to_eat.data_source import FoodImageRef
    from src.plugins.what_to_eat.image_api import _IMAGE_CACHE, _disk_cache_paths, get_food_image

    source = FoodImageRef("commons", "File:Hot pot dinner.jpg")

    search = respx.get(url__startswith=COMMONS_API_URL).mock(return_value=httpx.Response(200, json=commons_response()))
    thumbnail = respx.get(THUMBNAIL_URL).mock(
        return_value=httpx.Response(200, content=b"image", headers={"Content-Type": "image/jpeg"})
    )
    assert await get_food_image(source) is not None

    _IMAGE_CACHE.clear()
    _, image_file = _disk_cache_paths(source)
    image_file.write_bytes(b"corrupted")

    image = await get_food_image(source)

    assert image is not None
    assert image.content == b"image"
    assert search.call_count == 2
    assert thumbnail.call_count == 2


@respx.mock
async def test_get_food_image_rejects_untrusted_thumbnail_host(app: App):
    from src.plugins.what_to_eat.data_source import FoodImageRef
    from src.plugins.what_to_eat.image_api import get_food_image

    source = FoodImageRef("commons", "File:Hot pot dinner.jpg")

    search = respx.get(url__startswith=COMMONS_API_URL).mock(
        return_value=httpx.Response(200, json=commons_response("https://example.com/image.jpg"))
    )

    assert await get_food_image(source) is None
    assert search.called


@respx.mock
async def test_get_food_image_rejects_oversized_image(app: App):
    from src.plugins.what_to_eat.data_source import FoodImageRef
    from src.plugins.what_to_eat.image_api import MAX_IMAGE_BYTES, get_food_image

    source = FoodImageRef("commons", "File:Hot pot dinner.jpg")

    respx.get(url__startswith=COMMONS_API_URL).mock(return_value=httpx.Response(200, json=commons_response()))
    respx.get(THUMBNAIL_URL).mock(
        return_value=httpx.Response(
            200,
            content=b"image",
            headers={"Content-Type": "image/jpeg", "Content-Length": str(MAX_IMAGE_BYTES + 1)},
        )
    )

    assert await get_food_image(source) is None


@respx.mock
async def test_get_food_image_falls_back_when_api_fails(app: App):
    from src.plugins.what_to_eat.data_source import FoodImageRef
    from src.plugins.what_to_eat.image_api import get_food_image

    source = FoodImageRef("commons", "File:Hot pot dinner.jpg")

    respx.get(url__startswith=COMMONS_API_URL).mock(return_value=httpx.Response(503))

    assert await get_food_image(source) is None


@respx.mock
async def test_get_openverse_food_image(app: App):
    import nonebot_plugin_localstore as store

    from src.plugins.what_to_eat.data_source import FoodImageRef
    from src.plugins.what_to_eat.image_api import IMAGE_USER_AGENT, _disk_cache_paths, get_food_image

    source = FoodImageRef("openverse", OPENVERSE_ID)
    detail = respx.get(OPENVERSE_DETAIL_URL).mock(return_value=httpx.Response(200, json=openverse_response()))
    thumbnail = respx.get(OPENVERSE_THUMBNAIL_URL).mock(
        return_value=httpx.Response(200, content=b"openverse-image", headers={"Content-Type": "image/jpeg"})
    )

    image = await get_food_image(source)

    assert image is not None
    assert image.content == b"openverse-image"
    assert image.mimetype == "image/jpeg"
    assert image.creator == "测试作者"
    assert image.license_name == "CC BY 2.0"
    assert image.source_url == OPENVERSE_SOURCE_URL
    assert image.license_url == "https://creativecommons.org/licenses/by/2.0/"
    assert detail.calls[0].request.headers["User-Agent"] == IMAGE_USER_AGENT
    assert thumbnail.call_count == 1

    metadata_file, image_file = _disk_cache_paths(source)
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    assert metadata_file.parent == store.BASE_CACHE_DIR / "what_to_eat" / "images"
    assert metadata["provider"] == "openverse"
    assert metadata["id"] == OPENVERSE_ID
    assert image_file.read_bytes() == b"openverse-image"


@respx.mock
async def test_get_openverse_food_image_rejects_unsupported_license(app: App):
    from src.plugins.what_to_eat.data_source import FoodImageRef
    from src.plugins.what_to_eat.image_api import get_food_image

    source = FoodImageRef("openverse", OPENVERSE_ID)
    respx.get(OPENVERSE_DETAIL_URL).mock(
        return_value=httpx.Response(200, json=openverse_response(license_code="by-nc"))
    )
    thumbnail = respx.get(OPENVERSE_THUMBNAIL_URL)

    assert await get_food_image(source) is None
    assert not thumbnail.called


@respx.mock
async def test_get_openverse_food_image_rejects_mismatched_id(app: App):
    from src.plugins.what_to_eat.data_source import FoodImageRef
    from src.plugins.what_to_eat.image_api import get_food_image

    source = FoodImageRef("openverse", OPENVERSE_ID)
    respx.get(OPENVERSE_DETAIL_URL).mock(
        return_value=httpx.Response(
            200,
            json=openverse_response(image_id="5425e12c-0658-44e0-9cb3-512587c9c8cb"),
        )
    )

    assert await get_food_image(source) is None
