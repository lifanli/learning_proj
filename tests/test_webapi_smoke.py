from fastapi.testclient import TestClient
import threading
import time

import src.webapi.services as services
import src.webapi.app as app_module
from src.webapi.app import create_app
from src.webapi.task_runtime import BackgroundTaskRegistry


def test_webapi_smoke_endpoints():
    client = TestClient(create_app())

    for path in [
        '/api/health',
        '/api/dashboard',
        '/api/tasks',
        '/api/curriculum',
        '/api/settings',
        '/api/logs',
        '/api/knowledge-base',
    ]:
        response = client.get(path)
        assert response.status_code == 200, (path, response.text)


def test_webapi_settings_save_clears_worker_config_cache(tmp_path, monkeypatch):
    config_dir = tmp_path / 'config'
    config_dir.mkdir()
    settings_path = config_dir / 'settings.yaml'
    monkeypatch.setattr(services, 'CONFIG_PATH', settings_path)

    calls = []
    monkeypatch.setattr(services, 'clear_config_cache', lambda: calls.append('cleared'))

    services.save_settings_text('llm:\n  provider: openai\n')

    assert calls == ['cleared']


def test_webapi_settings_endpoint_does_not_return_or_save_api_key(tmp_path, monkeypatch):
    config_dir = tmp_path / 'config'
    config_dir.mkdir()
    settings_path = config_dir / 'settings.yaml'
    secret = 'dummy-test-secret-value'
    settings_path.write_text(
        'llm:\n  provider: openai\n  api_key_env: TEST_API_KEY\n  api_key: dummy-test-secret-value\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(services, 'CONFIG_PATH', settings_path)

    client = TestClient(create_app())

    loaded = client.get('/api/settings')
    saved = client.put(
        '/api/settings',
        json={'content': 'llm:\n  provider: openai\n  api_key_env: TEST_API_KEY\n  api_key: dummy-test-secret-value\n'},
    )

    assert loaded.status_code == 200
    assert secret not in loaded.text
    assert saved.status_code == 200
    assert saved.json()['settings']['llm']['api_key'] == ''
    assert secret not in settings_path.read_text(encoding='utf-8')


def test_webapi_system_state_redacts_api_key(tmp_path, monkeypatch):
    config_dir = tmp_path / 'config'
    config_dir.mkdir()
    settings_path = config_dir / 'settings.yaml'
    secret = 'dummy-system-state-secret'
    settings_path.write_text(
        'llm:\n  provider: openai\n  api_key_env: TEST_API_KEY\n  api_key: dummy-system-state-secret\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(services, 'CONFIG_PATH', settings_path)

    client = TestClient(create_app())
    response = client.get('/api/system/state')

    assert response.status_code == 200
    assert secret not in response.text
    assert response.json()['settings']['llm']['api_key'] == '***'


def test_webapi_material_detail_404_for_missing_item():
    client = TestClient(create_app())
    response = client.get('/api/materials/not-found')
    assert response.status_code == 404


def test_webapi_log_detail_blocks_path_traversal(tmp_path, monkeypatch):
    logs_dir = tmp_path / 'logs'
    config_dir = tmp_path / 'config'
    logs_dir.mkdir()
    config_dir.mkdir()
    (logs_dir / 'app.log').write_text('normal log line\n', encoding='utf-8')
    (config_dir / 'settings.yaml').write_text('secret: value\n', encoding='utf-8')
    monkeypatch.setattr(services, 'LOG_DIR', logs_dir)

    client = TestClient(create_app())

    valid = client.get('/api/logs/app.log')
    traversal = client.get('/api/logs/..%5Cconfig%5Csettings.yaml')

    assert valid.status_code == 200
    assert valid.json()['lines'] == ['normal log line']
    assert traversal.status_code == 404


def test_webapi_knowledge_file_blocks_sibling_prefix_escape(tmp_path, monkeypatch):
    kb_root = tmp_path / 'knowledge_base'
    sibling = tmp_path / 'knowledge_base_evil'
    kb_root.mkdir()
    sibling.mkdir()
    (kb_root / 'safe.md').write_text('safe content', encoding='utf-8')
    (sibling / 'secret.md').write_text('secret content', encoding='utf-8')
    monkeypatch.setattr(services, 'KB_ROOT', kb_root)

    client = TestClient(create_app())

    valid = client.get('/api/knowledge-base/file', params={'path': 'safe.md'})
    escaped = client.get('/api/knowledge-base/file', params={'path': '..\\knowledge_base_evil\\secret.md'})

    assert valid.status_code == 200
    assert valid.json()['content'] == 'safe content'
    assert escaped.status_code == 400


def test_webapi_tasks_list_uses_summary_and_detail_includes_result(tmp_path, monkeypatch):
    registry = BackgroundTaskRegistry(max_workers=1, storage_path=tmp_path / 'tasks.json')
    monkeypatch.setattr(app_module, 'registry', registry)
    try:
        task = registry.submit('test.large_result', lambda: {'payload': 'x' * 1000})
        client = TestClient(create_app())

        for _ in range(100):
            detail = client.get(f'/api/tasks/{task.id}').json()
            if detail['status'] == 'succeeded':
                break
            time.sleep(0.02)

        listing = client.get('/api/tasks')
        detail = client.get(f'/api/tasks/{task.id}')

        assert listing.status_code == 200
        assert detail.status_code == 200
        listed_task = listing.json()['items'][0]
        assert listed_task['id'] == task.id
        assert listed_task['has_result'] is True
        assert 'result_summary' in listed_task
        assert 'result' not in listed_task
        assert detail.json()['result']['payload'] == 'x' * 1000
    finally:
        registry.shutdown()


def test_webapi_task_retry_endpoint_resubmits_failed_task(tmp_path, monkeypatch):
    registry = BackgroundTaskRegistry(max_workers=1, storage_path=tmp_path / 'tasks.json')
    monkeypatch.setattr(app_module, 'registry', registry)
    calls = []

    def flaky_task(value):
        calls.append(value)
        if len(calls) == 1:
            raise RuntimeError('first attempt failed')
        return {'value': value, 'attempts': len(calls)}

    try:
        task = registry.submit('test.flaky', flaky_task, 'ok')
        client = TestClient(create_app())

        for _ in range(100):
            detail = client.get(f'/api/tasks/{task.id}').json()
            if detail['status'] == 'failed':
                break
            time.sleep(0.02)

        retry_response = client.post(f'/api/tasks/{task.id}/retry')
        retried_id = retry_response.json()['task']['id']
        for _ in range(100):
            retried = client.get(f'/api/tasks/{retried_id}').json()
            if retried['status'] == 'succeeded':
                break
            time.sleep(0.02)

        assert retry_response.status_code == 200
        assert retried['retry_of'] == task.id
        assert retried['result'] == {'value': 'ok', 'attempts': 2}
    finally:
        registry.shutdown()


def test_webapi_task_cancel_endpoint_marks_task(tmp_path, monkeypatch):
    registry = BackgroundTaskRegistry(max_workers=1, storage_path=tmp_path / 'tasks.json')
    monkeypatch.setattr(app_module, 'registry', registry)
    started = threading.Event()
    release = threading.Event()

    def blocking_task():
        started.set()
        release.wait(timeout=3)
        return {'done': True}

    try:
        registry.submit('test.blocking', blocking_task)
        assert started.wait(timeout=3)
        task = registry.submit('test.cancel', lambda: {'ok': True})
        client = TestClient(create_app())
        response = client.post(f'/api/tasks/{task.id}/cancel')

        assert response.status_code == 200
        assert response.json()['task']['status'] == 'canceled'
    finally:
        release.set()
        registry.shutdown()


def test_webapi_serves_vue_dist_and_preserves_api_404(tmp_path, monkeypatch):
    dist = tmp_path / 'dist'
    assets = dist / 'assets'
    assets.mkdir(parents=True)
    (dist / 'index.html').write_text('<html><body><div id="app">Study App</div></body></html>', encoding='utf-8')
    (assets / 'app.js').write_text('console.log("frontend")', encoding='utf-8')
    monkeypatch.setattr(app_module, 'FRONTEND_DIST', dist)

    client = TestClient(create_app())

    root = client.get('/')
    spa_route = client.get('/study')
    asset = client.get('/assets/app.js')
    api_root = client.get('/api')
    api_404 = client.get('/api/not-a-real-route')

    assert root.status_code == 200
    assert 'Study App' in root.text
    assert spa_route.status_code == 200
    assert 'Study App' in spa_route.text
    assert asset.status_code == 200
    assert 'console.log("frontend")' in asset.text
    assert api_root.status_code == 404
    assert api_root.json()['detail'] == 'API route not found'
    assert api_404.status_code == 404
    assert api_404.json()['detail'] == 'API route not found'
