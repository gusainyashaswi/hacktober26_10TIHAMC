import json
import argparse
import os
import subprocess
from datetime import datetime, UTC
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from nobluff.api import create_app
from nobluff.model import OllamaSettings
from nobluff.pipeline import AnalysisService
from nobluff.repositories import RepositoryLoader
from nobluff.verification.policy import verify_snapshot
from nobluff.reporting import export_report

ROOT = Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description='Create a controlled fixture and run actual local Qwen/Docker investigations.')
parser.add_argument('--fixture-directory', type=Path, default=Path('/tmp/nobluff-demo-fixture'))
parser.add_argument('--prepare-only', action='store_true')
parser.add_argument('--case', choices=['unicode','contradicted','inconclusive'])
args=parser.parse_args()
FIXTURE = args.fixture_directory.resolve()
FIXTURE.mkdir(exist_ok=True)
env = {**os.environ, 'GIT_AUTHOR_NAME':'NoBluff Fixture','GIT_AUTHOR_EMAIL':'fixture@example.invalid',
       'GIT_COMMITTER_NAME':'NoBluff Fixture','GIT_COMMITTER_EMAIL':'fixture@example.invalid',
       'GIT_AUTHOR_DATE':'2026-10-31T20:00:00+05:30','GIT_COMMITTER_DATE':'2026-10-31T20:00:00+05:30'}
def git(*args):
    return subprocess.run(['git','-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null',*args],cwd=FIXTURE,env=env,capture_output=True,text=True,check=True).stdout.strip()
if not (FIXTURE/'.git').exists():
    if any(FIXTURE.iterdir()): raise SystemExit('Refusing to initialize a non-empty fixture directory.')
    git('init','-b','main')
    code="def export_csv(path, rows):\n    with open(path, 'w', encoding='ascii') as stream:\n        stream.write(','.join(rows))\n"
    (FIXTURE/'exporter.py').write_text(code)
    (FIXTURE/'README.md').write_text('export_csv writes rows to a file. Unicode customer names should be supported.\n')
    git('add','.'); git('commit','-m','Controlled original fixture')
    original=git('rev-parse','HEAD')
    (FIXTURE/'exporter.py').write_text(code.replace("'ascii'","'utf-8'"))
    git('add','.');git('commit','-m','Controlled fix fixture')
    fix=git('rev-parse','HEAD')
else:
    fix=git('rev-parse','HEAD');original=git('rev-parse','HEAD~1')
if args.prepare_only:
    print(json.dumps({'repository':'example/nobluff-fixture','original_revision':original,'comparison_revision':fix,'NOBLUFF_LOCAL_REPOSITORIES':{'https://github.com/example/nobluff-fixture':str(FIXTURE)}},indent=2))
    raise SystemExit(0)
output=ROOT/'examples'/'end-to-end';output.mkdir(exist_ok=True)
test="from exporter import export_csv\ndef test_unicode(tmp_path):\n    output = tmp_path / 'out.csv'\n    export_csv(output, ['José'])\n    assert output.read_text(encoding='utf-8') == 'José'\n"
cases=[('unicode', 'When export_csv writes the row José to a file, it raises UnicodeEncodeError.'),
       ('contradicted', 'export_csv opens output files using UTF-8 encoding.'),
       ('inconclusive', 'I suspect export_csv intermittently fails because a remote database connection is unavailable.')]
loader=RepositoryLoader({'https://github.com/example/nobluff-fixture':str(FIXTURE)})
service=AnalysisService(OllamaSettings.from_env(), snapshot_loader=loader.load, runner=verify_snapshot)
with TestClient(create_app(service)) as client:
    for name,text in cases:
        if args.case and args.case != name: continue
        request={'repository':'example/nobluff-fixture','revision':original,'comparison_revision':fix,'report_text':text}
        (output/f'{name}-input.json').write_text(json.dumps(request,indent=2,ensure_ascii=False)+'\n')
        accepted=client.post('/api/analyses',json=request)
        accepted.raise_for_status()
        identifier=accepted.json()['id'];url=f'/api/analyses/{identifier}'
        report=client.get(url).json()
        print(name,'source stage',report['stage'],flush=True)
        if report['stage']=='error':
            print(report['errors'],flush=True)
        (output/f'{name}-source-output.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
        if name=='unicode' and report['claims'] and report['stage']=='complete':
            plan={'claim_id':report['claims'][0]['id'],'test_code':test,'approved':True,'expected_failure':'UnicodeEncodeError'}
            (output/'approved-test.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n')
            response=client.post(url+'/comparison',json=plan);response.raise_for_status()
            report=client.get(url).json()
        (output/f'{name}-output.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
        (output/f'{name}-output.md').write_text(client.get(url+'/export?format=markdown').text)
        print(name,[(x['assessment'],x['explanation']) for x in report['findings']],report['comparisons'],flush=True)
with httpx.Client(trust_env=False) as client:
    tags=client.get('http://127.0.0.1:11434/api/tags').json()
metadata={'generated_at':datetime.now(UTC).isoformat(),'synthetic_input':True,'outputs':'actual local Qwen3-8B and Docker outputs; not manually authored verdicts',
          'model':next(m for m in tags['models'] if m['name']=='qwen3:8b'),'original':original,'fix':fix,
          'fixture_directory':str(FIXTURE),'runtime':'API exercised through FastAPI TestClient; real Ollama HTTP and real Docker; no fake model/runner',
          'limitations':'Three tiny controlled cases are not a public-issue accuracy benchmark.'}
(output/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
loader.close()
