import importlib


def test_blank_optional_env_values_fall_back_to_defaults(monkeypatch) -> None:
    monkeypatch.setenv("PHILALENS_DATA_DIR", "")
    monkeypatch.setenv("PHILALENS_STAMP_YOLO_MODEL_PATH", "")
    monkeypatch.setenv("PHILALENS_CATALOG_DB_URL", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")

    import philalens.config

    importlib.reload(philalens.config)
    settings = philalens.config.Settings()

    assert settings.data_dir.name == "local"
    assert settings.stamp_yolo_model_path.name == "code2k13-philately-tool-model.pt"
    assert settings.catalog_db_url is None
    assert settings.openai_api_key is None
