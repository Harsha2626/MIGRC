from flask import Blueprint, render_template, g, current_app
from flask_login import login_required

from app.integrations import registry, CATEGORIES
from app.models import IntegrationConnection, GoogleWorkspaceConnection, EntraConnection, AzureConnection, OktaConnection, SlackConnection, JiraConnection

integrations_bp = Blueprint('integrations', __name__)

# Honest roadmap: nothing here is implemented yet.  Live apps (Google Workspace, Entra ID, Azure) are rendered directly in the template.
PLANNED_INTEGRATIONS = []  # every announced integration is implemented; add roadmap items here


@integrations_bp.route('/integrations')
@login_required
def integrations():
    org = getattr(g, 'current_org', None)
    connection = (GoogleWorkspaceConnection.query.filter_by(organization_id=org.id).first()
                  if org else None)
    entra_connection = (EntraConnection.query.filter_by(organization_id=org.id).first() if org else None)
    entra_configured = bool(current_app.config.get('ENTRA_CLIENT_ID') and current_app.config.get('ENTRA_CLIENT_SECRET')
                            and current_app.config.get('ENTRA_REDIRECT_URI'))
    azure_connection = (AzureConnection.query.filter_by(organization_id=org.id).first() if org else None)
    okta_connection = (OktaConnection.query.filter_by(organization_id=org.id).first() if org else None)
    slack_connection = (SlackConnection.query.filter_by(organization_id=org.id).first() if org else None)
    jira_connection = (JiraConnection.query.filter_by(organization_id=org.id).first() if org else None)
    google_configured = bool(current_app.config.get('GOOGLE_CLIENT_ID'))
    conns = ({c.provider: c for c in IntegrationConnection.query.filter_by(organization_id=org.id)} if org else {})
    reg = {}
    for spec in registry().values():
        reg.setdefault(spec['category'], []).append(spec)
    categories = {}
    for item in PLANNED_INTEGRATIONS:
        categories.setdefault(item['category'], []).append(item)
    categories = [(c, categories.get(c, []), reg.get(c, [])) for c in CATEGORIES]
    return render_template('integrations.html', page='integrations',
                           google_connection=connection, entra_connection=entra_connection, azure_connection=azure_connection, okta_connection=okta_connection, slack_connection=slack_connection, jira_connection=jira_connection, entra_configured=entra_configured, google_configured=google_configured,
                           planned_categories=categories, conns=conns)
