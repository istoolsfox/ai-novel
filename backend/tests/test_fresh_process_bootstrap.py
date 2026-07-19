import os
import subprocess
import sys
from pathlib import Path


def test_fresh_python_process_installs_security_and_migration_layers(tmp_path):
    database = tmp_path / "fresh.db"
    data_dir = tmp_path / "data"
    key_file = tmp_path / "master.key"
    script = """
from fastapi.testclient import TestClient
from backend.app.main import app, init_app
from backend.app.database import connect
init_app()
with TestClient(app) as client:
    assert client.get('/api/security/status').status_code == 200
    migration = client.get('/api/migrations/status')
    assert migration.status_code == 200
    assert migration.json()['current_version'] == 4
    release = client.get('/api/release/info')
    assert release.status_code == 200
    assert release.json()['version'] == '1.0.0'
    assert release.json()['release_channel'] == 'stable'
with connect() as conn:
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
assert 'encrypted_credentials' in tables
assert 'schema_migrations' in tables
assert 'application_state' in tables
print('fresh-bootstrap-ok')
"""
    env = {
        **os.environ,
        "AI_NOVEL_DATABASE_URL": f"sqlite:///{database}",
        "AI_NOVEL_DATA_DIR": str(data_dir),
        "AI_NOVEL_MASTER_KEY_FILE": str(key_file),
        "AI_NOVEL_AUTO_MIGRATE": "1",
        "AI_NOVEL_RUNTIME_SYNC": "1",
    }
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "fresh-bootstrap-ok" in result.stdout
    assert key_file.is_file()
