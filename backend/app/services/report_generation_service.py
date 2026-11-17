"""Generate a print-ready PDF from the exact dashboard analysis payload.

No repository is re-cloned or re-analyzed. Repository-derived strings are
escaped, sensitive keys/paths are omitted, and missing optional modules are
reported as unavailable rather than fabricated.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
import re
from datetime import datetime, timezone
from xml.sax.saxutils import escape
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    KeepTogether, HRFlowable, LongTable, Flowable,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

NAVY = colors.HexColor('#142B4A')
BLUE = colors.HexColor('#245B91')
INDIGO = colors.HexColor('#5267A8')
PALE = colors.HexColor('#EAF0F7')
PALE2 = colors.HexColor('#F5F7FA')
INK = colors.HexColor('#263445')
SLATE = colors.HexColor('#65758B')
BORDER = colors.HexColor('#D7DEE8')
FONT_DIR = Path(__file__).resolve().parents[1] / 'assets' / 'fonts'
pdfmetrics.registerFont(TTFont('RepoSans', str(FONT_DIR / 'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('RepoSans-Bold', str(FONT_DIR / 'DejaVuSans-Bold.ttf')))
pdfmetrics.registerFontFamily('RepoSans', normal='RepoSans', bold='RepoSans-Bold', italic='RepoSans', boldItalic='RepoSans-Bold')
for _cid_name in ('HeiseiMin-W3', 'STSong-Light', 'MSung-Light', 'HYSMyeongJo-Medium'):
    pdfmetrics.registerFont(UnicodeCIDFont(_cid_name))


def _font_for_text(value: str) -> str:
    if re.search(r'[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]', value):
        return 'HYSMyeongJo-Medium'
    if re.search(r'[\u3040-\u30ff]', value):
        return 'HeiseiMin-W3'
    if re.search(r'[\u4e00-\u9fff]', value):
        return 'STSong-Light'
    return 'RepoSans'



def _safe(value: Any) -> str:
    if value is None:
        return 'Not available'
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, default=str)
    text = str(value)
    text = re.sub(r'(?i)(gh[pousr]_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]+)', '[REDACTED]', text)
    text = re.sub(r'(?i)(token|password|secret|authorization)\s*[:=]\s*[^\s,;]+', r'\1=[REDACTED]', text)
    safe = escape(text).replace('\n', '<br/>')
    # Built-in CID fonts provide reliable CJK fallback without depending on
    # fonts installed on the user's machine.
    safe = re.sub(r'([\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]+)', r'<font name="HYSMyeongJo-Medium">\1</font>', safe)
    safe = re.sub(r'([\u3040-\u30ff]+)', r'<font name="HeiseiMin-W3">\1</font>', safe)
    safe = re.sub(r'([\u4e00-\u9fff]+)', r'<font name="STSong-Light">\1</font>', safe)
    return safe


def _clean(obj: Any, key: str = '') -> Any:
    if re.search(r'(?i)(token|secret|password|credential|local_path|readme_content|\.env)', key):
        return None
    if isinstance(obj, dict):
        return {k: v for k, raw in obj.items() if (v := _clean(raw, k)) is not None}
    if isinstance(obj, list):
        return [_clean(v, key) for v in obj if _clean(v, key) is not None]
    return obj


class MiniBarChart(Flowable):
    """Small vector chart; values are rendered directly from dashboard data."""
    def __init__(self, title: str, items: list[dict], label_key: str, value_key: str, width=165*mm, height=66*mm):
        super().__init__(); self.title=title; self.items=items[:12]; self.label_key=label_key; self.value_key=value_key; self.width=width; self.height=height
    def draw(self):
        c=self.canv; c.setFont('RepoSans-Bold', 10); c.setFillColor(NAVY); c.drawString(0,self.height-10,self.title)
        data=[]
        for x in self.items:
            try: val=float(x.get(self.value_key,0) or 0)
            except (TypeError,ValueError): val=0
            data.append((str(x.get(self.label_key,'—'))[:25],max(0,val)))
        if not data: c.setFont('RepoSans',8);c.setFillColor(SLATE);c.drawString(0,self.height-28,'No chart data available.');return
        maxv=max((v for _,v in data),default=1) or 1
        row_h=min(13,(self.height-24)/max(1,len(data)))
        for i,(label,val) in enumerate(data):
            y=self.height-25-(i+1)*row_h
            c.setFont(_font_for_text(label),7);c.setFillColor(INK);c.drawString(0,y+2,label[:26])
            bx=57*mm; bw=95*mm*val/maxv
            c.setFillColor(PALE);c.roundRect(bx,y,95*mm,7,2,fill=1,stroke=0)
            c.setFillColor(BLUE);c.roundRect(bx,y,max(1,bw),7,2,fill=1,stroke=0)
            c.setFillColor(SLATE);c.drawRightString(self.width,y+1,f'{val:g}')


class DiagramFlowable(Flowable):
    """Readable, bounded graph layout for PDF pages.

    Repository architecture graphs are often sparse: a small number of real
    edges may connect only a few of many components. Treating every isolated
    node as its own graph depth makes the cards collapse to a few millimetres.
    A stable three-column card grid avoids that failure while retaining and
    drawing every relationship whose endpoints are in the displayed slice.
    """
    def __init__(self, title: str, nodes: list[dict], edges: list[dict], width=170*mm):
        super().__init__()
        self.title = title
        self.nodes = [n for n in (nodes or []) if isinstance(n, dict)][:24]
        self.edges = [e for e in (edges or []) if isinstance(e, dict)][:48]
        self.width = width
        self.columns = min(3, max(1, len(self.nodes)))
        self.rows = max(1, (len(self.nodes) + self.columns - 1) // self.columns)
        self.pad = 3*mm
        self.gap_x = 4*mm
        self.gap_y = 5*mm
        self.card_h = 13*mm
        self.card_w = (self.width - 2*self.pad - (self.columns-1)*self.gap_x) / self.columns
        self.height = 24*mm + self.rows*self.card_h + (self.rows-1)*self.gap_y
        self.id_to_index = {}
        for i, node in enumerate(self.nodes):
            self.id_to_index[str(node.get('id', i))] = i
        self.valid = []
        for edge in self.edges:
            src = str(edge.get('source', edge.get('from', '')))
            dst = str(edge.get('target', edge.get('to', '')))
            if src in self.id_to_index and dst in self.id_to_index:
                self.valid.append((edge, self.id_to_index[src], self.id_to_index[dst]))

    @staticmethod
    def _wrap(text: str, font: str, size: float, max_width: float, max_lines: int = 2):
        words = str(text).split()
        lines, current = [], ''
        for word in words:
            candidate = f'{current} {word}'.strip()
            if current and pdfmetrics.stringWidth(candidate, font, size) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            last = lines[-1]
            while last and pdfmetrics.stringWidth(last + '…', font, size) > max_width:
                last = last[:-1]
            lines[-1] = last.rstrip() + '…'
        return lines or ['Component']

    def _xy(self, index: int):
        col = index % self.columns
        row = index // self.columns
        x = self.pad + col*(self.card_w+self.gap_x)
        y = self.height - 20*mm - self.card_h - row*(self.card_h+self.gap_y)
        return x, y

    def draw(self):
        c = self.canv
        c.setFont('RepoSans-Bold', 10)
        c.setFillColor(NAVY)
        c.drawString(0, self.height-9*mm, self.title)
        if not self.nodes:
            c.setFont('RepoSans', 8)
            c.setFillColor(SLATE)
            c.drawString(0, self.height-18*mm, 'No diagram data was available.')
            return

        # Draw relationships first so their lines sit behind the component cards.
        for edge, source_i, target_i in self.valid:
            sx, sy = self._xy(source_i)
            tx, ty = self._xy(target_i)
            scx, scy = sx+self.card_w/2, sy+self.card_h/2
            tcx, tcy = tx+self.card_w/2, ty+self.card_h/2
            c.setStrokeColor(INDIGO if edge.get('type') == 'loop-back' else BLUE)
            c.setLineWidth(0.75)
            # Orthogonal routing keeps the relationship direction clear.
            if abs(tcy-scy) < 1:
                x1 = sx+self.card_w if tcx > scx else sx
                x2 = tx if tcx > scx else tx+self.card_w
                c.line(x1, scy, x2, tcy)
                tip_x = x2
                tip_y = tcy
                direction = 1 if tcx > scx else -1
                path = c.beginPath()
                path.moveTo(tip_x, tip_y)
                path.lineTo(tip_x- direction*2*mm, tip_y+1.2*mm)
                path.lineTo(tip_x- direction*2*mm, tip_y-1.2*mm)
            else:
                start_y = sy if tcy < scy else sy+self.card_h
                end_y = ty+self.card_h if tcy < scy else ty
                mid_y = (start_y+end_y)/2
                c.line(scx, start_y, scx, mid_y)
                c.line(scx, mid_y, tcx, mid_y)
                c.line(tcx, mid_y, tcx, end_y)
                tip_x, tip_y = tcx, end_y
                direction = 1 if tcy < scy else -1
                path = c.beginPath()
                path.moveTo(tip_x, tip_y)
                path.lineTo(tip_x-1.2*mm, tip_y-direction*2*mm)
                path.lineTo(tip_x+1.2*mm, tip_y-direction*2*mm)
            path.close()
            c.setFillColor(BLUE)
            c.drawPath(path, fill=1, stroke=0)
            label = edge.get('label') or edge.get('type')
            if label:
                c.setFont('RepoSans', 5.2)
                c.setFillColor(INDIGO)
                c.drawCentredString((scx+tcx)/2, (scy+tcy)/2+1.1*mm, str(label)[:22])

        for i, node in enumerate(self.nodes):
            x, y = self._xy(i)
            c.setFillColor(PALE)
            c.setStrokeColor(BORDER)
            c.roundRect(x, y, self.card_w, self.card_h, 2.2, fill=1, stroke=1)
            label = node.get('label') or node.get('name') or node.get('path') or node.get('id') or 'Component'
            label_lines = self._wrap(str(label), 'RepoSans-Bold', 6.4, self.card_w-5*mm, 2)
            c.setFillColor(NAVY)
            c.setFont('RepoSans-Bold', 6.4)
            line_gap = 2.7*mm
            first_y = y+self.card_h/2 + (len(label_lines)-1)*line_gap/2 - 1.1*mm
            for j, line in enumerate(label_lines):
                c.drawCentredString(x+self.card_w/2, first_y-j*line_gap, line)

        c.setFillColor(SLATE)
        c.setFont('Helvetica-Oblique', 5.8)
        c.drawString(self.pad, 2*mm,
                     f'{len(self.nodes)} displayed nodes · {len(self.valid)} directed relationships; compact component view.')


class ReportGenerationService:
    def generate(self, payload: dict[str, Any]) -> bytes:
        data = _clean(payload) or {}
        meta=data.get('repository_metadata') or {}; static=data.get('static_analysis_result') or {}
        git=data.get('git_history_result') or {}; metrics=data.get('repository_metrics_result') or {}
        analytics=data.get('analytics') or {}; advanced=data.get('advanced_visualizations') or {}
        ai=data.get('ai_insights'); owner=(meta.get('owner') or {}).get('login') or meta.get('full_name','').split('/')[0]
        repo=meta.get('full_name') or meta.get('name') or 'Repository'
        buf=io.BytesIO(); styles=getSampleStyleSheet()
        styles.add(ParagraphStyle(name='CoverTitle',parent=styles['Title'],fontName='RepoSans-Bold',fontSize=27,leading=33,textColor=NAVY,alignment=TA_LEFT,spaceAfter=12))
        styles.add(ParagraphStyle(name='H1x',parent=styles['Heading1'],fontName='RepoSans-Bold',fontSize=18,leading=22,textColor=NAVY,spaceBefore=10,spaceAfter=8,keepWithNext=True))
        styles.add(ParagraphStyle(name='H2x',parent=styles['Heading2'],fontName='RepoSans-Bold',fontSize=12,leading=15,textColor=BLUE,spaceBefore=8,spaceAfter=5,keepWithNext=True))
        styles.add(ParagraphStyle(name='Bodyx',parent=styles['BodyText'],fontName='RepoSans',fontSize=8.6,leading=12,textColor=INK,spaceAfter=5))
        styles.add(ParagraphStyle(name='Smallx',parent=styles['BodyText'],fontName='RepoSans',fontSize=7,leading=9,textColor=SLATE,spaceAfter=3))
        styles.add(ParagraphStyle(name='Cellx',parent=styles['BodyText'],fontName='RepoSans',fontSize=7,leading=9,textColor=INK))
        story=[]
        def p(v,style='Bodyx'): return Paragraph(_safe(v),styles[style])
        def heading(t): story.append(Paragraph(_safe(t),styles['H1x']))
        def sub(t): story.append(Paragraph(_safe(t),styles['H2x']))
        def para(t):
            if t not in (None,'',[],{}): story.append(p(t))
        def table(rows, widths=None):
            if not rows:return
            cooked=[[p(c,'Cellx') for c in row] for row in rows]
            t=LongTable(cooked,colWidths=widths,repeatRows=1,hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('TEXTCOLOR',(0,0),(-1,0),NAVY),('FONTNAME',(0,0),(-1,0),'RepoSans-Bold'),('GRID',(0,0),(-1,-1),.35,BORDER),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE2]),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.append(t);story.append(Spacer(1,5))
        def keyvals(obj, exclude=()):
            rows=[['Field','Value']]
            if isinstance(obj,dict):
                for k,v in obj.items():
                    if k in exclude or v is None or isinstance(v,(dict,list)): continue
                    rows.append([str(k).replace('_',' ').title(),str(v)])
            if len(rows)>1:table(rows,[48*mm,120*mm])
        def recursive_rows(obj,prefix='',rows=None,depth=0):
            rows=rows if rows is not None else []
            if len(rows)>=10000:return rows
            if isinstance(obj,dict):
                for k,v in obj.items(): recursive_rows(v,f'{prefix}.{k}' if prefix else k,rows,depth+1)
            elif isinstance(obj,list):
                for i,v in enumerate(obj): recursive_rows(v,f'{prefix}[{i}]',rows,depth+1)
            elif obj is not None: rows.append([prefix,str(obj)[:500]])
            return rows

        # Compact cover: the report intentionally contains only the three requested sections.
        story += [Spacer(1,34*mm),p('REPOINFOGRAPHIC  /  ENGINEERING INTELLIGENCE','Smallx'),Spacer(1,8*mm),Paragraph('Repository Engineering<br/>Insights Report',styles['CoverTitle']),HRFlowable(width='100%',thickness=2,color=INDIGO),Spacer(1,10*mm)]
        story.append(p(repo,'H2x'));para(meta.get('description'));story.append(Spacer(1,5*mm))
        cover=[['Repository owner',owner or 'Not available'],['Repository URL',meta.get('html_url','Not available')],['Primary branch',meta.get('default_branch','Not available')],['Primary language',meta.get('primary_language','Not available')],['Analysis generated',data.get('generated_at','Not available')],['Report generated',datetime.now(timezone.utc).isoformat()]]
        table([['Report metadata','Value']]+cover,[48*mm,120*mm]);story.append(Spacer(1,8*mm))
        para('This focused report contains engineering health metrics, repository-specific architecture and workflow visualizations, and AI insights generated from the completed analysis. Git commit history, general repository inventories, and raw analysis appendices are intentionally excluded.')
        story.append(PageBreak())

        # 1. Engineering metrics only (no commit history or general analytics dump).
        heading('1. Engineering Metrics')
        gauge=analytics.get('health_gauge') or {}
        if gauge:
            sub('Overall Repository Health')
            keyvals(gauge)
        if isinstance(metrics,dict) and metrics:
            for name,value in metrics.items():
                sub(name.replace('_',' ').title())
                if isinstance(value,dict):
                    keyvals(value)
                    for labelx,vals in value.items():
                        if isinstance(vals,list) and vals:
                            para(f'{labelx.replace("_", " ").title()}: '+'; '.join(map(str,vals[:8])))
                elif isinstance(value,list):
                    if value: table([['Metric','Observed value']]+[[str(i+1),str(v)] for i,v in enumerate(value[:8])],[35*mm,133*mm])
                elif value is not None: para(f'{name.replace("_", " ").title()}: {value}')
        else:
            para('Engineering metrics were not returned by the completed analysis.')

        # 2. Advanced visualizations: show representative diagrams and counts, not hundreds
        # of rows of raw graph data (the previous appendix made this report hundreds of pages).
        heading('2. Advanced Visualizations')
        if advanced.get('summary'):
            keyvals(advanced['summary'])
        dg=advanced.get('dependency_graph') or {}
        dn=dg.get('nodes') or []; de=dg.get('edges') or []
        sub('Dependency Graph')
        para(f'{len(dn)} detected nodes and {len(de)} directed dependency edges. The diagram is a representative view; raw node and edge inventories are omitted for readability.')
        if dn:
            story.append(DiagramFlowable('Representative dependency relationships',dn[:16],de[:24]))
        arch=advanced.get('architecture') or {}; an=arch.get('nodes') or []; ae=arch.get('edges') or []
        sub('Dynamic Architecture')
        para(f'{len(an)} architecture components and {len(ae)} relationships were extracted from repository evidence.')
        if an: story.append(DiagramFlowable('Architecture components and relationships',an[:18],ae[:28]))
        else: para('Architecture diagram data was unavailable.')
        wf=advanced.get('workflow') or {}; workflows=wf.get('workflows') or []
        sub('Repository Workflows')
        para(f'{len(workflows)} workflow(s) were statically reconstructed from source code. Each diagram is limited to a readable representative slice; full source paths remain available in the dashboard.')
        for i,w in enumerate(workflows[:5]):
            steps=w.get('steps') or []; wedges=w.get('edges') or []
            sub(w.get('name') or f'Workflow {i+1}')
            entry=w.get('entry_point') or {}
            para(f"Entry point: {entry.get('name','Not specified')} · {entry.get('path','')}:{entry.get('line','')} · {len(steps)} steps · {len(wedges)} transitions")
            if steps: story.append(DiagramFlowable('Execution flow (representative view)',steps[:14],wedges[:22]))
        if len(workflows)>5:
            para(f'{len(workflows)-5} additional workflows are available in the interactive dashboard and are not expanded in this concise PDF.')
        warnings=advanced.get('warnings') or wf.get('limitations') or []
        if warnings:
            sub('Visualization Notes')
            for warning in warnings[:4]: para('• '+str(warning))

        # 3. AI output: render structured sections concisely, without recursive dumping.
        heading('3. AI Engineering Insights')
        ai_clean=_clean(ai) or {}
        if not ai_clean:
            para('AI insights were not available in this analysis result (AI may be disabled or unavailable).')
        else:
            status=ai_clean.get('status')
            model=ai_clean.get('model')
            if status or model: para('Generation status: '+str(status or 'Not reported')+' · Model: '+str(model or 'Not reported'))
            insight_data=ai_clean.get('insights') or {}
            if not insight_data and isinstance(ai_clean,dict):
                insight_data={k:v for k,v in ai_clean.items() if isinstance(v,(dict,str)) and k not in {'error','status','model','generated_at'}}
            for key,section in insight_data.items():
                if not isinstance(section,dict):
                    if section: sub(key.replace('_',' ').title()); para(section)
                    continue
                if section.get('available') is False: continue
                sub(key.replace('_',' ').title())
                if section.get('summary'): para(section['summary'])
                observations=section.get('observations') or []
                if observations:
                    para('Key observations:')
                    for obs in observations[:3]:
                        if isinstance(obs,dict):
                            para('• '+str(obs.get('statement','')))
                            evidence=obs.get('evidence') or []
                            if evidence: para('Evidence: '+'; '.join(map(str,evidence[:3])))
                        else: para('• '+str(obs))
                recommendations=section.get('recommendations') or []
                if recommendations:
                    para('Recommendations:')
                    for recommendation in recommendations[:3]: para('• '+str(recommendation))
                stages=section.get('stages') or []
                for stage in stages[:3]:
                    if isinstance(stage,dict):
                        para(str(stage.get('level','Stage'))+': '+str(stage.get('description','')))
                        for item in (stage.get('items') or [])[:3]: para('• '+str(item))
                missing=section.get('missing_information') or []
                if missing: para('Evidence gaps: '+'; '.join(map(str,missing[:3])))
            if not insight_data: para('The AI stage did not return any structured insight sections.')

        doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=19*mm,leftMargin=19*mm,topMargin=21*mm,bottomMargin=18*mm,title=f'{repo} - RepoInfographic Analysis Report',author='RepoInfographic',subject='GitHub Repository Analysis')
        def page(canvas,document):
            canvas.saveState();w,h=A4
            if document.page>1:
                canvas.setStrokeColor(BORDER);canvas.line(19*mm,h-14*mm,w-19*mm,h-14*mm)
                canvas.setFont('RepoSans-Bold',7);canvas.setFillColor(NAVY);canvas.drawString(19*mm,h-11*mm,'REPOINFOGRAPHIC  |  REPOSITORY ANALYSIS')
            canvas.setStrokeColor(BORDER);canvas.line(19*mm,13*mm,w-19*mm,13*mm)
            canvas.setFont('RepoSans',7);canvas.setFillColor(SLATE);canvas.drawString(19*mm,8*mm,str(repo)[:70]);canvas.drawRightString(w-19*mm,8*mm,f'Page {document.page}')
            canvas.restoreState()
        doc.build(story,onFirstPage=page,onLaterPages=page)
        return buf.getvalue()
