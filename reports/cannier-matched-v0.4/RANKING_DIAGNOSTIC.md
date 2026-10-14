# Secondary within-project ranking diagnostic

The protocol declared top ceil(10%) ranked separately inside each project. This audit independently recomputes that metric and adds paired project-resampling uncertainty after inspecting the primary comparison. No model, threshold, feature or split is changed. It is a secondary diagnostic, not a replacement primary endpoint.

| Task / balance | Baseline recovered | Context recovered | Recall difference | 95% project interval |
|---|---:|---:|---:|---|
| NOD-vs-Rest / natural | 26/157 | 51/157 | +15.92 percentage points | [-18.69, +39.48] pp |
| NOD-vs-Rest / author_smote_sensitivity | 38/157 | 53/157 | +9.55 percentage points | [-13.86, +20.13] pp |
| Victim-vs-Rest / natural | 118/1001 | 177/1001 | +5.89 percentage points | [+0.25, +15.75] pp |
| Victim-vs-Rest / author_smote_sensitivity | 152/1001 | 189/1001 | +3.70 percentage points | [-4.54, +14.02] pp |

All variants select the same 8,691 original cases in aggregate (ceil(10%) within each project). These are source-case counts, not independent cause counts or measured rerun savings. The intervals resample fixed predictions over 30 projects and omit refitting/prior development uncertainty. They do not establish full-detector superiority or untouched confirmation.
