"""Evidence identity, exclusion, and environment/round isolation checks."""
import csv
import hashlib
import io
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import consolidate_workflow_evidence as audit


class EvidenceAuditTests(unittest.TestCase):
    def test_class_names_disambiguate_same_file_and_method(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'round.xml'
            path.write_text('<testsuite><testcase file="tests/test_a.py" classname="A" name="test_x"/>'
                            '<testcase file="tests/test_a.py" classname="B" name="test_x"><failure/></testcase></testsuite>')
            outcomes, counts, missing = audit.parse_junit(path)
            self.assertEqual(len(outcomes), 2)
            self.assertEqual(counts['FAIL'], 1)
            self.assertEqual(missing, 0)

    def test_duplicate_phase_rows_do_not_create_a_flaky_label(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'round.xml'
            path.write_text('<testsuite><testcase classname="A" name="test_x"/>'
                            '<testcase classname="A" name="test_x"><error/></testcase></testsuite>')
            outcomes, counts, _ = audit.parse_junit(path)
            self.assertEqual(sum(counts.values()), 2)
            self.assertEqual(audit.label_outcomes(list(outcomes.values()) + ['PASS']), 'ambiguous_duplicate')

    def test_skips_and_missing_are_not_strict_negatives(self):
        self.assertEqual(audit.label_outcomes(['PASS', 'PASS']), 'not_observed_flaky')
        for value in ('SKIP', 'MISSING'):
            self.assertEqual(audit.label_outcomes(['PASS', value]), 'pass_with_skips_or_missing')
        self.assertEqual(audit.label_outcomes(['FAIL', 'SKIP']), 'failure_only')
        self.assertEqual(audit.label_outcomes(['PASS', 'ERROR']), 'observed_flaky')

    def test_named_module_collection_skip_is_retained_without_accepting_active_nameless_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'round.xml'
            path.write_text('<testsuite><testcase classname="" name="tests.optional"><skipped/></testcase>'
                            '<testcase classname="" name="unresolved_active"/></testsuite>')
            outcomes, _, missing = audit.parse_junit(path)
            self.assertEqual(missing, 1)
            self.assertEqual(outcomes[('', '', 'tests.optional')], 'SKIP')

    def test_acceptance_requires_identity_and_environment_matching(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder) / 'sample'
            (repo / 'results').mkdir(parents=True)
            (repo / 'logs').mkdir()
            xml = '<testsuite><testcase classname="A" name="test_x"/><testcase classname="B" name="test_y"/></testsuite>'
            (repo / 'logs/baseline.xml').write_text(xml)
            env = dict(id='environment-a', commit='a' * 40)
            baseline = dict(status='PASSED', environment_id=env['id'], collected_count=2, xml_file='logs/baseline.xml')
            manifest = dict(environment_id=env['id'], environment=env, collected_count=2,
                            original_rounds=[], random_rounds=[], reverse_rounds=[])
            rng = random.Random(42 + len(repo.name))
            for config, total in [('original', 12), ('random', 12), ('reverse', 1)]:
                for n in range(1, total + 1):
                    filename = f'{config}_run_{n}.xml'
                    (repo / 'results' / filename).write_text(xml)
                    manifest[config + '_rounds'].append(dict(xml_file=filename, round=n,
                        config=config + '-order', seed=rng.randint(100000,999999) if config=='random' else None,
                        exit_code=0, duration_seconds=1))
            for name, value in [('environment.json', env), ('baseline_state.json', baseline), ('results/execution_manifest.json', manifest)]:
                (repo / name).write_text(json.dumps(value))
            class Sink:
                def writerow(self, value):
                    pass
            def run():
                return audit.audit_project(repo, (Sink(), Sink(), Sink()), {})
            result = run()
            self.assertEqual(result['status'], 'protocol_complete_local_checks')
            self.assertEqual(result['labels'], {'not_observed_flaky': 2})
            (repo / 'results/random_run_1.xml').write_text(xml.replace('test_y', 'test_z'))
            self.assertEqual(run()['status'], 'incomplete_or_ambiguous')

            # A documented exclusion requires both the exact commit and pinned
            # source hash. It cannot bypass the environment gate or raw counts.
            baseline['environment_id'] = env['id']
            (repo / 'baseline_state.json').write_text(json.dumps(baseline))
            check_xml = xml.replace('classname="B" name="test_y"', 'classname="" name="project"')
            (repo / 'logs/baseline.xml').write_text(check_xml)
            for path in (repo / 'results').glob('*.xml'):
                path.write_text(check_xml)
            self.assertEqual(run()['status'], 'incomplete_or_ambiguous')
            source_root = Path(folder) / 'pinned-source'
            source_root.mkdir()
            source = source_root / 'plugin.py'
            source.write_text("class CheckdocsItem: pass\n")
            policy = dict(commit=env['commit'], excluded_identities=[dict(identity=['','','project'],reason='package check')],
                          source_evidence=[dict(path='plugin.py',sha256=hashlib.sha256(source.read_bytes()).hexdigest())])
            result = audit.audit_project(repo, (Sink(),Sink(),Sink()), {}, policy, source_root)
            self.assertEqual(result['status'], 'protocol_complete_with_exclusions')
            self.assertEqual(result['eligible_tests'], 1)
            self.assertEqual(result['tests'], 2)
            self.assertEqual(result['excluded_identity_count'], 1)
            source.write_text('changed source')
            result = audit.audit_project(repo, (Sink(),Sink(),Sink()), {}, policy, source_root)
            self.assertEqual(result['status'], 'incomplete_or_ambiguous')
            self.assertFalse(result['resolution_verified'])

            source.write_text("class CheckdocsItem: pass\n")
            policy['commit'] = 'b' * 40
            result = audit.audit_project(repo, (Sink(),Sink(),Sink()), {}, policy, source_root)
            self.assertFalse(result['resolution_verified'])
            self.assertEqual(result['status'], 'incomplete_or_ambiguous')
            policy['commit'] = env['commit']

            # Changing inputs cannot be repaired by stripping arbitrary numeric
            # parameter IDs. A verified family exclusion leaves the stable case.
            baseline_xml = xml.replace('test_y', 'unstable[baseline]')
            (repo / 'logs/baseline.xml').write_text(baseline_xml)
            for i, path in enumerate((repo / 'results').glob('*.xml')):
                path.write_text(xml.replace('test_y', f'unstable[{i}]'))
            self.assertEqual(run()['status'], 'incomplete_or_ambiguous')
            policy['excluded_identities'] = []
            policy['excluded_functions'] = [dict(classname='B',function='unstable',reason='unverifiable varying inputs')]
            result = audit.audit_project(repo, (Sink(),Sink(),Sink()), {}, policy, source_root)
            self.assertEqual(result['status'], 'protocol_complete_with_exclusions')
            self.assertEqual(result['eligible_tests'], 1)
            self.assertEqual(result['eligible_labels'], {'not_observed_flaky': 1})
            (repo / 'results/random_run_1.xml').write_text(xml)
            baseline['environment_id'] = 'environment-b'
            (repo / 'baseline_state.json').write_text(json.dumps(baseline))
            self.assertEqual(run()['status'], 'incomplete_or_ambiguous')


if __name__ == '__main__':
    unittest.main()
