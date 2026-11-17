import json
from pathlib import Path
from app.services.advanced_visualization_service import analyze_repository


def test_extracts_tree_languages_technologies_and_dependencies(tmp_path):
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src' / 'main.py').write_text('from src.util import run\nimport requests\n')
    (tmp_path / 'src' / 'util.py').write_text('def run(): return True\n')
    (tmp_path / 'package.json').write_text(json.dumps({'dependencies': {'react': '^18'}}))
    result = analyze_repository(str(tmp_path))
    assert result['summary']['total_files'] == 3
    assert result['languages'][0]['name'] == 'Python'
    assert any(t['name'] == 'react' for t in result['technologies'])
    assert any(e['type'] == 'internal' for e in result['dependency_graph']['edges'])
    assert any(e['type'] == 'external-package' for e in result['dependency_graph']['edges'])
    assert result['tree']['children'][0]['type'] == 'directory'


def test_excludes_secrets_generated_dirs_and_symlinks(tmp_path):
    (tmp_path / '.env').write_text('TOKEN=secret')
    (tmp_path / 'id_rsa').write_text('private')
    (tmp_path / 'node_modules').mkdir()
    (tmp_path / 'node_modules' / 'ignored.js').write_text('bad')
    (tmp_path / 'ok.py').write_text('print(1)')
    outside = tmp_path.parent / 'outside.py'
    outside.write_text('secret')
    try:
        (tmp_path / 'linked.py').symlink_to(outside)
    except OSError:
        pass
    result = analyze_repository(str(tmp_path))
    paths = [x['path'] for x in result['tree']['children']]
    assert paths == ['ok.py']


def test_empty_and_malformed_files_are_partial_not_fatal(tmp_path):
    (tmp_path / 'broken.py').write_text('def nope(:\n')
    result = analyze_repository(str(tmp_path))
    assert result['summary']['total_files'] == 1
    assert result['dependency_graph']['nodes']
    assert any('malformed' in w for w in result['warnings'])


def test_empty_repository(tmp_path):
    result = analyze_repository(str(tmp_path))
    assert result['summary']['total_files'] == 0
    assert result['languages'] == []
    assert result['dependency_graph']['edges'] == []
