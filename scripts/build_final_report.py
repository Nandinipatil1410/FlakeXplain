"""Render a concise four-page guide report from verified measured results."""
import csv,json
from html import escape
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/final-confirmation-v0.3'
PDF=ROOT/'output/pdf/FlakeXplain_Final_Study_Report.pdf'
NAVY=colors.HexColor('#17324D');TEAL=colors.HexColor('#087F8C');LIGHT=colors.HexColor('#EEF4F7')

def read(path):
    with path.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))

def main():
    validation=json.loads((OUT/'validation.json').read_text())
    if validation['status']!='passed':raise ValueError('Verified evaluation required')
    deployment=json.loads((OUT/'deployment_model_card.json').read_text());metrics=read(OUT/'external_metrics.csv')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleFX',fontName='Helvetica-Bold',fontSize=24,leading=28,textColor=NAVY,spaceAfter=12))
    styles.add(ParagraphStyle(name='HeadingFX',fontName='Helvetica-Bold',fontSize=13,leading=16,textColor=TEAL,spaceBefore=11,spaceAfter=7))
    styles.add(ParagraphStyle(name='BodyFX',fontName='Helvetica',fontSize=10,leading=14,spaceAfter=8))
    styles.add(ParagraphStyle(name='SmallFX',fontName='Helvetica',fontSize=8,leading=10,spaceAfter=5))
    styles.add(ParagraphStyle(name='CellFX',fontName='Helvetica',fontSize=8.5,leading=10.5))
    story=[]
    def p(text,style='BodyFX'):story.append(Paragraph(text,styles[style]))
    def h(text):p(text,'HeadingFX')
    def table(rows,widths,small=False):
        data=[[Paragraph(('<font color="#ffffff"><b>'+escape(str(v))+'</b></font>') if i==0 else escape(str(v)),styles['SmallFX' if small else 'CellFX']) for v in row] for i,row in enumerate(rows)]
        t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('TEXTCOLOR',(0,0),(-1,0),colors.white),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,LIGHT]),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),3 if small else 6),('BOTTOMPADDING',(0,0),(-1,-1),2 if small else 6),('LINEBELOW',(0,0),(-1,0),.8,TEAL)]))
        story.append(t);story.append(Spacer(1,7))
    p('FlakeXplain','TitleFX');p('Completed study and independent confirmation - 14 October 2026')
    h('The result to present')
    p('We completed an audited dataset, static context extraction, project-separated model experiments, a prospective three-project confirmation, source-linked explanations and a separate all-data deployment fit.')
    p('<b>Context showed a development ranking signal and fewer observed external false alarms. Independent flaky-test recall and superiority to CANNIER remain unestablished.</b>')
    table([['Stage','Cases / projects','Observed positives'],['Development corpus','96,118 / 35','693 (0.721%)'],['Independent confirmation','2,610 / 3','0'],['Deployment fit after evaluation','98,728 / 38','693']], [195,170,130])
    h('Development evidence')
    p('In the bounded nested development study, revised-context Extra Trees reached average precision 0.0552 versus 0.0071 for the revised core. The project-resampling interval for the difference was [-0.0065, 0.0855], including zero. These inspected folds are development evidence.')
    p('At the top 10% ranked separately within each development project, context/core models recovered 121/693 (17.46%) and 103/693 (14.86%) observed positives. No execution-time saving was measured.')
    h('Prospective confirmation: false-alarm results')
    table([['Frozen model','Flags / 2,610','Per 1,000 negatives'],['Extra Trees: scope-aware core','111','42.529'],['Extra Trees: core + context','3','1.149'],['Random Forest: core reference','24','9.195'],['Random Forest: context reference','2','0.766'],['Constant-negative reference','0','0.000']],[265,105,125])
    p('All confirmation cases passed 25 rounds. Recall and average precision are undefined. Models use separately frozen development-selected thresholds; different selected class weights and thresholds prevent a pure causal attribution to context. A constant-negative classifier also makes zero false alarms here.','SmallFX')
    story.append(PageBreak())
    p('The evaluated corpus','TitleFX');p('Model-eligible cases. Negatives mean not observed flaky after the recorded finite run budget.','SmallFX')
    data=[['Project','Cases','Observed flaky','Prevalence']]
    original=read(ROOT/'dataset/v0.1/project_summary.csv')
    for r in sorted(original,key=lambda r:r['project']):
        n=int(r['model_cases']);pos=int(r['observed_flaky']);data.append([r['project'],f'{n:,}',str(pos),f'{100*pos/n:.2f}%'])
    for r in read(OUT/'guide_project_table.csv'):data.append([r['project']+' (confirmation)',f"{int(r['binary_cases']):,}",r['observed_flaky'],'0.00%'])
    data.append(['Total eligible / 38 projects','98,728','693','0.702%'])
    table(data,[230,85,100,80],small=True)
    p('Development source coverage: 96,118 of 99,861 candidate cases (96.25%); excluded 3,743 cases, including 22 observed positives. Original evidence remains retained. Confirmation collected 2,621 identities: 2,610 binary all-pass cases and 11 attrs skip-only identities. No confirmation binary source exclusions.','SmallFX')
    story.append(PageBreak())
    p('Method and fair comparisons','TitleFX')
    h('What was frozen before confirmation')
    p('Werkzeug, attrs and Tenacity were selected before inspecting their new outcomes. Source commits, the 30/96 feature representations, model candidate grids, project folds, selection rule, thresholds and metrics were recorded. Four final models were fitted only on the 35 development projects before opening confirmation artifacts.')
    p('Each new project passed a full baseline gate, followed by 12 original, 12 random and one reverse round on Ubuntu 24.04 / Python 3.11.9. All jobs completed within about 4.5 minutes, inside the four-hour cap. Zero-positive projects were retained.')
    h('Static features and leakage controls')
    p('The 30-feature core includes two scope-aware read indicators. The 96-feature extension adds bounded fixture, helper, lifecycle and class-state counts. Runtime outcomes, repeated-run counts, identities and seeds are label/provenance evidence only. No synthetic oversampling or artificial duplication was used.')
    p('The external feature adapter exactly reproduced 7,680 numeric values across 80 development contexts. Frozen external model predictions and metrics passed 109 checks. The existing suite ran 85 tests: 84 passed and one Linux-specific test skipped.')
    h('Published work: compatibility matters')
    p('The 2024 IEEE Access cross-project artifact uses Java metrics. Its transfer experiment trains with labels from 25%, 50% or 75% of the target project and evaluates a separate target subset. Our new-project task has no target training labels. Direct score comparisons would be invalid.')
    p('Our 100-tree Random Forest references use our Python core/context features and the same external cases. They omit sampling, PCA and target-label transfer. They are model-family adaptations, not faithful paper reproductions. No complete CANNIER hybrid baseline or matched rerun-efficiency experiment was reproduced.')
    h('Explanations and uncertainty')
    p('Nine source-linked examples decompose the Extra Trees score into an average tree-root value plus contributions along observed decision paths. Every explanation reconstructs the score. These are tree-path attributions, not SHAP or causal diagnoses. Global impurity importances have known attribution biases.')
    p('Random rounds change both order and runtime seeds; order-dependency subtypes remain provisional. Plugin-aware fixture lookup, dynamic dispatch, near-clone checks and human cause validation remain incomplete. Only three external projects were sampled, with no observed positives.')
    story.append(PageBreak())
    p('Artifacts and guide decision','TitleFX')
    h('A usable all-data deployment model')
    p(f"After independent evaluation, we fitted a separate context Extra Trees model on {deployment['training_cases']:,} eligible cases across {len(deployment['training_projects'])} projects, with {deployment['training_positives']} observed positives. It retains the development-selected configuration and threshold {deployment['threshold']:.6f}.")
    p('This deployment model does not own the earlier confirmation score. It has seen those projects during fitting and has no new unbiased test result. Its serialization was replayed on 100 cases. Risk scores are uncalibrated estimates, not confirmed flaky labels.')
    h('What is available to review')
    for text in ['FINAL_STUDY_REPORT.md: measured findings, limitations and reproduction notes.', 'GUIDE_FINAL_BRIEF.md: a concise meeting brief.', 'external_metrics.csv / external_predictions.csv.gz: frozen model results, including undefined-metric flags.', 'protocol.json / model_manifest.json / artifact_provenance.json: prospective design, model hashes and raw-evidence references.', 'source_linked_explanations.json: nine checked attributions with source hashes.', 'MANUSCRIPT_DRAFT.md: an empirical-study draft, explicitly marked not submission-ready.']:
        p(text,'SmallFX')
    h('The decision to discuss with the guide')
    p('The completed work supports an evidence-backed empirical study of bounded Python test context. A stronger detection-improvement paper needs independent positive confirmation, a compatible reproduced baseline and human validation. A deployment fit or high accuracy on a zero-positive sample cannot supply that evidence.')
    p('Recommended follow-up: prospectively define independent positive-project collection; validate extraction and cause annotations with human reviewers; then test matched recall or matched inspection budgets. Keep this confirmation unchanged. No publication acceptance guarantee is justified.')
    h('Primary references')
    p('CANNIER (2023): doi:10.1007/s10664-023-10307-w<br/>Cross-project flaky-test prediction (2024): doi:10.1109/ACCESS.2024.3458184<br/>Static Test Flakiness Prediction (2022): doi:10.1007/s10664-022-10227-1','SmallFX')
    p('Workflow: github.com/Nandinipatil1410/FlakeXplain/actions/runs/38429430361<br/>Authors artifact inspected at commit 8fe244f03122706763484dea7b4d98b09fefb923.','SmallFX')
    p('Reporting clarification: the preserved evaluation metadata calls attrs\' 1,412 retained identities "candidate_binary_cases"; 11 are skip-only. The corrected binary total is 1,401. Scores and metrics are unaffected; see metadata_clarification.json.','SmallFX')
    def footer(canvas,doc):
        canvas.setStrokeColor(TEAL);canvas.line(50,42,545,42);canvas.setFont('Helvetica',8);canvas.setFillColor(NAVY);canvas.drawString(50,29,'FlakeXplain | verified study, not a publication guarantee');canvas.drawRightString(545,29,str(doc.page))
    PDF.parent.mkdir(parents=True,exist_ok=True)
    SimpleDocTemplate(str(PDF),pagesize=A4,rightMargin=50,leftMargin=50,topMargin=42,bottomMargin=55,title='FlakeXplain: Final Study and Independent Confirmation',author='FlakeXplain Team').build(story,onFirstPage=footer,onLaterPages=footer)
    print(str(PDF))

if __name__=='__main__':main()
