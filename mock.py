async def stub_curl_json(self, node) -> dict:
    """Return static key service status data for tests."""
    return {
        "current_key_rate": 3.5,
        "key_size": 256,
        "master_SAE_ID": "precisA-fileTransfer1",
        "max_SAE_ID_count": 0,
        "max_key_count": 100,
        "max_key_per_request": 10,
        "max_key_size": 324,
        "min_key_size": 128,
        "slave_SAE_ID": "campus-fileTransfer1",
        "source_KME_ID": "precisA",
        "stored_key_count": 42,
        "target_KME_ID": "campus",
    }
