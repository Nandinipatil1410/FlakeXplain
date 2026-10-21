"""Analyse the v0.10 CodeBERT out-of-fold scores against extra_trees_v2_context (frozen protocol).

Reads the five Colab outputs fold_<k>_predictions.csv / fold_<k>_run.json, verifies them against
the freeze record, joins labels and the comparator's out-of-fold scores, and computes the
protocol's metrics, the project-bootstrap interval for delta AP and the section 6 decision.

Run only after all five real folds exist. --fake-from-et writes stand-in fold files built from the
comparator's own scores (plus optional noise) into a scratch folder, to test this script.
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_pilot import metrics, weighted_ap  # same AP / top-10% / MCC definitions as v0.2

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/llm-codebert-v0.10'
EVIDENCE = ROOT / 'local-evidence/llm-codebert-v0.10'
DATA = ROOT / 'dataset/v0.1'
COMPARATOR = 'extra_trees_v2_context'
FROZEN = dict(model='microsoft/codebert-base', max_len=256, epochs=3, lr=2e-5, weight_decay=0.01,
              warmup_fraction=0.06, batch_size=32, seed=20261021)
BOOT = 2000
MIN_EFFECT = 0.01
EXPECTED_TESTS, EXPECTED_POSITIVES, EXPECTED_PROJECTS = 96118, 693, 35


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv_gz(path):
    with gzip.open(path, 'rt', encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def load_reference(protocol):
    """Labels, projects, folds, label-evidence patterns and comparator scores, keyed by example_id."""
    comparator_file = ROOT / protocol['comparator_predictions']
    if sha(comparator_file) != protocol['comparator_predictions_sha256']:
        raise ValueError('Comparator predictions differ from the freeze record')
    folds = {r['project']: int(r['outer_test_fold']) for r in csv.DictReader(open(DATA / 'splits_outer.csv'))}
    ref = {}
    for r in read_csv_gz(comparator_file):
        if folds[r['project']] != int(r['outer_fold']):
            raise ValueError(f'Fold mismatch for {r["example_id"]}')
        ref[r['example_id']] = dict(project=r['project'], fold=int(r['outer_fold']), label=int(r['label']),
                                    et_score=float(r[f'{COMPARATOR}_score']),
                                    et_threshold=float(r[f'{COMPARATOR}_threshold']))
    for r in read_csv_gz(DATA / 'labels.csv.gz'):
        if int(r['label']) != ref[r['example_id']]['label']:
            raise ValueError(f'Label mismatch for {r["example_id"]}')
        # Label evidence, used only after all scores are fixed (protocol section 7).
        original_failures = int(r['original_fail_count']) + int(r['original_error_count'])
        ref[r['example_id']]['pattern'] = (None if r['label'] != '1' else
                                           'fails_in_original_order' if original_failures else 'od_looking')
    if len(ref) != EXPECTED_TESTS or sum(v['label'] for v in ref.values()) != EXPECTED_POSITIVES:
        raise ValueError('Reference data do not match dataset/v0.1')
    return ref, folds


def load_codebert(evidence, protocol, ref, folds):
    """Verify each fold's run record and predictions; return scores, thresholds and run records."""
    scores, runs, files = {}, [], {}
    for k in range(5):
        run_file, pred_file = evidence / f'fold_{k}_run.json', evidence / f'fold_{k}_predictions.csv'
        run = json.load(open(run_file, encoding='utf-8'))
        problems = []
        if run.get('fold') != k:
            problems.append(f'fold is {run.get("fold")}')
        if run.get('smoke') is not False:
            problems.append('smoke run')
        if run.get('input_sha256') != protocol['input_sha256']:
            problems.append('input SHA-256 differs')
        problems += [f'{key}={run.get(key)!r}, protocol {value!r}' for key, value in FROZEN.items()
                     if run.get(key) != value]
        fold_projects = sorted(p for p, f in folds.items() if f == k)
        if sorted(run.get('test_projects', [])) != fold_projects:
            problems.append('test projects differ from splits_outer.csv')
        with open(pred_file, encoding='utf-8', newline='') as f:
            rows = list(csv.DictReader(f))
        ids = [r['example_id'] for r in rows]
        fold_ids = {i for i, v in ref.items() if v['fold'] == k}
        if len(ids) != len(set(ids)) or set(ids) != fold_ids:
            problems.append(f'{len(ids)} predictions, {len(set(ids) & fold_ids)} of {len(fold_ids)} fold tests')
        if run.get('test') != len(ids):
            problems.append(f'run says {run.get("test")} test rows, file has {len(ids)}')
        values = np.array([float(r['score']) for r in rows])
        if not (np.isfinite(values).all() and (values >= 0).all() and (values <= 1).all()):
            problems.append('scores outside [0, 1]')
        if problems:
            raise ValueError(f'fold {k}: ' + '; '.join(problems))
        overlap = set(ids) & set(scores)
        if overlap:
            raise ValueError(f'fold {k}: {len(overlap)} example_ids already predicted by another fold')
        scores.update(zip(ids, values))
        runs.append(run)
        files[pred_file.name], files[run_file.name] = sha(pred_file), sha(run_file)
    if set(scores) != set(ref):
        raise ValueError(f'Predictions cover {len(scores)} tests, expected {len(ref)}')
    gpus = {r.get('gpu') for r in runs}
    if len(gpus) != 1 or 'A100' not in str(next(iter(gpus))):  # AMENDMENT_1.md
        raise ValueError(f'All folds must run on one A100 GPU type, found {sorted(map(str, gpus))}')
    return scores, runs, files


def bootstrap_delta(y, a, b, projects):
    """Project bootstrap of AP(a) - AP(b): resample the 35 projects, predictions held fixed."""
    _, inverse = np.unique(projects, return_inverse=True)
    n = int(inverse.max() + 1)
    rng = np.random.default_rng(FROZEN['seed'])
    deltas, invalid = [], 0
    for _ in range(BOOT):
        w = rng.multinomial(n, np.repeat(1 / n, n))[inverse].astype(float)
        aa, bb = weighted_ap(y, a, w), weighted_ap(y, b, w)
        if aa is None or bb is None:
            invalid += 1
        else:
            deltas.append(aa - bb)
    low, high = np.quantile(deltas, [.025, .975])
    return dict(resamples=BOOT, valid=len(deltas), without_positives=invalid, seed=FROZEN['seed'],
                interval_95=[float(low), float(high)])


def decide(delta, low, high):
    if delta >= MIN_EFFECT and low > 0:
        return 'CodeBERT better'
    if delta <= -MIN_EFFECT and high < 0:
        return 'Extra Trees better'
    return 'No clear difference'


def threshold_metrics(y, score, prediction, ids):
    m = metrics(y, score, prediction, ids)
    tp, fp, tn, fn = m['tp'], m['fp'], m['tn'], m['fn']
    negative_f1 = 2 * tn / (2 * tn + fn + fp) if 2 * tn + fn + fp else 0.0
    m['macro_f1'] = (m['f1'] + negative_f1) / 2
    return m


def top_set(score, ids, fraction):
    budget = math.ceil(fraction * len(score))
    return set(np.lexsort((ids, -score))[:budget]), budget


def analyse(ref, cb_scores, runs):
    ids = np.array(sorted(ref))
    y = np.array([ref[i]['label'] for i in ids])
    projects = np.array([ref[i]['project'] for i in ids])
    fold = np.array([ref[i]['fold'] for i in ids])
    et = np.array([ref[i]['et_score'] for i in ids])
    cb = np.array([cb_scores[i] for i in ids])
    cb_threshold = np.array([runs[f]['threshold'] for f in fold])
    et_threshold = np.array([ref[i]['et_threshold'] for i in ids])
    models = {'codebert': (cb, cb >= cb_threshold), COMPARATOR: (et, et >= et_threshold)}

    pooled = {name: threshold_metrics(y, s, p, ids) for name, (s, p) in models.items()}
    per_fold = []
    for k in range(5):
        part = fold == k
        row = dict(fold=k, cases=int(part.sum()), positives=int(y[part].sum()),
                   projects=sorted(set(projects[part])), codebert_threshold=runs[k]['threshold'],
                   codebert_best_epoch=runs[k]['best_epoch'], codebert_val_ap=runs[k]['best_val_ap'])
        for name, (s, p) in models.items():
            m = threshold_metrics(y[part], s[part], p[part], ids[part])
            row[name] = {key: m[key] for key in ('average_precision', 'precision', 'recall', 'f1', 'mcc',
                                                 'macro_f1', 'recall_at_top_10_percent')}
        per_fold.append(row)
    per_project = []
    for project in sorted(set(projects)):
        part = projects == project
        row = dict(project=project, fold=int(fold[part][0]), cases=int(part.sum()), positives=int(y[part].sum()))
        for name, (s, _) in models.items():
            row[f'{name}_ap'] = weighted_ap(y[part], s[part], np.ones(part.sum())) if y[part].any() else None
        per_project.append(row)

    delta = pooled['codebert']['average_precision'] - pooled[COMPARATOR]['average_precision']
    boot = bootstrap_delta(y, cb, et, projects)
    decision = decide(delta, *boot['interval_95'])

    # Section 7, descriptive. Patterns come from label evidence and are provisional.
    top_cb, budget1 = top_set(cb, ids, .01)
    top_et, _ = top_set(et, ids, .01)
    positives = set(np.flatnonzero(y == 1))
    overlap = dict(top_fraction=0.01, cases_per_model=budget1, shared_cases=len(top_cb & top_et),
                   codebert_true_positives=len(top_cb & positives), extra_trees_true_positives=len(top_et & positives),
                   shared_true_positives=len(top_cb & top_et & positives))
    pattern = np.array([ref[i]['pattern'] or '' for i in ids])
    top10 = {name: top_set(s, ids, .10)[0] for name, (s, _) in models.items()}
    patterns = []
    for name in ('od_looking', 'fails_in_original_order'):
        members = set(np.flatnonzero(pattern == name))
        row = dict(pattern=name, positives=len(members))
        for model, (_, p) in models.items():
            row[f'{model}_recall_at_threshold'] = float(p[list(members)].mean()) if members else None
            row[f'{model}_in_top_10_percent'] = len(members & top10[model])
            row[f'{model}_in_top_1_percent'] = len(members & (top_cb if model == 'codebert' else top_et))
        patterns.append(row)

    return dict(pooled=pooled, delta_ap=delta, bootstrap=boot, decision=decision,
                base_rate_ap=float(y.mean()), per_fold=per_fold, per_project=per_project,
                top_1_percent_overlap=overlap, patterns=patterns)


def fake_from_et(ref, protocol, folds, out, noise):
    """Stand-in fold files from the comparator's scores (test only; not results)."""
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(1)
    for k in range(5):
        rows = sorted((i, v) for i, v in ref.items() if v['fold'] == k)
        with open(out / f'fold_{k}_predictions.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['example_id', 'score'])
            for i, v in rows:
                w.writerow([i, f'{float(np.clip(v["et_score"] + rng.normal(0, noise), 0, 1)):.8f}'])
        threshold = rows[0][1]['et_threshold']
        run = dict(fold=k, smoke=False, input_sha256=protocol['input_sha256'], **FROZEN, test=len(rows),
                   test_projects=sorted(p for p, f in folds.items() if f == k), best_epoch=1,
                   best_val_ap=None, threshold=threshold, gpu='NVIDIA A100-SXM4-40GB (fake)',
                   fake_from_et=True, noise=noise)
        json.dump(run, open(out / f'fold_{k}_run.json', 'w', encoding='utf-8'), indent=1)
    print(f'wrote fake fold files (noise {noise}) to {out}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=EVIDENCE)
    parser.add_argument('--out', type=Path, default=REPORT / 'results.json')
    parser.add_argument('--fake-from-et', type=Path, metavar='DIR', help='write stand-in fold files to DIR and stop')
    parser.add_argument('--noise', type=float, default=0.0)
    args = parser.parse_args()
    protocol = json.load(open(REPORT / 'protocol.json', encoding='utf-8'))
    if sha(REPORT / 'PROTOCOL.md') != protocol['protocol_sha256']:
        raise ValueError('PROTOCOL.md differs from the freeze record')
    ref, folds = load_reference(protocol)
    if len(folds) != EXPECTED_PROJECTS:
        raise ValueError('Expected 35 projects')
    if args.fake_from_et:
        if args.fake_from_et.resolve() == EVIDENCE.resolve():
            raise ValueError('Refusing to write fake files into the real evidence folder')
        fake_from_et(ref, protocol, folds, args.fake_from_et, args.noise)
        return
    real = args.evidence.resolve() == EVIDENCE.resolve()
    if not real and args.out.resolve().parent == REPORT.resolve():
        raise ValueError('Test runs on other evidence must not write into reports/llm-codebert-v0.10')
    scores, runs, files = load_codebert(args.evidence, protocol, ref, folds)
    result = analyse(ref, scores, runs)
    amendments = sorted(p.name for p in REPORT.glob('AMENDMENT_*.md'))
    record = dict(version='v0.10', protocol_sha256=protocol['protocol_sha256'], comparator=COMPARATOR,
                  evidence=str(args.evidence), real_evidence=real, amendments=amendments, input_files=files,
                  runs=[{key: r.get(key) for key in ('fold', 'fit', 'fit_positives', 'val', 'val_positives', 'test',
                                                     'epoch_log', 'best_epoch', 'best_val_ap', 'threshold',
                                                     'train_seconds', 'gpu', 'torch', 'transformers', 'sklearn',
                                                     'python')} for r in runs],
                  **result)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(record, open(args.out, 'w', encoding='utf-8'), indent=1)
    cb, et = result['pooled']['codebert'], result['pooled'][COMPARATOR]
    low, high = result['bootstrap']['interval_95']
    print(f'AP CodeBERT {cb["average_precision"]:.4f}  AP ET {et["average_precision"]:.4f}  '
          f'delta {result["delta_ap"]:+.4f} [{low:+.4f}, {high:+.4f}]  -> {result["decision"]}')
    print(f'wrote {args.out}')


if __name__ == '__main__':
    main()
