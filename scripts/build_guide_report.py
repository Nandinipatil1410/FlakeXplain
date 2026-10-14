"""Create a four-page guide report and reproducible development summaries."""
import csv
import hashlib
from html import escape
import json
from pathlib import Path
from statistics import mean
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from reportlab.graphics.shapes import Drawing,Rect,String,Line

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/development-v0.2'
PDF=ROOT/'output/pdf/FlakeXplain_Guide_Progress_Report.pdf'
NAMES={
    'extra_trees_v1_body':'Tuned ET: body v1', 'extra_trees_v1_context':'Tuned ET: context v1',
    'extra_trees_v2_body':'Tuned ET: core v2*', 'extra_trees_v2_context':'Tuned ET: context v2',
    'logistic_v1_body':'LR: body v1', 'logistic_v1_context':'LR: context v1',
    'logistic_v2_body':'LR: core v2*', 'logistic_v2_context':'LR: context v2',
    'text_logistic_text_body':'Text LR: body', 'text_logistic_text_context':'Text LR: context'}
NAVY=colors.HexColor('#16324F'); TEAL=colors.HexColor('#087F8C'); LIGHT=colors.HexColor('#EEF4F7'); AMBER=colors.HexColor('#8C5B18')

def read(path):
    with path.open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    result=json.loads((OUT/'results.json').read_text()); valid=json.loads((OUT/'validation.json').read_text())
    if valid['status']!='passed':
        raise ValueError('Validate development results before authoring the guide report')
    original=json.loads((ROOT/'reports/pilot-v0.1/results.json').read_text())
    dataset=json.loads((ROOT/'dataset/v0.1/manifest.json').read_text())
    static=json.loads((ROOT/'reports/dataset-preparation/statistics.json').read_text())
    audit=json.loads((OUT/'manual_error_review.json').read_text()); collision=read(OUT/'feature_collision_audit.csv')
    pooled={r['model']:r for r in result['pooled'] if r['threshold_mode']=='inner_f1'}
    old={r['model']:r for r in original['pooled'] if r['threshold_mode']=='inner_f1'}
    best=max(pooled.values(),key=lambda r:r['average_precision'])
    core=pooled['extra_trees_v2_body']; context=pooled['extra_trees_v2_context']
    ci=result['primary_paired_project_bootstrap']['percentile_95_interval']
    by_project=[r for r in read(OUT/'metrics_by_project.csv') if r['threshold_mode']=='inner_f1']
    macro=[]
    for name in NAMES:
        records=[r for r in by_project if r['model']==name]
        positive=[r for r in records if int(r['positives'])>0]
        macro.append(dict(model=name,positive_projects=len(positive),macro_positive_project_ap=mean(float(r['average_precision']) for r in positive),
                          macro_f1_all_projects=mean(float(r['f1']) for r in records),
                          macro_fp_per_1000_negative=mean(float(r['false_positives_per_1000_negative']) for r in records),
                          per_project_top10_cases=sum(int(r['top_10_percent_cases']) for r in records),
                          per_project_top10_captured=sum(round(float(r['recall_at_top_10_percent'] or 0)*int(r['positives'])) for r in records)))
    with (OUT/'metrics_project_macro.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(macro[0])); w.writeheader(); w.writerows(macro)
    pcore={r['project']:r for r in by_project if r['model']=='extra_trees_v2_body' and int(r['positives'])>0}
    pcontext={r['project']:r for r in by_project if r['model']=='extra_trees_v2_context' and int(r['positives'])>0}
    deltas=[dict(project=p,core_ap=float(pcore[p]['average_precision']),context_ap=float(pcontext[p]['average_precision']),
                 context_minus_core_ap=float(pcontext[p]['average_precision'])-float(pcore[p]['average_precision'])) for p in sorted(pcore)]
    with (OUT/'primary_project_deltas.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(deltas[0])); w.writeheader(); w.writerows(deltas)
    improvement=best['average_precision']-old['extra_trees_body']['average_precision']
    project_budget={r['model']:r for r in macro}
    original_projects=[r for r in read(ROOT/'reports/pilot-v0.1/metrics_by_project.csv') if r['model']=='extra_trees_body' and r['threshold_mode']=='inner_f1']
    original_project_capture=sum(round(float(r['recall_at_top_10_percent'] or 0)*int(r['positives'])) for r in original_projects)
    core_capture=project_budget['extra_trees_v2_body']['per_project_top10_captured']
    context_capture=project_budget['extra_trees_v2_context']['per_project_top10_captured']
    budget_cases=project_budget['extra_trees_v2_context']['per_project_top10_cases']
    summary=dict(cases=dataset['model_cases'],positives=dataset['observed_flaky'],negative_cases=dataset['model_cases']-dataset['observed_flaky'],
                 projects=dataset['projects'],best_observed_development_model=best['model'],best_development_ap=best['average_precision'],
                 original_body_ap=old['extra_trees_body']['average_precision'],best_minus_original_body_ap=improvement,
                 primary_v2_context_minus_core_ap=context['average_precision']-core['average_precision'],primary_conditional_project_interval=ci,
                 primary_project_ap_improved=sum(r['context_minus_core_ap']>1e-12 for r in deltas),
                 primary_project_ap_regressed=sum(r['context_minus_core_ap'] < -1e-12 for r in deltas),
                 primary_positive_projects=len(deltas),error_sample_cases=100,source_excerpt_reviews=audit['reviewed_cases'],
                 validation_checks=len(valid['checks']),models_replayed=valid['models_replayed'],convergence_warnings=result['convergence_warnings'],
                 per_project_top10_budget_cases=budget_cases,original_body_per_project_top10_captured=original_project_capture,
                 revised_core_per_project_top10_captured=core_capture,revised_context_per_project_top10_captured=context_capture,
                 status='Development evidence after inspected pilot; no independent final or CANNIER-superiority claim')
    (OUT/'guide_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    fold=read(OUT/'metrics_by_fold.csv')
    rows=[('Original ET: body',old['extra_trees_body']),('Original ET: context',old['extra_trees_context'])]+[(NAMES[name],pooled[name]) for name in NAMES]
    table_header=['Model','AP (0-1)','Precision','Recall','F1','MCC','FP / 1k']
    data=[table_header]
    for label,r in rows:
        data.append([label,f"{r['average_precision']:.5f}",f"{100*r['precision']:.2f}%",f"{100*r['recall']:.2f}%",f"{100*r['f1']:.2f}%",f"{r['mcc']:.4f}",f"{r['false_positives_per_1000_negative']:.1f}"])
    note='V2 core* includes six new body-operation counts and two scoped-read indicators in addition to the original 22 body counts. Thus v2 is an incremental-context comparison, not a pure body/context ablation. The v1 comparisons retain the strict 22-versus-55 distinction.'
    conclusion=(f"The highest observed development AP is {best['average_precision']:.5f} ({NAMES[best['model']]}), versus {old['extra_trees_body']['average_precision']:.5f} for the original body-only pilot. "
                f"The predeclared revised-context comparison changes pooled AP by {context['average_precision']-core['average_precision']:+.5f}, with a conditional project-bootstrap interval [{ci[0]:+.5f}, {ci[1]:+.5f}]. "
                'These are development findings on already-inspected folds, not proof of improvement over a published base paper.')
    detailed=['# FlakeXplain: bounded development-cycle results','',conclusion,'',
              'Prepared 13 October 2026 for the guide discussion on 14 October 2026.','',
              '## Scope and method','',
              'Original dataset v0.1, labels and splits are frozen. All 96,118 cases and 35 projects remain; no artificial balancing, subject reruns or label changes were performed. Ten model variants were assessed using five outer development folds and four inner project folds. Four Extra Trees configurations vary depth/leaf size/class weighting; two Logistic Regression C values are compared. Candidates maximize inner OOF average precision; thresholds maximize inner OOF F1. Numeric LR uses training-only log1p/scaling. Text LR uses masked AST tokens and stateless hashing with training-only IDF. Every selected inner OOF score is retained.',
              '',note,'','## Results','', '| '+' | '.join(table_header)+' |','|'+'|'.join(['---']+['---:']*6)+'|']
    detailed += ['| '+' | '.join(row)+' |' for row in data[1:]]
    detailed += ['', 'AP is average precision, not accuracy or trapezoidal PR area. Precision/recall/F1 use thresholds chosen inside the training partitions. Best model is identified after development-result inspection and is descriptive, not a confirmed deployment selection. Pooled scores from different models/folds need not be calibrated; retain fold/project/macro results.',
                 '', '## Primary paired comparison by fold','', '| Fold | Revised core AP | Revised context AP |','|---|---:|---:|']
    fold_table=[]
    for i in range(5):
        a=next(r for r in fold if r['model']=='extra_trees_v2_body' and r['threshold_mode']=='inner_f1' and int(r['outer_fold'])==i)
        b=next(r for r in fold if r['model']=='extra_trees_v2_context' and r['threshold_mode']=='inner_f1' and int(r['outer_fold'])==i)
        fold_table.append([str(i),f"{float(a['average_precision']):.5f}",f"{float(b['average_precision']):.5f}"])
        detailed.append('| '+' | '.join(fold_table[-1])+' |')
    detailed += ['',f"Among {len(deltas)} positive projects, revised context AP improved in {summary['primary_project_ap_improved']} and regressed in {summary['primary_project_ap_regressed']}. See metrics_project_macro.csv and primary_project_deltas.csv. The bootstrap resamples projects without refitting; it excludes feature-development/model-selection uncertainty and is not definitive significance.",
                 '', '## Per-project ranking budget','',
                 f"Taking the top 10% separately inside each project selects {budget_cases:,} cases in total (rounding up within projects). The original body pilot captures {original_project_capture}/693 positives ({100*original_project_capture/693:.2f}%), the revised ET core captures {core_capture}/693 ({100*core_capture/693:.2f}%), and revised ET context captures {context_capture}/693 ({100*context_capture/693:.2f}%). This matched within-project ranking diagnostic is more relevant to a new project than pooling scores from differently calibrated fold models.",
                 '',f"The revised context model's pooled top-10% recall is {100*context['recall_at_top_10_percent']:.2f}%, which is substantially higher than its per-project-budget recall. Do not present the pooled figure as the expected recall at a 10% budget inside a new project, or as measured rerun time savings. This is a retrospective label-capture analysis, not a new rerunning experiment.",
                 '', '## Error and representation audit','',
                 'The declared sample contains 50 context-model false positives and 50 false negatives across 35 projects, with distinct source families per error type. Twelve source excerpts across 12 projects were inspected by Codex; no human causal validation or label changes are claimed. All 100 sample rows remain a declared review queue, with completed excerpt reviews stored separately.',
                 '', '| Representation | Features | Positive cases sharing vectors with negatives |','|---|---:|---:|']
    for r in collision:
        detailed.append(f"| {r['representation']} | {r['features']} | {r['positive_cases_in_mixed_vectors']} / 693 ({100*float(r['positive_fraction_in_mixed_vectors']):.2f}%) |")
    detailed += ['', 'Collision counts are full-corpus descriptive diagnostics; labels were used only to measure collisions, never to construct predictors or fit an oracle. Lower collision counts mean more distinguishable source representations, not proven predictive or causal improvement.',
                 '', 'Concrete findings: assertion-like unittest/fixture calls were missed by ast.Assert counts; decorator-generated arguments can be mistaken for candidate fixtures; time-related API names can describe deterministic operations; shared module state, parameter-specific behavior and stringified subprocess programs remain partial. The revision separates fixture/helper/lifecycle means and adds operation counts and potential class state. Plugin/override graph expansion was not implemented in this bounded cycle.',
                 '', '## Verification','',
                 f"{len(valid['checks'])} checks passed; {valid['models_replayed']} saved models reproduced outer scores. Independent sklearn metrics, inner-AP selection, thresholds from saved inner predictions, training-only scalers/IDF and project membership were verified. Candidate-fit convergence warnings: {result['convergence_warnings']}. The repository unit suite passed 84 tests with one Linux-only test skipped (85 discovered). Exact models and inner score arrays are retained in ignored local-evidence/development-models.",
                 '', '## Research positioning and next decisions','',
                 'Recommended framing: cross-project static prediction of observed Python test instability. Use the 2024 cross-project study for the research question and the 2022 static study as a methodological baseline family. Keep CANNIER as a Python/hybrid reference and source of subject overlap. These are adaptations to investigate, not reproduced methods or beaten published scores.',
                 '', 'The 2024 study evaluates transfer/filtering approaches with source/target adaptation conditions. Audit its released code and target-data assumptions before attempting a zero-target-label comparison. The 2022 study uses Java metrics, requiring an explicit Python mapping. CANNIER has runtime features, different targets, budgets and a hybrid objective. None of their reported scores is directly comparable with our development scores.',
                 '', 'Proposed next steps: agree the static cross-project scope with the guide; complete a compatible released-baseline adaptation and bounded fixture/parameter audit; predeclare the final model/evaluation protocol; obtain independent evidence if an untouched confirmation claim is required. Current outer folds have influenced development. All-pass-after-N labels remain uncertain; random-round order/seed effects are confounded; current source/near-duplicate/fixture limitations remain disclosed.',
                 '', '## Sources','',
                 '- [Cross-project study, IEEE Access 2024](https://doi.org/10.1109/ACCESS.2024.3458184) and [authors\' artifact](https://github.com/alfcan/crossproject-flaky-test-prediction).',
                 '- [Static Test Flakiness Prediction, EMSE 2022](https://doi.org/10.1007/s10664-022-10227-1).',
                 '- [CANNIER, EMSE 2023](https://doi.org/10.1007/s10664-023-10307-w).','']
    (OUT/'DEVELOPMENT_RESULTS_REPORT.md').write_text('\n'.join(detailed),encoding='utf-8')
    brief=['# Talking points for the guide','',
           '- We have an audited, source-linked corpus: 35 projects, 96,118 model-ready cases, 693 observed positives. Labels preserve their finite-run uncertainty.',
           '- The original static-context pilot was weak on unseen projects; this result is retained as a negative reference.',
           '- We completed a bounded follow-up: targeted static revisions, regularized numeric/text baselines, and inner-project configuration selection.',
           f"- Highest observed development AP: {best['average_precision']:.5f} ({NAMES[best['model']]}). Original body pilot AP: {old['extra_trees_body']['average_precision']:.5f}. This is not a published-baseline victory.",
           f"- Revised context minus revised core AP: {context['average_precision']-core['average_precision']:+.5f}; conditional interval [{ci[0]:+.5f}, {ci[1]:+.5f}].",
           f"- At a top-10% budget inside each project ({budget_cases:,} cases total), captured positives are {original_project_capture} original body / {core_capture} revised core / {context_capture} revised context, out of 693. Do not substitute pooled 44%-style recall for this project-level result.",
           '- The error study covers 100 declared cases; 12 source excerpts were inspected. Original body-feature collisions affect 379 positive cases; revised full-context collisions affect 123.',
           '- Proposed paper direction: fixture-aware static prediction across Python projects, framed against cross-project/static literature; retain CANNIER as related Python/hybrid work.',
           '- Decisions requested in the meeting: agree the task/base-paper framing, choose a compatible comparison, and agree the final independent-evaluation evidence/time budget.',
           '', 'Bring the four-page PDF first; use DEVELOPMENT_RESULTS_REPORT.md and the CSV/JSON evidence for questions. Final training and submission readiness are not claimed.','']
    (OUT/'GUIDE_BRIEF.md').write_text('\n'.join(brief),encoding='utf-8')
    # The PDF is authored only after the required artifact-start marker is run.
    PDF.parent.mkdir(parents=True,exist_ok=True)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleGuide',fontName='Helvetica-Bold',fontSize=24,leading=28,textColor=NAVY,spaceAfter=12))
    styles.add(ParagraphStyle(name='GuideH',fontName='Helvetica-Bold',fontSize=13,leading=17,textColor=NAVY,spaceBefore=12,spaceAfter=7))
    styles.add(ParagraphStyle(name='GuideBody',fontName='Helvetica',fontSize=9.2,leading=13.1,spaceAfter=8))
    styles.add(ParagraphStyle(name='GuideSmall',fontName='Helvetica',fontSize=8,leading=10.5,spaceAfter=6,textColor=colors.HexColor('#435566')))
    styles.add(ParagraphStyle(name='GuideCell',fontName='Helvetica',fontSize=8,leading=10))
    def p(text,style='GuideBody'):
        return Paragraph(text,styles[style])
    def h(text):
        return p(text,'GuideH')
    def table(rows,widths):
        header_style=ParagraphStyle(name='HeaderCell',parent=styles['GuideCell'],textColor=colors.white,fontName='Helvetica-Bold')
        cells=[[Paragraph(escape(str(cell)).replace('\n','<br/>'),header_style if i==0 else styles['GuideCell']) for cell in row] for i,row in enumerate(rows)]
        t=Table(cells,colWidths=widths,hAlign='LEFT',repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('TEXTCOLOR',(0,0),(-1,0),colors.white),
                               ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,LIGHT]),('VALIGN',(0,0),(-1,-1),'TOP'),
                               ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
                               ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
                               ('LINEBELOW',(0,0),(-1,0),.7,TEAL)]))
        return t
    story=[p('FlakeXplain','TitleGuide'),p('Evidence, pilot results and research direction','GuideH'),
           p('Prepared 13 October 2026 | Guide discussion: 14 October 2026','GuideSmall'),
           p('<b>Development assessment - not an untouched final evaluation.</b> The original pilot and the follow-up use the same frozen projects and cases. No result below establishes superiority over CANNIER.'),
           table([['Projects','Model-ready cases','Observed positives','Positive prevalence'],['35','96,118','693','0.7210%']],[108,147,133,115]),
           h('What has been completed'),
           p('An evidence audit and exact-source joins; a frozen 22/55-feature pilot; a 100-case error-audit sample with 12 inspected source excerpts; a revised 30/96-feature representation; ten follow-up model variants with project-separated inner selection; saved predictions, models and verification records.'),
           h('Measured outcome'),p(escape(conclusion)),h('Average precision comparison')]
    chart_rows=[('Original body',old['extra_trees_body']['average_precision']),('Original context',old['extra_trees_context']['average_precision']),
                ('Revised ET core',core['average_precision']),('Revised ET context',context['average_precision'])]
    if best['model'] not in ('extra_trees_v2_body','extra_trees_v2_context'):
        chart_rows.append(('Highest development AP',best['average_precision']))
    drawing=Drawing(503,170); max_value=max(v for _,v in chart_rows)*1.15
    for i,(label,value) in enumerate(chart_rows):
        yy=140-i*28; drawing.add(String(0,yy+4,label,fontName='Helvetica',fontSize=8.5,fillColor=NAVY))
        drawing.add(Rect(150,yy,290*value/max_value,15,fillColor=TEAL if i>=2 else NAVY,strokeColor=None))
        drawing.add(String(450,yy+4,f'{value:.5f}',fontName='Helvetica-Bold',fontSize=8.5,fillColor=NAVY))
    drawing.add(Line(150,16,440,16,strokeColor=colors.HexColor('#A6B6C3')))
    drawing.add(String(150,2,'AP (0-1); point estimates, not accuracy',fontName='Helvetica',fontSize=8,fillColor=NAVY))
    story += [drawing,p(f"At a top-10% budget separately within each project, captured positives are <b>{original_project_capture} original body / {core_capture} revised core / {context_capture} revised context</b>, out of 693 ({budget_cases:,} selected cases). This is retrospective label capture, not measured rerun savings.",'GuideSmall'),
              p('The highest AP is identified after development inspection. Pooled scores mix fold-model calibration. Conditional paired uncertainty is reported on page 2.','GuideSmall'),PageBreak(),
              p('Controlled model comparison','TitleGuide'),
              p('All rows use 96,118 cases. P/R/F1 use thresholds selected only from inner training-fold predictions. AP is threshold-independent.','GuideSmall'),
              table(data,[163,58,55,55,55,55,62]),Spacer(1,8),p(escape(note),'GuideSmall'),
              h('Revised Extra Trees comparison by outer development fold'),
              table([['Fold','Core v2 AP','Full context v2 AP']]+fold_table,[70,210,223]),
              p(f"Primary context-minus-core AP: <b>{context['average_precision']-core['average_precision']:+.5f}</b>. Conditional 95% project-bootstrap interval: [{ci[0]:+.5f}, {ci[1]:+.5f}] (500 resamples; no refitting). Project AP improved in {summary['primary_project_ap_improved']} of 29 positive projects and regressed in {summary['primary_project_ap_regressed']}.",'GuideSmall'),
              PageBreak(),p('What the error audit teaches us','TitleGuide'),
              p('A declared sample of 50 false positives and 50 false negatives spans 35 projects. Twelve source excerpts from 12 projects were checked. These are AI-assisted static observations; no causal annotations or label changes were made.'),
              table([['Example','Observed issue / representation consequence'],
                     ['Airflow\nFalse positive','Mock decorators supply arguments that appear as unresolved fixture candidates. Unittest assertions require call-aware counts.'],
                     ['Dask\nFalse positive','Fixed datetime.date values can trigger a time-API proxy despite deterministic intent. A risk token is not a failure cause.'],
                     ['Filelock\nFalse negative','Process events, timed waits and joins motivate blocking/cleanup features; runtime scheduling remains unobserved.'],
                     ['Freezegun\nFalse negative','Late imports and sys.modules checks expose module-cache state beyond the function body.'],
                     ['Hydra\nFalse negative','Parameterized cases share a body; parameter-specific behavior is not fully represented.'],
                     ['Xonsh\nFalse negative','Shell fixture context reaches the original extraction bound; dynamic behavior remains partial.']],[133,370]),
              h('Exact numeric feature collisions'),
              table([['Representation','Features','Positive cases sharing vectors with negatives']]+
                    [[r['representation'],r['features'],f"{r['positive_cases_in_mixed_vectors']} / 693 ({100*float(r['positive_fraction_in_mixed_vectors']):.1f}%)"] for r in collision],[140,65,298]),
              p('Full-corpus labels are used only for this descriptive audit. Opposite labels with identical vectors cannot be perfectly separated by that representation. Fewer collisions demonstrate richer source information, not proven generalization.'),
              h('Verification'),
              p(f"{len(valid['checks'])} checks passed, with {valid['models_replayed']} selected models replayed. Saved inner predictions reproduce configuration selection and thresholds. Training-only scaler/IDF fits and independent sklearn metrics were verified. The repository suite passed 84 tests; one Linux-only check was skipped. Convergence warnings: {result['convergence_warnings']}.",'GuideSmall'),
              PageBreak(),p('Research direction and decisions','TitleGuide'),
              h('Recommended scope'),p('<b>Fixture-aware static prediction of observed Python test instability across projects.</b> Treat the current work as a reproducible development study. Retain negative results and report project/family sensitivity alongside pooled scores.'),
              table([['Research role','Reference and fit'],
                     ['Primary framing','A Large-Scale Empirical Investigation Into Cross-Project Flaky Test Prediction (IEEE Access, 2024): directly addresses project heterogeneity and adaptation.'],
                     ['Methodological baseline','Static Test Flakiness Prediction: How Far Can We Go? (EMSE, 2022): static metrics, studied in Java; requires a declared Python adaptation.'],
                     ['Python/hybrid reference','CANNIER (EMSE, 2023): runtime features and ML-assisted rerunning with different targets/budgets; not reproduced by this static experiment.']],[133,370]),
              p('The 2024 adaptation settings and target-data assumptions must be audited before comparison. Its published scores cannot be compared directly with ours. A changed base-paper framing does not establish novelty or an experimental win.','GuideSmall'),
              h('Decisions for the guide'),
              p('1. Agree the static cross-project task and primary reference.<br/>2. Select a compatible released-baseline adaptation and a bounded fixture/parameter audit.<br/>3. Freeze the final evaluation plan. Fresh independent evidence is needed for an untouched confirmation claim after these inspected folds.<br/>4. Decide whether the main contribution is predictive improvement, an empirical replication/benchmark, or a validated analysis of representation limits.'),
              h('Claims we can make now'),
              p('Audited empirical corpus; reproducible negative reference and development comparisons; source-linked error examples; measured representation collisions. We cannot yet claim a superior CANNIER detector, confirmed OD causes, a complete fixture resolver, independent final performance or submission readiness.'),
              h('Sources and artifact trail'),
              p('<link href="https://doi.org/10.1109/ACCESS.2024.3458184" color="#087F8C">Cross-project study (2024)</link> | <link href="https://github.com/alfcan/crossproject-flaky-test-prediction" color="#087F8C">Authors\' artifact</link><br/>'
                '<link href="https://doi.org/10.1007/s10664-022-10227-1" color="#087F8C">Static prediction study (2022)</link><br/>'
                '<link href="https://doi.org/10.1007/s10664-023-10307-w" color="#087F8C">CANNIER (2023)</link>','GuideSmall'),
              p('Machine-readable evidence: reports/development-v0.2. Original corpus: dataset/v0.1. Model payloads and transformed source documents are retained locally under ignored local-evidence. See GUIDE_BRIEF.md for meeting talking points.','GuideSmall')]
    def footer(canvas,doc):
        canvas.saveState(); canvas.setStrokeColor(TEAL); canvas.line(46,39,A4[0]-46,39)
        canvas.setFont('Helvetica',8); canvas.setFillColor(NAVY)
        canvas.drawString(46,25,'FlakeXplain | Development evidence | 13 October 2026')
        canvas.drawRightString(A4[0]-46,25,str(doc.page)); canvas.restoreState()
    doc=SimpleDocTemplate(str(PDF),pagesize=A4,leftMargin=46,rightMargin=46,topMargin=42,bottomMargin=54,
                          title='FlakeXplain guide progress report',author='FlakeXplain project team',pageCompression=1)
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    files={p.name:digest(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='review_manifest.json'}
    (OUT/'review_manifest.json').write_text(json.dumps(dict(files=files,pdf_path=str(PDF.relative_to(ROOT)),pdf_sha256=digest(PDF),report_generator_sha256=digest(Path(__file__))),indent=2)+'\n')
    print(json.dumps(dict(pdf=str(PDF),best_development_model=best['model'],best_ap=best['average_precision'],primary_delta=summary['primary_v2_context_minus_core_ap']),indent=2))

if __name__=='__main__':
    main()
