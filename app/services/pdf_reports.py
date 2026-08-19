from datetime import datetime
from fpdf import FPDF

BRAND = (59, 130, 246)   # #3b82f6
INK = (30, 41, 59)
MUTED = (100, 116, 139)
LINE = (226, 232, 240)
GREEN = (16, 185, 129)
RED = (239, 68, 68)
AMBER = (245, 158, 11)


def _safe(text):
    """fpdf2's core fonts are latin-1 only — replace common unicode punctuation rather than crash."""
    if text is None:
        return ''
    text = str(text)
    replacements = {'–': '-', '—': '-', '‘': "'", '’': "'",
                    '“': '"', '”': '"', '…': '...', '·': '-', '→': '->'}
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text.encode('latin-1', 'replace').decode('latin-1')


class Report(FPDF):
    def __init__(self, title):
        super().__init__()
        self.report_title = title
        self.set_auto_page_break(auto=True, margin=18)
        self.add_page()

    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(*INK)
        self.cell(0, 10, _safe(self.report_title), ln=True)
        self.set_font('Helvetica', '', 9)
        self.set_text_color(*MUTED)
        self.cell(0, 6, f'MIGRC Compliance Platform - Generated {datetime.utcnow().strftime("%d %b %Y %H:%M UTC")}', ln=True)
        self.set_draw_color(*LINE)
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', '', 8)
        self.set_text_color(*MUTED)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def section(self, text):
        self.ln(2)
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(*INK)
        self.cell(0, 9, _safe(text), ln=True)
        self.set_draw_color(*LINE)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def kpi_row(self, items):
        """items: list of (label, value) tuples, rendered as evenly-spaced boxes."""
        n = len(items)
        w = 190 / n
        y0 = self.get_y()
        for i, (label, value) in enumerate(items):
            x = 10 + i * w
            self.set_xy(x, y0)
            self.set_font('Helvetica', 'B', 15)
            self.set_text_color(*BRAND)
            self.cell(w, 9, _safe(value), align='C', ln=0)
            self.set_xy(x, y0 + 9)
            self.set_font('Helvetica', '', 8)
            self.set_text_color(*MUTED)
            self.cell(w, 6, _safe(label), align='C')
        self.set_y(y0 + 20)

    def table(self, headers, rows, widths):
        self.set_font('Helvetica', 'B', 8.5)
        self.set_fill_color(241, 245, 249)
        self.set_text_color(*INK)
        for h, w in zip(headers, widths):
            self.cell(w, 7, _safe(h), border=0, fill=True)
        self.ln()
        self.set_font('Helvetica', '', 8.5)
        for row in rows:
            if self.get_y() > 270:
                self.add_page()
            for val, w in zip(row, widths):
                self.cell(w, 6.5, _safe(val), border='B')
            self.ln()
        self.ln(4)


def build_compliance_report_pdf(framework, subtitle=None):
    from app.models import Control
    controls = framework.controls.order_by(Control.code).all()
    pdf = Report(f'{framework.name} - Compliance Report')
    if subtitle:
        pdf.set_font('Helvetica', 'I', 10)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 6, _safe(subtitle), ln=True)
        pdf.ln(2)

    pdf.section('Summary')
    pdf.kpi_row([
        ('Compliance Score', f'{framework.compliance_score}%'),
        ('Passing', framework.passing),
        ('Failing', framework.failing),
        ('Not Assessed', framework.not_assessed),
        ('N/A', framework.not_applicable),
    ])

    pdf.section(f'Controls ({len(controls)})')
    rows = [(c.code, c.title[:55], c.category or '-', c.status) for c in controls]
    pdf.table(['Code', 'Title', 'Category', 'Status'], rows, [20, 95, 40, 35])

    return bytes(pdf.output())


def build_audit_report_pdf(audit, evidence_items, findings):
    pdf = Report(f'Audit Report - {audit.name}')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, _safe(f'Framework: {audit.framework}   Auditor: {audit.auditor or "-"}'), ln=True)
    pdf.cell(0, 6, _safe(f'Period: {audit.start_date} to {audit.end_date}   Status: {audit.status}'), ln=True)
    pdf.ln(2)

    pdf.section(f'Evidence Summary ({audit.evidence_collected}/{audit.evidence_total} collected)')
    rows = [(i.control.code, i.control.title[:55], i.status, i.evidence.title if i.evidence else '-') for i in evidence_items]
    pdf.table(['Code', 'Control', 'Status', 'Evidence'], rows, [18, 80, 30, 62])

    pdf.section(f'Findings ({len(findings)})')
    if findings:
        rows = []
        for f in findings:
            remediation = f'{f.remediation.owner or "-"} / {f.remediation.status}' if f.remediation else 'Not planned'
            rows.append((f.type, f.severity, f.description[:60], f.status, remediation))
        pdf.table(['Type', 'Severity', 'Description', 'Status', 'Remediation'], rows, [28, 22, 65, 25, 50])
    else:
        pdf.set_font('Helvetica', 'I', 9)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 6, 'No findings were logged for this audit.', ln=True)

    return bytes(pdf.output())


def build_dashboard_snapshot_pdf(context):
    pdf = Report('Executive Compliance Summary')
    pdf.section('Key Metrics')
    pdf.kpi_row([
        ('Compliance Score', f"{context['compliance_score']}%"),
        ('Open Risks', context['open_risks']),
        ('Active Policies', context['policy_count']),
        ('Pending Evidence', context['pending_evidence']),
    ])

    pdf.section('Frameworks')
    rows = [(fw['name'], fw['category'], f"{fw['compliance_score']}%", fw['passing'], fw['failing']) for fw in context['frameworks']]
    pdf.table(['Framework', 'Category', 'Score', 'Passing', 'Failing'], rows, [70, 40, 25, 27, 28])

    pdf.section('Top Risks')
    rows = [(r.title[:60], r.impact, str(r.score), r.status) for r in context['risks']]
    pdf.table(['Risk', 'Impact', 'Score', 'Status'], rows, [95, 30, 25, 40])

    pdf.section('Upcoming Deadlines (30 days)')
    if context['deadlines']:
        rows = [(d['type'], d['name'][:50], d['date'].strftime('%d %b %Y'), f"{d['days_until']}d") for d in context['deadlines']]
        pdf.table(['Type', 'Item', 'Due', 'In'], rows, [45, 80, 35, 30])
    else:
        pdf.set_font('Helvetica', 'I', 9)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 6, 'Nothing due in the next 30 days.', ln=True)

    return bytes(pdf.output())


def build_soc2_readiness_pdf(framework):
    subtitle = ('This report summarizes readiness against the AICPA SOC 2 Common Criteria as currently '
                'assessed in MIGRC. It is a working readiness snapshot, not a certified audit opinion.')
    return build_compliance_report_pdf(framework, subtitle=subtitle)
