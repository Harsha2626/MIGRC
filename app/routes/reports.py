from flask import Blueprint, render_template, Response
from flask_login import login_required
from app.models import Framework
from app.routes.main import _dashboard_context
from app.services.pdf_reports import build_dashboard_snapshot_pdf, build_soc2_readiness_pdf

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports')
@login_required
def reports():
    frameworks = Framework.query.order_by(Framework.name).all()
    soc2 = next((fw for fw in frameworks if 'soc 2' in fw.name.lower() or 'soc2' in fw.name.lower()), None)
    return render_template('reports.html', page='reports', frameworks=frameworks, soc2=soc2)


@reports_bp.route('/reports/dashboard.pdf')
@login_required
def dashboard_pdf():
    context = _dashboard_context()
    pdf_bytes = build_dashboard_snapshot_pdf(context)
    return Response(pdf_bytes, mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=migrc_executive_summary.pdf'})


@reports_bp.route('/reports/soc2-readiness.pdf')
@login_required
def soc2_readiness_pdf():
    frameworks = Framework.query.all()
    soc2 = next((fw for fw in frameworks if 'soc 2' in fw.name.lower() or 'soc2' in fw.name.lower()), None)
    if not soc2:
        return Response('SOC 2 framework has not been configured yet. Add it under Compliance first.',
            status=404, mimetype='text/plain')
    pdf_bytes = build_soc2_readiness_pdf(soc2)
    return Response(pdf_bytes, mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=soc2_readiness_report.pdf'})
