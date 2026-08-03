from flask import Flask, render_template, jsonify, request
import json
from datetime import datetime, timedelta
import random

app = Flask(__name__)
app.secret_key = 'migrc-prototype-key'

# ============================================================
# MOCK DATA
# ============================================================

FRAMEWORKS = [
    # ISO 27001:2022 Annex A: 93 controls across 4 themes
    # Organizational (37), People (8), Physical (14), Technological (34)
    # Source: ISO/IEC 27001:2022 standard
    {"id": 1, "name": "ISO 27001:2022", "icon": "globe", "total_controls": 93,
     "controls_detail": "Organizational (37) + People (8) + Physical (14) + Technological (34)",
     "passing": 71, "failing": 13, "not_applicable": 9, "status": "In Progress", "category": "Security",
     "description": "International standard for Information Security Management Systems (ISMS) with 93 Annex A controls"},
]

RISKS = [
    {"id": 1, "title": "Unauthorized access to production databases", "category": "Access Control", "likelihood": "High", "impact": "Critical", "score": 25, "owner": "Raj Patel", "status": "Open", "treatment": "Mitigate", "created": "2026-06-15"},
    {"id": 2, "title": "Third-party vendor data breach", "category": "Vendor Risk", "likelihood": "Medium", "impact": "High", "score": 16, "owner": "Priya Sharma", "status": "In Treatment", "treatment": "Transfer", "created": "2026-05-20"},
    {"id": 3, "title": "Lack of encryption for data at rest", "category": "Data Protection", "likelihood": "Medium", "impact": "High", "score": 15, "owner": "Amit Kumar", "status": "Open", "treatment": "Mitigate", "created": "2026-07-01"},
    {"id": 4, "title": "Insufficient backup and disaster recovery", "category": "Business Continuity", "likelihood": "Low", "impact": "Critical", "score": 12, "owner": "Neha Gupta", "status": "In Treatment", "treatment": "Mitigate", "created": "2026-04-10"},
    {"id": 5, "title": "Phishing attack on employees", "category": "Social Engineering", "likelihood": "High", "impact": "Medium", "score": 15, "owner": "Vikram Singh", "status": "Open", "treatment": "Mitigate", "created": "2026-06-28"},
    {"id": 6, "title": "Unpatched critical vulnerabilities", "category": "Vulnerability Mgmt", "likelihood": "High", "impact": "High", "score": 20, "owner": "Raj Patel", "status": "Open", "treatment": "Mitigate", "created": "2026-07-10"},
    {"id": 7, "title": "Insider threat - privileged user abuse", "category": "Access Control", "likelihood": "Low", "impact": "High", "score": 10, "owner": "Priya Sharma", "status": "Accepted", "treatment": "Accept", "created": "2026-03-15"},
    {"id": 8, "title": "Cloud misconfiguration in AWS S3", "category": "Cloud Security", "likelihood": "Medium", "impact": "High", "score": 16, "owner": "Amit Kumar", "status": "Open", "treatment": "Mitigate", "created": "2026-07-18"},
]

POLICIES = [
    {"id": 1, "name": "Information Security Policy", "version": "3.2", "owner": "CISO", "status": "Published", "last_reviewed": "2026-06-01", "next_review": "2026-12-01", "framework": "ISO 27001", "acknowledgements": 45, "total_employees": 50},
    {"id": 2, "name": "Acceptable Use Policy", "version": "2.1", "owner": "IT Head", "status": "Published", "last_reviewed": "2026-05-15", "next_review": "2026-11-15", "framework": "SOC 2", "acknowledgements": 48, "total_employees": 50},
    {"id": 3, "name": "Data Classification Policy", "version": "1.5", "owner": "Data Protection Officer", "status": "Published", "last_reviewed": "2026-04-20", "next_review": "2026-10-20", "framework": "GDPR", "acknowledgements": 42, "total_employees": 50},
    {"id": 4, "name": "Incident Response Plan", "version": "2.0", "owner": "Security Lead", "status": "Draft", "last_reviewed": "2026-07-01", "next_review": "2027-01-01", "framework": "SOC 2", "acknowledgements": 0, "total_employees": 50},
    {"id": 5, "name": "Access Control Policy", "version": "3.0", "owner": "IT Head", "status": "Published", "last_reviewed": "2026-03-10", "next_review": "2026-09-10", "framework": "ISO 27001", "acknowledgements": 50, "total_employees": 50},
    {"id": 6, "name": "Business Continuity Policy", "version": "1.2", "owner": "COO", "status": "In Review", "last_reviewed": "2026-06-20", "next_review": "2026-12-20", "framework": "ISO 27001", "acknowledgements": 30, "total_employees": 50},
    {"id": 7, "name": "Password Policy", "version": "4.0", "owner": "IT Head", "status": "Published", "last_reviewed": "2026-07-05", "next_review": "2027-01-05", "framework": "SOC 2", "acknowledgements": 47, "total_employees": 50},
    {"id": 8, "name": "Privacy Policy", "version": "2.5", "owner": "Data Protection Officer", "status": "Published", "last_reviewed": "2026-05-25", "next_review": "2026-11-25", "framework": "GDPR", "acknowledgements": 44, "total_employees": 50},
]

AUDITS = [
    {"id": 1, "name": "SOC 2 Type II Annual Audit", "framework": "SOC 2", "auditor": "Deloitte", "status": "In Progress", "start_date": "2026-07-01", "end_date": "2026-08-30", "evidence_collected": 42, "evidence_total": 64, "findings": 3},
    {"id": 2, "name": "ISO 27001 Surveillance Audit", "framework": "ISO 27001", "auditor": "BSI Group", "status": "Scheduled", "start_date": "2026-09-15", "end_date": "2026-10-15", "evidence_collected": 10, "evidence_total": 93, "findings": 0},
    {"id": 3, "name": "GDPR Data Protection Audit", "framework": "GDPR", "auditor": "Internal", "status": "Completed", "start_date": "2026-04-01", "end_date": "2026-05-15", "evidence_collected": 42, "evidence_total": 42, "findings": 2},
    {"id": 4, "name": "PCI DSS v4.0 Assessment", "framework": "PCI DSS", "auditor": "Coalfire", "status": "Scheduled", "start_date": "2026-10-01", "end_date": "2026-11-30", "evidence_collected": 0, "evidence_total": 78, "findings": 0},
]

VENDORS = [
    {"id": 1, "name": "AWS", "category": "Cloud Infrastructure", "risk_tier": "Critical", "risk_score": 82, "status": "Approved", "last_assessment": "2026-06-15", "next_assessment": "2026-12-15", "compliance": ["SOC 2", "ISO 27001", "HIPAA"]},
    {"id": 2, "name": "Slack", "category": "Communication", "risk_tier": "High", "risk_score": 71, "status": "Approved", "last_assessment": "2026-05-20", "next_assessment": "2026-11-20", "compliance": ["SOC 2", "ISO 27001"]},
    {"id": 3, "name": "GitHub", "category": "Development", "risk_tier": "Critical", "risk_score": 78, "status": "Approved", "last_assessment": "2026-04-10", "next_assessment": "2026-10-10", "compliance": ["SOC 2", "ISO 27001"]},
    {"id": 4, "name": "Salesforce", "category": "CRM", "risk_tier": "High", "risk_score": 68, "status": "Under Review", "last_assessment": "2026-07-01", "next_assessment": "2027-01-01", "compliance": ["SOC 2", "ISO 27001", "GDPR"]},
    {"id": 5, "name": "Stripe", "category": "Payment Processing", "risk_tier": "Critical", "risk_score": 85, "status": "Approved", "last_assessment": "2026-06-01", "next_assessment": "2026-12-01", "compliance": ["PCI DSS", "SOC 2", "ISO 27001"]},
    {"id": 6, "name": "Jira", "category": "Project Management", "risk_tier": "Medium", "risk_score": 55, "status": "Approved", "last_assessment": "2026-03-15", "next_assessment": "2026-09-15", "compliance": ["SOC 2"]},
    {"id": 7, "name": "Datadog", "category": "Monitoring", "risk_tier": "High", "risk_score": 65, "status": "Approved", "last_assessment": "2026-05-10", "next_assessment": "2026-11-10", "compliance": ["SOC 2", "ISO 27001"]},
    {"id": 8, "name": "Zoom", "category": "Communication", "risk_tier": "Medium", "risk_score": 52, "status": "Approved", "last_assessment": "2026-04-20", "next_assessment": "2026-10-20", "compliance": ["SOC 2"]},
]

ASSETS = [
    {"id": 1, "name": "Production Database (RDS)", "type": "Database", "environment": "Production", "owner": "Raj Patel", "classification": "Confidential", "status": "Active", "cloud_provider": "AWS"},
    {"id": 2, "name": "Web Application Server", "type": "Compute", "environment": "Production", "owner": "Amit Kumar", "classification": "Internal", "status": "Active", "cloud_provider": "AWS"},
    {"id": 3, "name": "S3 Data Lake", "type": "Storage", "environment": "Production", "owner": "Priya Sharma", "classification": "Confidential", "status": "Active", "cloud_provider": "AWS"},
    {"id": 4, "name": "CI/CD Pipeline Server", "type": "Compute", "environment": "Development", "owner": "Vikram Singh", "classification": "Internal", "status": "Active", "cloud_provider": "AWS"},
    {"id": 5, "name": "Employee Laptops", "type": "Endpoint", "environment": "Corporate", "owner": "IT Head", "classification": "Internal", "status": "Active", "cloud_provider": "N/A"},
    {"id": 6, "name": "VPN Gateway", "type": "Network", "environment": "Production", "owner": "Raj Patel", "classification": "Restricted", "status": "Active", "cloud_provider": "AWS"},
    {"id": 7, "name": "Backup Storage", "type": "Storage", "environment": "DR", "owner": "Neha Gupta", "classification": "Confidential", "status": "Active", "cloud_provider": "AWS"},
    {"id": 8, "name": "Staging Environment", "type": "Compute", "environment": "Staging", "owner": "Amit Kumar", "classification": "Internal", "status": "Active", "cloud_provider": "AWS"},
]

TRAINING_MODULES = [
    {"id": 1, "name": "Security Awareness Fundamentals", "category": "General", "duration": "30 min", "assigned": 50, "completed": 45, "overdue": 3, "status": "Active"},
    {"id": 2, "name": "Phishing Prevention", "category": "Social Engineering", "duration": "20 min", "assigned": 50, "completed": 42, "overdue": 5, "status": "Active"},
    {"id": 3, "name": "Data Handling & Classification", "category": "Data Protection", "duration": "25 min", "assigned": 50, "completed": 38, "overdue": 8, "status": "Active"},
    {"id": 4, "name": "GDPR Compliance Training", "category": "Privacy", "duration": "45 min", "assigned": 30, "completed": 28, "overdue": 1, "status": "Active"},
    {"id": 5, "name": "Incident Reporting Procedures", "category": "Incident Response", "duration": "15 min", "assigned": 50, "completed": 47, "overdue": 0, "status": "Active"},
    {"id": 6, "name": "Password Security Best Practices", "category": "Access Control", "duration": "15 min", "assigned": 50, "completed": 49, "overdue": 0, "status": "Completed"},
]

ACCESS_REVIEWS = [
    {"id": 1, "user": "Raj Patel", "role": "Admin", "systems": ["AWS Console", "Production DB", "GitHub"], "last_review": "2026-06-01", "next_review": "2026-09-01", "status": "Active", "risk": "High"},
    {"id": 2, "user": "Priya Sharma", "role": "Developer", "systems": ["GitHub", "Jira", "Staging DB"], "last_review": "2026-06-15", "next_review": "2026-09-15", "status": "Active", "risk": "Medium"},
    {"id": 3, "user": "Amit Kumar", "role": "DevOps", "systems": ["AWS Console", "CI/CD", "Docker Registry"], "last_review": "2026-05-20", "next_review": "2026-08-20", "status": "Review Due", "risk": "High"},
    {"id": 4, "user": "Neha Gupta", "role": "Analyst", "systems": ["Jira", "Confluence", "Slack"], "last_review": "2026-07-01", "next_review": "2026-10-01", "status": "Active", "risk": "Low"},
    {"id": 5, "user": "Vikram Singh", "role": "Developer", "systems": ["GitHub", "Jira", "Dev DB"], "last_review": "2026-06-10", "next_review": "2026-09-10", "status": "Active", "risk": "Medium"},
]


# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def dashboard():
    total_controls = sum(f['total_controls'] for f in FRAMEWORKS)
    passing_controls = sum(f['passing'] for f in FRAMEWORKS)
    failing_controls = sum(f['failing'] for f in FRAMEWORKS)
    compliance_score = round((passing_controls / total_controls) * 100) if total_controls > 0 else 0

    open_risks = len([r for r in RISKS if r['status'] == 'Open'])
    critical_risks = len([r for r in RISKS if r['impact'] == 'Critical'])
    policy_count = len([p for p in POLICIES if p['status'] == 'Published'])
    pending_audits = len([a for a in AUDITS if a['status'] in ['In Progress', 'Scheduled']])

    return render_template('dashboard.html',
        page='dashboard',
        compliance_score=compliance_score,
        total_controls=total_controls,
        passing_controls=passing_controls,
        failing_controls=failing_controls,
        open_risks=open_risks,
        critical_risks=critical_risks,
        policy_count=policy_count,
        pending_audits=pending_audits,
        frameworks=FRAMEWORKS,
        risks=RISKS[:5],
        audits=AUDITS,
        vendors_count=len(VENDORS),
        assets_count=len(ASSETS),
    )

@app.route('/compliance')
def compliance():
    return render_template('compliance.html', page='compliance', frameworks=FRAMEWORKS)

@app.route('/risks')
def risks():
    return render_template('risks.html', page='risks', risks=RISKS)

@app.route('/policies')
def policies():
    return render_template('policies.html', page='policies', policies=POLICIES)

@app.route('/audits')
def audits():
    return render_template('audits.html', page='audits', audits=AUDITS)

@app.route('/vendors')
def vendors():
    return render_template('vendors.html', page='vendors', vendors=VENDORS)

@app.route('/assets')
def assets():
    return render_template('assets.html', page='assets', assets=ASSETS)

@app.route('/access-reviews')
def access_reviews():
    return render_template('access_reviews.html', page='access_reviews', reviews=ACCESS_REVIEWS)

@app.route('/training')
def training():
    return render_template('training.html', page='training', modules=TRAINING_MODULES)

@app.route('/trust-center')
def trust_center():
    published_policies = [p for p in POLICIES if p['status'] == 'Published']
    active_frameworks = [f for f in FRAMEWORKS if f['status'] in ['Active', 'In Progress']]
    return render_template('trust_center.html', page='trust_center',
        policies=published_policies, frameworks=active_frameworks)

@app.route('/settings')
def settings():
    return render_template('settings.html', page='settings')


# ============================================================
# API ENDPOINTS (for AJAX / chart data)
# ============================================================

@app.route('/api/dashboard/stats')
def api_dashboard_stats():
    total_controls = sum(f['total_controls'] for f in FRAMEWORKS)
    passing = sum(f['passing'] for f in FRAMEWORKS)
    failing = sum(f['failing'] for f in FRAMEWORKS)
    return jsonify({
        'compliance_score': round((passing / total_controls) * 100),
        'total_controls': total_controls,
        'passing': passing,
        'failing': failing,
        'open_risks': len([r for r in RISKS if r['status'] == 'Open']),
        'critical_risks': len([r for r in RISKS if r['impact'] == 'Critical']),
        'frameworks': FRAMEWORKS,
    })

@app.route('/api/risks/matrix')
def api_risk_matrix():
    matrix = {"Critical": {"High": 0, "Medium": 0, "Low": 0},
              "High": {"High": 0, "Medium": 0, "Low": 0},
              "Medium": {"High": 0, "Medium": 0, "Low": 0},
              "Low": {"High": 0, "Medium": 0, "Low": 0}}
    for r in RISKS:
        if r['impact'] in matrix and r['likelihood'] in matrix[r['impact']]:
            matrix[r['impact']][r['likelihood']] += 1
    return jsonify(matrix)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
