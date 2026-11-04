from flask import Blueprint, render_template, g, current_app
from flask_login import login_required

from app.models import GoogleWorkspaceConnection

integrations_bp = Blueprint('integrations', __name__)

# Honest roadmap: nothing here is implemented yet. Only Google Workspace is real.
PLANNED_INTEGRATIONS = [
    {'category': 'Cloud Providers', 'name': 'Amazon Web Services', 'icon': 'fab fa-aws', 'color': 'orange',
     'capabilities': ['Automated tests', 'Asset inventory', 'Continuous monitoring']},
    {'category': 'Cloud Providers', 'name': 'Google Cloud', 'icon': 'fab fa-google', 'color': 'red',
     'capabilities': ['Automated tests', 'Asset inventory']},
    {'category': 'Cloud Providers', 'name': 'Microsoft Azure', 'icon': 'fab fa-microsoft', 'color': 'blue',
     'capabilities': ['Automated tests', 'Asset inventory', 'User access data']},
    {'category': 'Identity Providers', 'name': 'Okta', 'icon': None, 'badge': 'OK', 'color': 'blue',
     'capabilities': ['Employee directory', 'User access data', 'SSO']},
    {'category': 'Identity Providers', 'name': 'Microsoft Entra ID', 'icon': 'fab fa-microsoft', 'color': 'blue',
     'capabilities': ['Employee directory', 'User access data', 'SSO']},
    {'category': 'Workplace Tools', 'name': 'Slack', 'icon': 'fab fa-slack', 'color': 'green',
     'capabilities': ['Notifications', 'Employee directory']},
    {'category': 'Workplace Tools', 'name': 'Jira', 'icon': 'fab fa-jira', 'color': 'blue',
     'capabilities': ['Remediation ticket sync', 'Risk and finding tracking']},
]


@integrations_bp.route('/integrations')
@login_required
def integrations():
    org = getattr(g, 'current_org', None)
    connection = (GoogleWorkspaceConnection.query.filter_by(organization_id=org.id).first()
                  if org else None)
    google_configured = bool(current_app.config.get('GOOGLE_CLIENT_ID'))
    categories = []
    for item in PLANNED_INTEGRATIONS:
        if not categories or categories[-1][0] != item['category']:
            categories.append((item['category'], []))
        categories[-1][1].append(item)
    return render_template('integrations.html', page='integrations',
                           google_connection=connection, google_configured=google_configured,
                           planned_categories=categories)
