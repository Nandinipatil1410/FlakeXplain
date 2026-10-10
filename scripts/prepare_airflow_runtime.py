"""Reproduce globally installed dependencies for Airflow's system-site children.

Only the disposable CI base interpreter is changed. Isolated virtualenvs do not
read its site-packages or this .pth file. No upstream source/test is modified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

FAILURE_TARGETS = [
    'tests/operators/test_python_operator.py::TestPythonVirtualenvOperator::test_config_context',
    'tests/operators/test_virtualenv_operator.py::TestPythonVirtualenvOperator',
    'tests/task/task_runner/test_standard_task_runner.py::TestStandardTaskRunner::test_on_kill',
    'tests/utils/test_helpers.py::TestHelpers::test_reap_process_group',
    'tests/www_rbac/test_views.py::TestTriggerDag',
]


def check_tests(repo):
    from runtime import pytest_command, pytest_env, run_command
    xml = repo / 'logs/airflow-prerequisite-tests.xml'
    command = pytest_command('airflow', repo) + [
        '-p', 'no:randomly', '-p', 'no:cov', '--with-db-init',
        '--tb=short', '-q', '--log-cli-level=INFO', '--junitxml=' + str(xml),
    ] + FAILURE_TARGETS
    _, _, code = run_command(command, cwd=repo, env=pytest_env(repo),
                             log_path=repo / 'logs/airflow-prerequisite-tests.log')
    if code:
        raise SystemExit(code)


def bridge_line(dependencies):
    return "import site; site.addsitedir({!r})\n".format(str(dependencies))


def prepare(repo):
    python = repo / '.venv/bin/python'
    probe = (
        "import json,sys,sysconfig; print(json.dumps(dict("
        "dependencies=sysconfig.get_path('purelib'), "
        "base_site=sysconfig.get_path('purelib',vars={'base':sys.base_prefix,"
        "'platbase':sys.base_prefix}))))"
    )
    paths = json.loads(subprocess.check_output([str(python), '-c', probe], text=True))
    dependencies = Path(paths['dependencies']).resolve()
    base_site = Path(paths['base_site']).resolve()
    if dependencies == base_site or not dependencies.is_dir() or not base_site.is_dir():
        raise RuntimeError('Expected a separate Airflow venv and CI base site-packages')
    bridge = base_site / 'flakexplain_airflow.pth'
    content = bridge_line(dependencies)
    if bridge.exists() and bridge.read_text() != content:
        raise RuntimeError('Refusing to replace a different Airflow dependency bridge')
    bridge.write_text(content, encoding='utf8')
    # Verify both sides of the real virtualenv flag, without leaking packages
    # through PYTHONPATH or changing the operator's commands.
    checks = []
    with tempfile.TemporaryDirectory(prefix='airflow-runtime-') as folder:
        for system in (False, True):
            child = Path(folder) / ('system' if system else 'isolated')
            command = [str(python), '-m', 'virtualenv', '--no-download', str(child)]
            if system:
                command += ['--system-site-packages']
            subprocess.run(command, check=True)
            assertion = ('import funcsigs; import airflow; print(airflow.__version__)' if system else
                         "import importlib.util; assert importlib.util.find_spec('funcsigs') is None")
            subprocess.run([str(child / 'bin/python'), '-c', assertion], check=True)
            checks.append({'system_site_packages': system, 'passed': True})
    python2 = subprocess.check_output(['python2', '--version'], stderr=subprocess.STDOUT, text=True).strip()
    if not python2.startswith('Python 2.7.'):
        raise RuntimeError('The pinned upstream tests require Python 2.7')
    record = dict(bridge=str(bridge), content=content,
                  sha256=hashlib.sha256(content.encode()).hexdigest(),
                  python2=python2, virtualenv_checks=checks,
                  pid1=Path('/proc/1/comm').read_text().strip())
    logs = repo / 'logs'
    logs.mkdir(exist_ok=True)
    (logs / 'airflow-runtime-fixtures.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--check-tests', action='store_true',
                        help='Run diagnostic prerequisite tests as the experiment user')
    args = parser.parse_args()
    (check_tests if args.check_tests else prepare)(args.repo.resolve())
