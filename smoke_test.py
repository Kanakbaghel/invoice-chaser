import sys, os
# ensure webapp package modules are importable when running this script from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'webapp'))
from webapp.app import app

client = app.test_client()

for path in ['/api/languages', '/api/sample?snapshot=2013-03-01']:
    res = client.get(path)
    print(path, '->', res.status_code)
    try:
        j = res.get_json()
        if isinstance(j, dict):
            print('  keys:', list(j.keys())[:10])
        else:
            print('  type:', type(j))
    except Exception as e:
        print('  json error:', e)
