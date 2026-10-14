"""Create a three-page supplement from verified matched comparison results."""
import csv,json
from html import escape
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer,PageBreak

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/cannier-matched-v0.4';PDF=ROOT/'output/pdf/CANNIER_Matched_Comparison_Addendum.pdf'

def read(path):
    with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))

def main():
    validation=json.loads((OUT/'validation.json').read_text());result=json.loads((OUT/'conclusion.json').read_text());data=json.loads((ROOT/'dataset/cannier-matched-v0.4/manifest.json').read_text())
    if validation['status']!='passed':raise ValueError('Validated comparison required')
    comparisons=read(OUT/'paired_comparisons.csv');original=read(OUT/'authors_released_predictions_summary.csv');styles=getSampleStyleSheet()
    navy=colors.HexColor('#17324D');teal=colors.HexColor('#087F8C');light=colors.HexColor('#EEF4F7')
    styles.add(ParagraphStyle(name='TitleFX',fontName='Helvetica-Bold',fontSize=22,leading=26,textColor=navy,spaceAfter=12))
    styles.add(ParagraphStyle(name='HeadingFX',fontName='Helvetica-Bold',fontSize=12,leading=15,textColor=teal,spaceBefore=11,spaceAfter=6))
    styles.add(ParagraphStyle(name='BodyFX',fontSize=10,leading=14,spaceAfter=8))
    styles.add(ParagraphStyle(name='SmallFX',fontSize=8,leading=10.5,spaceAfter=5))
    story=[]
    def p(s,style='BodyFX'):story.append(Paragraph(s,styles[style]))
    def h(s):p(s,'HeadingFX')
    def table(rows,widths):
        cells=[[Paragraph(('<font color="#ffffff"><b>'+escape(str(v))+'</b></font>') if i==0 else escape(str(v)),styles['SmallFX']) for v in row] for i,row in enumerate(rows)]
        t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT');t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,light]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.append(t);story.append(Spacer(1,6))
    p('CANNIER matched comparison','TitleFX');p('Supplement to the FlakeXplain study - 14 October 2026')
    p('We recovered the authors\' genuine feature measurements and test identities, then compared their 18-feature classifier input with the same input plus 66 static context features. The two representations share cases, labels, model settings and project-held-out folds.')
    p(f"Matched cohort: <b>{data['cases']:,} cases across 30 projects</b>; {data['nod']} author-labelled NOD cases and {data['victim']} author-labelled victims. Source exclusions: {data['released_cases']-data['cases']:,} of {data['released_cases']:,} released cases.")
    h('Primary: natural class imbalance')
    for balance in ('natural','author_smote_sensitivity'):
        if balance!='natural':h('Secondary: author-SMOTE sensitivity')
        rows=[['Task','Baseline AP','Context AP','Baseline MCC','Context MCC']]
        for r in comparisons:
            if r['balance']==balance:rows.append([r['task'],f"{float(r['baseline_ap']):.4f}",f"{float(r['context_ap']):.4f}",f"{float(r['baseline_mcc']):.4f}",f"{float(r['context_mcc']):.4f}"])
        table(rows,[155,85,85,85,85])
    p('MCC uses the fixed 0.5 threshold and retains its sign. SMOTE is confined to training partitions and is not used in the primary experiment. Both task results, including regressions, are reported. Inner-OOF MCC-selected thresholds appear separately in the full tables.','SmallFX')
    h('Primary context-minus-baseline uncertainty')
    rows=[['Task','95% AP-difference interval','95% MCC-difference interval']]
    for r in comparisons:
        if r['balance']=='natural':
            ap='undefined' if not r['ap_ci_lower'] else f"[{float(r['ap_ci_lower']):+.4f}, {float(r['ap_ci_upper']):+.4f}]"
            mcc='undefined' if not r['mcc_ci_lower'] else f"[{float(r['mcc_ci_lower']):+.4f}, {float(r['mcc_ci_upper']):+.4f}]"
            rows.append([r['task'],ap,mcc])
    table(rows,[155,170,170]);p('500 paired project-resampling replicates of fixed OOF scores. These intervals omit refitting and prior feature-development uncertainty.','SmallFX')
    h('What the result establishes')
    p(escape(result['conclusion']))
    story.append(PageBreak())
    p('Reference scores and scope','TitleFX')
    h('CANNIER AP recovered from released predictions')
    rows=[['Original task','Derived mean AP','Mean MCC']]
    for r in original:rows.append([r['task'],f"{float(r['derived_ap_mean']):.4f}",f"{float(r['signed_mcc_mean']):.4f}"])
    table(rows,[265,115,115]);p('AP values above were newly calculated from the authors\' 30 saved prediction repeats. The paper reports MCC. Their case-level stratified ten-fold setup, SMOTE, complete original cohort and random single-measurement selection differ from our matched project-fold experiment; these are reference scores, not directly comparable superiority targets.')
    h('Controls and verification')
    p('Every released item row and all 30 feature measurements were aligned with the read-only SQLite identities. Context came from exact pinned source revisions. Generated or unresolved tests were excluded from both representations, with original labels and reasons retained. No upstream source code or pickle payload was executed.')
    p(f"{validation['checks']:,} verification checks passed, including replay of all 40 outer models, label joins, feature allowlists, project separation, sampling counts and training-only threshold selection. The test suite ran 89 tests: 88 passed and one Linux-specific test was skipped.")
    h('Secondary: top 10% ranked within each project')
    ranking=read(OUT/'ranking_budget_uncertainty.csv');rows=[['Task / natural imbalance','Baseline found','Context found','Recall gain']]
    for r in ranking:
        if r['balance']=='natural':rows.append([r['task'],r['baseline_found']+'/'+r['positives'],r['context_found']+'/'+r['positives'],f"{100*float(r['recall_difference']):+.2f} pp"])
    table(rows,[210,95,95,95])
    p('For victims, recall at this budget increased from 11.79% to 17.68% (+5.89 percentage points). The conditional project-bootstrap interval for the difference is [+0.25, +15.75] pp. The NOD interval includes zero. This is an exploratory secondary prioritization signal; multiple metrics were examined and prior development/refitting uncertainty is omitted. It does not overturn the mixed primary results.')
    story.append(PageBreak())
    p('What we can claim','TitleFX')
    h('Interpretation boundaries')
    p('The models use the published best families and tree counts: 100-tree Extra Trees for NOD-vs-rest and 75-tree Extra Trees for victim-vs-rest. We use scikit-learn 1.7.2 rather than 1.0.2, five project-grouped folds rather than ten case folds, and the first stored measurement rather than a randomly selected measurement.')
    p('These projects and the source/context design influenced earlier development. This is a retrospective controlled ablation, not untouched positive confirmation. The earlier three-project confirmation remains zero-positive. Human fixture review and near-clone checks remain incomplete.')
    p('Author code takes absolute MCC; we use signed MCC. Their feature display names reverse External Modules and Assertions relative to the stored numeric columns; we preserve the numbers and use SQLite column names. Neither difference is hidden.')
    p('We did not rerun the complete CANNIER hybrid detector or measure matched execution cost. Offline classifier results cannot establish faster flaky-test detection or full-system superiority.')
    h('Next research decision')
    p('The evidence does not support a broad classifier-improvement claim. A narrower follow-up can test context-assisted prioritization at a prospectively fixed per-project budget, using independent positive projects and measured rerun yield. Human context review and a controlled confirmation must precede a stronger paper claim.')
    p('At the primary fixed 0.5 threshold, the natural-imbalance context models flagged no cases. Their MCC of zero is not successful detection. Validation-selected thresholds and the SMOTE sensitivity show different trade-offs, all retained in the full tables.')
    h('Files and references')
    p('Full report: reports/cannier-matched-v0.4/MATCHED_COMPARISON_REPORT.md<br/>Ranking audit: RANKING_DIAGNOSTIC.md<br/>Paired tables: paired_comparisons.csv; project details: metrics_by_project.csv<br/>Data component: dataset/cannier-matched-v0.4/','SmallFX')
    p('Paper: doi:10.1007/s10664-023-10307-w<br/>Authors release: github.com/flake-it/cannier-experiment<br/>Pinned release revision: b96d6ed02e98d514eb6a92ca264a082234cb9728','SmallFX')
    def footer(canvas,doc):
        canvas.setStrokeColor(teal);canvas.line(50,42,545,42);canvas.setFillColor(navy);canvas.setFont('Helvetica',8);canvas.drawString(50,29,'FlakeXplain | matched classifier comparison');canvas.drawRightString(545,29,str(doc.page))
    PDF.parent.mkdir(parents=True,exist_ok=True);SimpleDocTemplate(str(PDF),pagesize=A4,leftMargin=50,rightMargin=50,topMargin=42,bottomMargin=55,title='CANNIER Matched Comparison Addendum',author='FlakeXplain Team').build(story,onFirstPage=footer,onLaterPages=footer);print(PDF)

if __name__=='__main__':main()
