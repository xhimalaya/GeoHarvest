def test_api_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_api_ladakh_sample(client):
    response = client.get("/api/aoi/samples/ladakh")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Ladakh Region"
    assert data["analysis"]["valid"] is True
    assert data["analysis"]["area_km2"] > 0


def test_api_providers_list(client):
    response = client.get("/api/providers")
    assert response.status_code == 200
    providers = response.json()
    assert len(providers) >= 2
    ids = [p["provider_id"] for p in providers]
    assert "aws-earthsearch" in ids
    assert "planetary-computer" in ids


def test_api_system_status(client):
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["disk_total_bytes"] > 0
    assert data["active_workers"] > 0


def test_api_sources(client):
    response = client.get("/api/sources")
    assert response.status_code == 200
    sources = response.json()
    assert len(sources) >= 3
    source_ids = [s["id"] for s in sources]
    assert "aws-earthsearch" in source_ids
    assert "local-filesystem" in source_ids


def test_api_crs_recommend_endpoint(client):
    response = client.post(
        "/api/crs/recommend",
        json={"bbox": [76.10, 33.15, 79.20, 35.15]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["recommended_crs"] == "EPSG:32643"
    assert data["crosses_multiple_zones"] is True
    assert len(data["candidates"]) >= 3


def test_api_processing_recipes(client):
    response = client.get("/api/processing/recipes")
    assert response.status_code == 200
    recipes = response.json()
    assert len(recipes) >= 3
    recipe_ids = [r["id"] for r in recipes]
    assert "s2-aoi-cog" in recipe_ids
    assert "glacier-snow-ndsi" in recipe_ids
    assert "vegetation-ndvi" in recipe_ids


def test_spa_index_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "GeoHarvest" in response.text


