import io
from urllib.parse import parse_qs, urlparse

import httpx
from PIL import Image
import pytest


def test_wms_proxy_validation(client):
    res_no_url = client.get("/api/wms/proxy?LAYERS=test:layer")
    assert res_no_url.status_code == 400

    res_no_layer = client.get("/api/wms/proxy?TARGET_URL=https://example.com/wms")
    assert res_no_layer.status_code == 400


def test_wms_proxy_forwards_upstream_image_and_vendor_params(client, monkeypatch):
    captured_urls = []
    # Minimal 2x2 valid PNG
    buf = io.BytesIO()
    Image.new("RGBA", (2, 2), (20, 140, 120, 255)).save(buf, format="PNG")
    expected_png = buf.getvalue()

    class _FakeResp:
        status_code = 200
        content = expected_png
        headers = {"content-type": "image/png"}

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url: str, **kwargs):
            captured_urls.append(url)
            return _FakeResp()

    monkeypatch.setattr("backend.app.api.wms.httpx.AsyncClient", _FakeClient)

    resp = client.get(
        "/api/wms/proxy",
        params={
            "TARGET_URL": "https://example.com/mapserv?map=/srv/india.map",
            "LAYERS": "dsm_layer",
            "STYLES": "default",
            "FORMAT": "image/png",
            "SRS": "EPSG:4326",
            "BBOX": "74.0,34.0,76.0,36.0",
            "WIDTH": "256",
            "HEIGHT": "256",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/png")
    assert resp.headers["x-geoharvest-wms-source"] == "upstream"
    assert resp.content == expected_png
    assert len(captured_urls) == 1
    assert "map=%2Fsrv%2Findia.map" in captured_urls[0]
    assert "VERSION=1.1.1" in captured_urls[0]
    assert "SRS=EPSG%3A4326" in captured_urls[0]
    assert "LAYERS=dsm_layer" in captured_urls[0]


def test_wms_proxy_synthesizes_georeferenced_png_on_xml_exception_or_offline(client, monkeypatch):
    class _XmlExceptionResp:
        status_code = 200
        content = b'<?xml version="1.0"?><ServiceExceptionReport><ServiceException>InvalidSRS</ServiceException></ServiceExceptionReport>'
        headers = {"content-type": "application/vnd.ogc.se_xml"}

    class _FakeExceptionClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url: str, **kwargs):
            return _XmlExceptionResp()

    monkeypatch.setattr("backend.app.api.wms.httpx.AsyncClient", _FakeExceptionClient)

    # Tile inside EXTENT_BBOX should have non-zero alpha pixels
    inside_resp = client.get(
        "/api/wms/proxy",
        params={
            "TARGET_URL": "https://vedas.sac.gov.in/geoserver/vedas/wms",
            "LAYERS": "vedas:INDIA_500KDSM2018_19",
            "BBOX": "74.5,34.7,76.4,36.0",
            "EXTENT_BBOX": "74.430135,34.651623,76.537046,36.162063",
            "WIDTH": "128",
            "HEIGHT": "128",
        },
    )
    assert inside_resp.status_code == 200
    assert inside_resp.headers["x-geoharvest-wms-source"] == "fallback"
    assert inside_resp.content.startswith(b"\x89PNG\r\n\x1a\n")
    img_in = Image.open(io.BytesIO(inside_resp.content))
    assert img_in.size == (128, 128)
    assert img_in.mode == "RGBA"
    # Center pixel is inside EXTENT_BBOX -> alpha > 0
    assert img_in.getpixel((64, 64))[3] > 0

    # Tile completely outside EXTENT_BBOX should be transparent
    outside_resp = client.get(
        "/api/wms/proxy",
        params={
            "TARGET_URL": "https://vedas.sac.gov.in/geoserver/vedas/wms",
            "LAYERS": "vedas:INDIA_500KDSM2018_19",
            "BBOX": "10.0,10.0,12.0,12.0",
            "EXTENT_BBOX": "74.430135,34.651623,76.537046,36.162063",
            "WIDTH": "128",
            "HEIGHT": "128",
        },
    )
    assert outside_resp.status_code == 200
    img_out = Image.open(io.BytesIO(outside_resp.content))
    assert img_out.getpixel((64, 64))[3] == 0


def _mock_strict_upstream(monkeypatch, response, captured=None):
    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def get(self, url):
            if captured is not None:
                captured.append(parse_qs(urlparse(url).query))
            return response

    monkeypatch.setattr("backend.app.api.wms.httpx.AsyncClient", Client)


def _png(width, height):
    data = io.BytesIO()
    Image.new("RGB", (width, height), (23, 54, 72)).save(data, format="PNG")
    return data.getvalue()


def test_wms_strict_forwards_13_axis_order_and_validates_tile(client, monkeypatch):
    captured = []
    png = _png(256, 256)
    _mock_strict_upstream(monkeypatch, httpx.Response(200, content=png), captured)
    response = client.get("/api/wms/proxy", params={
        "TARGET_URL": "https://example.com/wms?TIME=2020-01-01",
        "LAYERS": "test:layer", "CRS": "EPSG:4326", "VERSION": "1.3.0",
        "BBOX": "32,74,36,82", "WIDTH": 256, "HEIGHT": 256, "STRICT": True,
    })

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-geoharvest-wms-source"] == "upstream"
    assert response.content == png
    assert captured[0]["VERSION"] == ["1.3.0"]
    assert captured[0]["CRS"] == ["EPSG:4326"]
    assert captured[0]["BBOX"] == ["32,74,36,82"]
    assert captured[0]["TIME"] == ["2020-01-01"]
    assert "SRS" not in captured[0] and "STRICT" not in captured[0]


@pytest.mark.parametrize(("content", "media_type", "expected"), [
    (b"<ServiceExceptionReport/>", "application/vnd.ogc.se_xml", "XML or HTML"),
    (b"not a png", "image/png", "unreadable"),
    (_png(64, 64), "image/png", "64×64 image"),
])
def test_wms_strict_surfaces_failed_map_instead_of_fallback(client, monkeypatch, content, media_type, expected):
    _mock_strict_upstream(monkeypatch, httpx.Response(200, content=content, headers={"Content-Type": media_type}))
    response = client.get("/api/wms/proxy", params={
        "TARGET_URL": "https://example.com/wms", "LAYERS": "test:layer", "STRICT": True,
    })
    assert response.status_code == 502
    assert expected in response.json()["detail"]
