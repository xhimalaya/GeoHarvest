import json
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api import toposheets

client = TestClient(app)


def test_toposheet_status_has_official_sources():
    response = client.get('/api/toposheets/status')
    assert response.status_code == 200
    body = response.json()
    assert body['provider_id'] == 'survey-of-india-toposheets'
    assert body['official_urls']['free_osm_pdf'].startswith('https://onlinemaps.surveyofindia.gov.in/')
    assert body['download_mode'] == 'assisted'
    assert body['supports_grid_generation'] is True


def test_index_upload_and_aoi_search(tmp_path, monkeypatch):
    index_dir = tmp_path / 'toposheets'
    index_path = index_dir / 'sheet_index.geojson'
    monkeypatch.setattr(toposheets, 'INDEX_DIR', index_dir)
    monkeypatch.setattr(toposheets, 'INDEX_PATH', index_path)

    index = {
        'type': 'FeatureCollection',
        'features': [
            {
                'type': 'Feature',
                'properties': {'sheet_no': 'H42W12', 'scale': '1:50,000'},
                'geometry': {'type': 'Polygon', 'coordinates': [[[77.0, 33.0], [78.0, 33.0], [78.0, 34.0], [77.0, 34.0], [77.0, 33.0]]]},
            },
            {
                'type': 'Feature',
                'properties': {'sheet_no': 'OUTSIDE'},
                'geometry': {'type': 'Polygon', 'coordinates': [[[80.0, 33.0], [81.0, 33.0], [81.0, 34.0], [80.0, 34.0], [80.0, 33.0]]]},
            },
        ],
    }
    upload = client.post('/api/toposheets/index/upload', files={'file': ('index.geojson', json.dumps(index), 'application/geo+json')})
    assert upload.status_code == 200, upload.text
    assert upload.json()['feature_count'] == 2

    search = client.post('/api/toposheets/search', json={
        'bbox': [77.2, 33.2, 77.8, 33.8],
    })
    assert search.status_code == 200, search.text
    body = search.json()
    assert body['total_found'] == 1
    assert body['results'][0]['sheet_number'] == 'H42W12'
    assert body['results'][0]['availability'] == 'portal_only'
    assert body['results'][0]['direct_available'] is False


def test_standard_soi_grid_generation_ladakh(tmp_path, monkeypatch):
    index_dir = tmp_path / 'toposheets'
    index_path = index_dir / 'sheet_index.geojson'
    monkeypatch.setattr(toposheets, 'INDEX_DIR', index_dir)
    monkeypatch.setattr(toposheets, 'INDEX_PATH', index_path)

    gen_resp = client.post('/api/toposheets/index/generate-standard', json={
        'bbox': [77.0, 33.5, 78.0, 34.5],
        'include_250k': True,
        'include_50k': True,
    })
    assert gen_resp.status_code == 200
    data = gen_resp.json()
    assert data['generated'] is True
    assert data['feature_count'] > 0

    # Search for Leh coordinates
    search = client.post('/api/toposheets/search', json={
        'bbox': [77.5, 34.1, 77.6, 34.2],
    })
    assert search.status_code == 200
    res = search.json()
    sheet_numbers = [r['sheet_number'] for r in res['results']]
    assert any('52F' in s for s in sheet_numbers)


def test_dynamic_fallback_grid_when_no_index(tmp_path, monkeypatch):
    empty_dir = tmp_path / 'empty'
    monkeypatch.setattr(toposheets, 'INDEX_DIR', empty_dir)
    monkeypatch.setattr(toposheets, 'INDEX_PATH', empty_dir / 'sheet_index.geojson')

    # Search in Ladakh directly with no index uploaded - should compute on the fly
    search = client.post('/api/toposheets/search', json={
        'bbox': [77.5, 34.1, 77.6, 34.2],
    })
    assert search.status_code == 200
    res = search.json()
    assert res['total_found'] > 0
    sheet_numbers = [r['sheet_number'] for r in res['results']]
    assert any('52F' in s for s in sheet_numbers)


def test_toposheet_harvest_endpoint(tmp_path):
    dest = tmp_path / 'downloads'
    dest.mkdir(parents=True, exist_ok=True)
    resp = client.post('/api/toposheets/harvest', json={
        'name': 'Test_Harvest_SOI',
        'sheets': [
            {'sheet_number': '40D/15', 'formats': ['pdf', 'tif']}
        ],
        'destination_dir': str(dest)
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert 'id' in data
    assert data['total_downloads'] == 2


def test_toposheet_harvest_portal_only_fails_gracefully(tmp_path):
    dest = tmp_path / 'downloads'
    dest.mkdir(parents=True, exist_ok=True)
    resp = client.post('/api/toposheets/harvest', json={
        'name': 'Test_Harvest_SOI_Portal_Only',
        'sheets': [
            {'sheet_number': '43A/9', 'formats': ['pdf']}
        ],
        'destination_dir': str(dest)
    })
    assert resp.status_code == 400
    assert 'open-access direct download' in resp.json()['detail']


def test_catalog_lookup_accuracy():
    from backend.core.toposheets.catalog import get_sheet_release_info
    avail = get_sheet_release_info('40F/5')
    assert avail['direct_available'] is True
    assert avail['pdf_url'] is not None and '40F_5.pdf' in avail['pdf_url']
    assert avail['georef_url'] is not None and '40F_5.tif' in avail['georef_url']

    unavail = get_sheet_release_info('43A/9')
    assert unavail['direct_available'] is False
    assert unavail['pdf_url'] is None

