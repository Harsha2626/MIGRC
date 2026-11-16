from flask import Blueprint, render_template, g, current_app
from flask_login import login_required

from app.models import GoogleWorkspaceConnection, EntraConnection

integrations_bp = Blueprint('integrations', __name__)

# Honest roadmap: nothing here is implemented yet.  Live apps (Google Workspace, Entra ID) are rendered in the template's Available now section.
PLANNED_INTEGRATIONS = [
    {'category': 'Cloud Providers', 'name': 'Amazon Web Services', 'icon': 'fab fa-aws', 'color': 'orange',
     'capabilities': ['Automated tests', 'Asset inventory', 'Continuous monitoring']},
    {'category': 'Cloud Providers', 'name': 'Google Cloud', 'icon': 'fab fa-google', 'color': 'red',
     'capabilities': ['Automated tests', 'Asset inventory']},
    {'category': 'Cloud Providers', 'name': 'Microsoft Azure', 'icon': 'fab fa-microsoft', 'color': 'blue',
     'capabilities': ['Automated tests', 'Asset inventory', 'User access data']},
    {'category': 'Identity Providers', 'name': 'Okta', 'icon': None, 'badge': 'OK', 'color': 'blue',
     'capabilities': ['Employee directory', 'User access data', 'SSO']},
    {'category': 'SaaS Application', 'name': 'Slack', 'icon': 'fab fa-slack', 'color': 'green',
     'capabilities': ['Notifications', 'Employee directory']},
    {'category': 'SaaS Application', 'name': 'Jira', 'icon': 'fab fa-jira', 'color': 'blue',
     'capabilities': ['Remediation ticket sync', 'Risk and finding tracking']},
]


@integrations_bp.route('/integrations')
@login_required
def integrations():
    org = getattr(g, 'current_org', None)
    connection = (GoogleWorkspaceConnection.query.filter_by(organization_id=org.id).first()
                  if org else None)
    entra_connection = (EntraConnection.query.filter_by(organization_id=org.id).first() if org else None)
    entra_configured = bool(current_app.config.get('ENTRA_CLIENT_ID') and current_app.config.get('ENTRA_CLIENT_SECRET')
                            and current_app.config.get('ENTRA_REDIRECT_URI'))
    google_configured = bool(current_app.config.get('GOOGLE_CLIENT_ID'))
    categories = {}
    for item in PLANNED_INTEGRATIONS:
        categories.setdefault(item['category'], []).append(item)
    categories = [(c, categories[c]) for c in ('Cloud Providers', 'Identity Providers', 'SaaS Application')]
    return render_template('integrations.html', page='integrations',
                           google_connection=connection, entra_connection=entra_connection, entra_configured=entra_configured, google_configured=google_configured,
                           planned_categories=categories)
