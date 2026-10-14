# What the matched CANNIER comparison establishes

**The primary results do not establish a robust general improvement over CANNIER's classifier.** This experiment uses genuine original CANNIER features and labels, with our bounded context added under identical project-held-out evaluation.

## Primary: natural imbalance

| Task | Baseline AP | Context AP | Result |
|---|---:|---:|---|
| NOD-vs-rest | 0.004641 | 0.006960 | Increase; project uncertainty includes zero gain |
| Victim-vs-rest | 0.017761 | 0.017277 | Slight decrease; project uncertainty includes zero gain |

At a fixed 0.5 threshold, the context models flag no cases. Their zero MCC is not successful detection. Inner-validation-selected thresholds have separate results and do not justify replacing the primary endpoint after seeing it.

## Separate SMOTE sensitivity

Victim AP increases from 0.026556 to 0.029918 and fixed-threshold MCC from 0.028134 to 0.089941. Both paired project uncertainty intervals include no gain. This sampling experiment is secondary; it must not be presented as the natural-imbalance primary result.

## Narrower prioritization finding

The protocol also declared a top-10% budget ranked separately within each project. Under natural imbalance:

- NOD: 26/157 recovered by the baseline versus 51/157 with context. Its paired project uncertainty interval includes zero gain.
- Victims: 118/1001 (11.79%) versus 177/1001 (17.68%). The +5.89 percentage-point difference has a conditional project-bootstrap interval of [+0.25, +15.75] pp.

This is an exploratory secondary prioritization signal. Multiple metrics were examined, predictions are fixed during resampling, projects/context influenced earlier development, and parameterized cases can share source/cause families. It is not independent confirmation or proof of faster hybrid detection.

## Original CANNIER AP, now recoverable

From the authors' 30 released prediction repeats, mean AP is 0.490934 for NOD-vs-rest and 0.529366 for victim-vs-rest. These are newly calculated reference values, not AP numbers printed in the paper. Their original case-level folds and complete cohort differ from the matched project-fold experiment. Do not compare these reference values directly with the old FlakeXplain generic-instability AP of 0.0552.

## Completed work and next step

Completed: 86,781 matched cases across all 30 projects, 18 genuine features versus 18+66 context features, 200 fits, 40 replayed outer models, original-label verification, source exclusion audit, separate sampling analysis and 1,774 verification checks. The full unit suite ran 89 tests: 88 passed and one Linux-only test skipped.

Next: if pursuing a paper-improvement claim, test the prioritization finding prospectively on independent positive projects at a fixed inspection/rerun budget, complete human context validation, and measure actual detection yield/cost. Keep the mixed classification result visible. No new deployment fit or extra model search can substitute for that evidence.
