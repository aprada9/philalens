from pathlib import Path

from philalens.config import Settings, load_env_file


def test_blank_optional_env_values_fall_back_to_defaults(monkeypatch) -> None:
    monkeypatch.setenv("PHILALENS_DATA_DIR", "")
    monkeypatch.setenv("PHILALENS_STAMP_YOLO_MODEL_PATH", "")
    monkeypatch.setenv("PHILALENS_CATALOG_DB_URL", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")

    settings = Settings()

    assert settings.data_dir.name == "local"
    assert settings.stamp_yolo_model_path.name == "code2k13-philately-tool-model.pt"
    assert settings.catalog_db_url is None
    assert settings.openai_api_key is None


def test_settings_read_environment_at_instantiation(monkeypatch) -> None:
    monkeypatch.setenv("PHILALENS_VISION_PROVIDER", "none")
    before = Settings()
    assert before.vision_provider == "none"

    monkeypatch.setenv("PHILALENS_VISION_PROVIDER", "openai")
    monkeypatch.setenv("PHILALENS_OPENAI_VISION_MODEL", "gpt-test")
    after = Settings()

    assert after.vision_provider == "openai"
    assert after.openai_vision_model == "gpt-test"


def test_load_env_file_does_not_override_existing_environment(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("PHILALENS_TEST_EXISTING", "from-environ")
    monkeypatch.delenv("PHILALENS_TEST_NEW", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n"
        "PHILALENS_TEST_EXISTING=from-file\n"
        'PHILALENS_TEST_NEW="from-file"\n'
        "not a key value line\n",
        encoding="utf-8",
    )

    load_env_file(env_file)

    import os

    assert os.environ["PHILALENS_TEST_EXISTING"] == "from-environ"
    assert os.environ["PHILALENS_TEST_NEW"] == "from-file"
    monkeypatch.delenv("PHILALENS_TEST_NEW", raising=False)
