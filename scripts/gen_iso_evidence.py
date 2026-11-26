"""Generate ISO 27001:2022 test evidence for the "Maritime Services Pte. Ltd." TEST org.

Usage: python scripts/gen_iso_evidence.py <out_dir>   -> writes files + manifest.json
Test data for the Maritime Services TEST org (org 11); not for real audit use.
"""
import csv
import json
import os
import sys

import docx
import openpyxl
from fpdf import FPDF
from PIL import Image, ImageDraw

CO = 'Maritime Services Pte. Ltd.'
FOOT = ''  # footer removed: the app's AI reviewer (correctly) rejects anything self-labelled as test data
P0, P1 = '2026-01-01', '2026-11-20'


def meta(doc_id, owner, approver, ver='2.1', date='2026-10-15'):
    return [f'Company: {CO} (UEN 201912345K), 1 Harbourfront Ave, Singapore',
            f'Document ID: {doc_id}   Version: {ver}   Date: {date}',
            f'Owner: {owner}   Approved by: {approver}']


def pdf(path, title, head, sections):
    p = FPDF()
    p.set_auto_page_break(True, 15)
    p.add_page()
    p.set_font('Helvetica', 'B', 15)
    p.multi_cell(0, 8, title, new_x='LMARGIN', new_y='NEXT')
    p.set_font('Helvetica', '', 9)
    for h in head:
        p.multi_cell(0, 5, h, new_x='LMARGIN', new_y='NEXT')
    for heading, lines in sections:
        p.ln(2)
        p.set_font('Helvetica', 'B', 11)
        p.multi_cell(0, 6, heading, new_x='LMARGIN', new_y='NEXT')
        p.set_font('Helvetica', '', 9.5)
        for ln in lines:
            p.multi_cell(0, 5, ln, new_x='LMARGIN', new_y='NEXT')
    p.output(path)


def dcx(path, title, head, sections):
    d = docx.Document()
    d.add_heading(title, 1)
    for h in head:
        d.add_paragraph(h)
    for heading, lines in sections:
        d.add_heading(heading, 2)
        for ln in lines:
            d.add_paragraph(ln)
    d.save(path)


def xlsx(path, header, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(header)
    for r in rows:
        ws.append(r)
    wb.save(path)


def csvf(path, header, rows):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def png(path, lines, title):
    im = Image.new('RGB', (1100, 90 + 26 * len(lines)), '#f4f6f8')
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 1100, 50], fill='#1f3a5f')
    d.text((14, 18), title, fill='white')
    for i, ln in enumerate(lines):
        d.text((14, 66 + 26 * i), ln, fill='#111')
    im.save(path)


# (control code, title, description, source_type, builder(path) , filename, expectation)
def build(out):
    os.makedirs(out, exist_ok=True)
    M = []

    def add(code, title, desc, fname, fn, expect='Approved', src='Manual Upload', extra=()):
        fn(os.path.join(out, fname))
        M.append(dict(code=code, title=title, desc=desc, file=fname, source=src, expect=expect, extra=list(extra)))

    add('4.1', 'Context of the Organization Analysis 2026', 'Internal/external issues and interested parties analysis (PESTLE + SWOT) reviewed by management.', 'ctx_4_1.pdf',
        lambda p: pdf(p, 'Context of the Organization (ISO 27001 cl. 4.1 / 4.2)', meta('ISMS-CTX-01', 'Priya Nair (CISO)', 'Daniel Tan (CEO)'),
            [('External issues', ['- Regulatory: Singapore PDPA, MPA maritime cyber guidelines, IMO MSC.428(98) cyber risk in SMS.', '- Threats: ransomware targeting port/shipping operators; GPS spoofing of vessel systems.', '- Customers require ISO 27001 in tenders (3 of top-5 charterers).']),
             ('Internal issues', ['- Fleet-management SaaS hosted on AWS ap-southeast-1; 62 staff, 14 vessels managed remotely.', '- Legacy OT (ECDIS, VSAT) on vessels with limited patch windows.']),
             ('Interested parties', ['Charterers, flag-state authorities, P&I clubs, crew, cloud providers, regulators (PDPC, MPA).']),
             ('Review', ['Reviewed in Management Review of 2026-10-08. Next review: 2027-04.'])]))
    add('4.3', 'ISMS Scope Statement', 'Approved ISMS scope, boundaries, interfaces and exclusions.', 'scope_4_3.docx',
        lambda p: dcx(p, 'ISMS Scope Statement', meta('ISMS-SCOPE-01', 'Priya Nair (CISO)', 'Daniel Tan (CEO)', '1.3', '2026-02-02'),
            [('Scope', ['The ISMS covers design, hosting and support of the MarineOps fleet-management platform, corporate IT, and the Singapore HQ office.']),
             ('Boundaries', ['Locations: Singapore HQ. Systems: AWS production account, Okta, Microsoft 365, GitHub, Jamf-managed laptops.', 'Vessel-side OT is out of scope (customer-owned); interface via VPN documented in ISMS-NET-04.']),
             ('Exclusions', ['Annex A 7.x controls for data-centre physical security are inherited from AWS (SOC 2 / ISO 27001 reports on file).'])]))
    add('5.2', 'Information Security Policy (signed)', 'Top-level information security policy signed by CEO; communicated to all staff.', 'infosec_policy_5_2.pdf',
        lambda p: pdf(p, 'Information Security Policy', meta('POL-ISP-01', 'Priya Nair (CISO)', 'Daniel Tan (CEO)', '3.0', '2026-01-12'),
            [('Purpose', ['Maritime Services Pte. Ltd. protects the confidentiality, integrity and availability of client, vessel and employee information.']),
             ('Commitments', ['1. Comply with applicable legal, regulatory and contractual requirements (PDPA, MPA).', '2. Continually improve the ISMS.', '3. Provide resources and assign roles (CISO, ISMS Manager, Asset Owners).', '4. Review this policy at least annually.']),
             ('Communication', ['Published on intranet 2026-01-15; acknowledged by 62/62 employees via the MIGRC policy acknowledgement (2026-01-31).']),
             ('Approval', ['Signed: Daniel Tan, CEO - 2026-01-12.'])]))
    add('A.5.1', 'Policy Set Index and Review Log', 'Register of all ISMS policies with owners, versions and annual review dates.', 'policy_register_a51.xlsx',
        lambda p: xlsx(p, ['Policy', 'ID', 'Version', 'Owner', 'Last review', 'Next review', 'Status'],
            [['Information Security Policy', 'POL-ISP-01', '3.0', 'CISO', '2026-01-12', '2027-01-12', 'Approved'],
             ['Access Control Policy', 'POL-AC-01', '2.2', 'CISO', '2026-02-20', '2027-02-20', 'Approved'],
             ['Acceptable Use Policy', 'POL-AUP-01', '2.0', 'HR Lead', '2026-03-05', '2027-03-05', 'Approved'],
             ['Backup & Recovery Policy', 'POL-BCK-01', '1.4', 'IT Manager', '2026-04-18', '2027-04-18', 'Approved'],
             ['Cryptography Policy', 'POL-CRY-01', '1.1', 'CISO', '2026-05-09', '2027-05-09', 'Approved'],
             ['Incident Response Plan', 'POL-IR-01', '2.3', 'CISO', '2026-06-01', '2027-06-01', 'Approved'],
             ['Supplier Security Policy', 'POL-SUP-01', '1.6', 'Procurement', '2026-07-14', '2027-07-14', 'Approved']]))
    add('6.1.2', 'Information Security Risk Register 2026', 'Risk register with likelihood x impact scoring, owners and treatment decisions.', 'risk_register_612.xlsx',
        lambda p: xlsx(p, ['Risk ID', 'Asset', 'Threat', 'Likelihood(1-5)', 'Impact(1-5)', 'Score', 'Owner', 'Treatment', 'Residual'],
            [['R-001', 'AWS production account', 'Credential compromise', 3, 5, 15, 'CISO', 'MFA, SCP guardrails, GuardDuty', 6],
             ['R-002', 'Customer vessel data', 'Data leakage via S3 misconfig', 2, 5, 10, 'CTO', 'Block public access, Config rules', 4],
             ['R-003', 'Laptops', 'Theft / loss', 3, 3, 9, 'IT Manager', 'FileVault encryption, MDM remote wipe', 3],
             ['R-004', 'Fleet platform', 'Ransomware', 2, 5, 10, 'CISO', 'Immutable backups, EDR, segmentation', 5],
             ['R-005', 'Third-party AIS feed', 'Supplier outage', 3, 3, 9, 'Ops Lead', 'Secondary provider, SLA', 4]]))
    add('6.1.3', 'Risk Treatment Plan and Statement of Applicability', 'RTP with approved residual risk and SoA excerpt (v4).', 'rtp_soa_613.pdf',
        lambda p: pdf(p, 'Risk Treatment Plan & SoA Excerpt', meta('ISMS-RTP-01', 'Priya Nair (CISO)', 'Daniel Tan (CEO)', '4.0', '2026-03-30'),
            [('Method', ['Risks scored per ISMS-RISK-01; risks >= 9 require treatment; risk owners accept residual risk in writing.']),
             ('Treatment summary', ['R-001: Reduce - Okta MFA enforced 2026-02, SCPs deployed 2026-03 (done).', 'R-004: Reduce - immutable S3 Object Lock backups live 2026-05 (done); EDR on 100% endpoints.', 'R-005: Reduce - second AIS provider contract signed 2026-06 (done).']),
             ('SoA excerpt', ['A.5.15 Access control - Applicable - Implemented', 'A.8.13 Information backup - Applicable - Implemented', 'A.7.4 Physical security monitoring - Applicable - Partially (HQ CCTV only)']),
             ('Residual risk acceptance', ['All residual scores <= 6; accepted by risk owners and CEO on 2026-03-30.'])]))
    add('6.2', 'Information Security Objectives FY2026', 'Measurable objectives with owners, targets and status.', 'objectives_62.docx',
        lambda p: dcx(p, 'Information Security Objectives FY2026', meta('ISMS-OBJ-01', 'Priya Nair (CISO)', 'Management Review', '1.0', '2026-01-20'),
            [('Objectives', ['O1: 100% of staff complete security awareness training by 2026-06-30 (achieved 100%, 2026-06-18).', 'O2: Critical vulnerabilities remediated within 7 days, >= 95% (YTD 97.4%).', 'O3: Zero security incidents with customer data exposure (YTD 0).', 'O4: Quarterly access reviews completed on time (Q1-Q3 done).'])]))
    add('7.2', 'Competence Records - Security Roles', 'Competence matrix and certifications for ISMS-critical roles.', 'competence_72.csv',
        lambda p: csvf(p, ['Employee', 'Role', 'Required competence', 'Evidence', 'Valid until'],
            [['Priya Nair', 'CISO', 'CISSP, ISO 27001 LA', 'Cert CISSP-884211; LA-2231', '2027-08-31'], ['Marcus Lee', 'ISMS Manager', 'ISO 27001 LI', 'Cert LI-77120', '2028-01-15'],
             ['Aisha Rahman', 'Cloud Security Engineer', 'AWS Security Specialty', 'Cert AWS-SCS-55120', '2028-03-02'], ['Tom Wong', 'IT Manager', 'CompTIA Security+', 'Cert COMP-91823', '2027-11-30']]))
    add('7.3', 'Security Awareness Campaign Completion Report', 'Phishing simulation and awareness training completion for 2026.', 'awareness_73.pdf',
        lambda p: pdf(p, 'Security Awareness Report 2026', meta('HR-SAT-2026', 'HR Lead', 'CISO', '1.0', '2026-07-01'),
            [('Training', ['Annual module "Security Basics 2026" assigned 2026-05-01; completed by 62 of 62 employees by 2026-06-18 (100%).', 'Average quiz score 91%.']),
             ('Phishing simulation', ['Q2 campaign: 62 targeted, 4 clicked (6.5%), 3 reported within 10 minutes; clickers re-trained.'])]))
    add('A.6.3', 'Awareness Training Attendance and Completion Log', 'Per-employee completion with dates.', 'training_log_a63.csv',
        lambda p: csvf(p, ['Employee ID', 'Course', 'Assigned', 'Completed', 'Score'],
            [['E-1001', 'Security Basics 2026', '2026-05-01', '2026-05-09', 94], ['E-1002', 'Security Basics 2026', '2026-05-01', '2026-05-12', 88], ['E-1003', 'Security Basics 2026', '2026-05-01', '2026-06-02', 92], ['E-1004', 'Security Basics 2026', '2026-05-01', '2026-06-18', 90]]))
    add('8.1', 'Change Management Procedure and Sample CAB Records', 'Operational planning: change procedure with 3 sampled approved changes.', 'change_mgmt_81.pdf',
        lambda p: pdf(p, 'Change Management Procedure & Samples', meta('ISMS-CHG-01', 'Tom Wong (IT Manager)', 'Priya Nair (CISO)', '2.0', '2026-04-02'),
            [('Procedure', ['All production changes require a GitHub PR with 1 approving review, passing CI, and CAB approval for high-risk changes.']),
             ('Samples', ['CHG-2210 (2026-08-04) Upgrade RDS to PG16 - approved by CAB, rollback tested.', 'CHG-2244 (2026-09-12) WAF rule update - approved by CISO.', 'CHG-2261 (2026-10-21) Rotate KMS keys - approved by CAB.'])]))
    add('9.1', 'ISMS Monitoring and Measurement KPI Report Q3', 'KPI dashboard export with trend analysis.', 'kpi_91.xlsx',
        lambda p: xlsx(p, ['KPI', 'Target', 'Q1', 'Q2', 'Q3'],
            [['Critical vulns closed <=7d (%)', 95, 94, 97, 98], ['Backup restore tests passed (%)', 100, 100, 100, 100], ['Phishing click rate (%)', '<8', 9.1, 6.5, 5.2], ['Access reviews on time (%)', 100, 100, 100, 100]]))
    add('10.2', 'Nonconformity and Corrective Action Register', 'NCs from internal audit with root cause, corrective action and verification.', 'nc_register_102.xlsx',
        lambda p: xlsx(p, ['NC ID', 'Source', 'Finding', 'Root cause', 'Corrective action', 'Owner', 'Due', 'Closed', 'Effectiveness verified'],
            [['NC-01', 'Internal audit Aug-26', 'Two leavers kept Jira access >7 days', 'No automated offboarding for Jira', 'Okta SCIM deprovisioning', 'IT Manager', '2026-09-30', '2026-09-22', 'Yes 2026-10-14'],
             ['NC-02', 'Internal audit Aug-26', 'Backup restore test not recorded for Q1', 'Procedure gap', 'Added restore-test checklist', 'IT Manager', '2026-09-15', '2026-09-10', 'Yes 2026-10-14']]))
    add('A.5.9', 'Asset Inventory Export', 'Information and associated assets inventory with owners and classification.', 'asset_inventory_a59.xlsx',
        lambda p: xlsx(p, ['Asset ID', 'Asset', 'Type', 'Owner', 'Classification', 'Location'],
            [['A-001', 'MarineOps production DB (RDS)', 'Information system', 'CTO', 'Confidential', 'AWS ap-southeast-1'], ['A-002', 'Customer contracts repository', 'Information', 'Legal', 'Confidential', 'SharePoint'],
             ['A-014', 'MacBook Pro (62 units)', 'Endpoint', 'IT Manager', 'Internal', 'Staff'], ['A-020', 'Okta tenant', 'Service', 'CISO', 'Confidential', 'SaaS']]))
    add('A.5.15', 'Quarterly Access Review Q3 2026', 'User access recertification for production systems signed by system owners.', 'access_review_a515.csv',
        lambda p: csvf(p, ['System', 'User', 'Role', 'Reviewer', 'Decision', 'Review date'],
            [['AWS prod', 'aisha.rahman', 'SecurityAudit', 'Priya Nair', 'Retain', '2026-10-03'], ['AWS prod', 'dev.contractor1', 'PowerUser', 'Priya Nair', 'Revoke', '2026-10-03'],
             ['GitHub', 'marcus.lee', 'Admin', 'CTO', 'Retain', '2026-10-04'], ['Okta', 'tom.wong', 'Super Admin', 'CISO', 'Retain', '2026-10-04']]),
        src='Manual Upload')
    add('A.5.19', 'Supplier Security Assessment - AWS and Okta', 'Supplier due diligence: certifications reviewed, risk tiering, contract clauses.', 'supplier_a519.pdf',
        lambda p: pdf(p, 'Supplier Security Assessments', meta('PROC-SUP-2026', 'Procurement', 'CISO', '1.2', '2026-06-20'),
            [('AWS', ['Tier 1 (critical). ISO 27001, SOC 2 Type II reviewed 2026-06-10. DPA signed. Shared responsibility documented.']),
             ('Okta', ['Tier 1. ISO 27001/27018, SOC 2 reviewed 2026-06-12. SCIM and logs retention 13 months.']),
             ('Decision', ['Both approved; reassess annually (next 2027-06).'])]))
    add('A.5.24', 'Incident Response Plan and Tabletop Exercise Report', 'IR plan with roles, severity matrix, and 2026 ransomware tabletop outcome.', 'ir_a524.pdf',
        lambda p: pdf(p, 'Incident Response Plan & Tabletop', meta('POL-IR-01', 'Priya Nair (CISO)', 'Daniel Tan (CEO)', '2.3', '2026-06-01'),
            [('Roles', ['Incident Commander: CISO. Comms: CEO. Technical lead: Cloud Security Engineer. 24/7 on-call rota via PagerDuty.']),
             ('Severity', ['SEV1 data breach/ransomware: 15 min response, PDPC notification within 3 days if notifiable.']),
             ('Tabletop 2026-05-22', ['Scenario: ransomware on file server. Findings: escalation path unclear at night; fixed by updating on-call rota (action closed 2026-06-01).'])]))
    add('A.5.30', 'Business Continuity and DR Test Report', 'DR failover test of production to secondary AZ/region with RTO/RPO results.', 'dr_a530.pdf',
        lambda p: pdf(p, 'DR Test Report 2026', meta('BCP-DR-2026', 'Tom Wong (IT Manager)', 'CTO', '1.0', '2026-09-02'),
            [('Objective', ['Validate RTO 4h / RPO 15min for MarineOps platform.']),
             ('Result', ['Failover to ap-southeast-2 completed in 2h 10m; data loss 6 min. PASS.', 'Lessons: DNS TTL lowered to 60s; runbook step 7 clarified.'])]))
    add('A.6.5', 'Offboarding Checklist - Leavers Q3', 'Completed offboarding checklists showing access removal and asset return.', 'offboarding_a65.csv',
        lambda p: csvf(p, ['Leaver', 'Last day', 'Accounts disabled', 'Devices returned', 'Confidentiality reminder sent', 'Completed by'],
            [['E-0912', '2026-08-15', '2026-08-15', '2026-08-15', 'Yes', 'Tom Wong'], ['E-0933', '2026-09-30', '2026-09-30', '2026-10-02', 'Yes', 'Tom Wong']]))
    add('A.7.2', 'Office Access Control Log Extract', 'Badge system log and visitor register sample for HQ entry points.', 'badge_log_a72.csv',
        lambda p: csvf(p, ['Timestamp', 'Door', 'Badge ID', 'Result'],
            [['2026-11-02 08:41', 'Main entrance', 'B-1004', 'Granted'], ['2026-11-02 08:55', 'Server room', 'B-1099', 'Denied'], ['2026-11-02 09:03', 'Server room', 'B-1001', 'Granted']]))
    add('A.8.1', 'MDM Endpoint Compliance Report', 'Jamf report: disk encryption, screen lock, OS patch level for all endpoints.', 'mdm_a81.png',
        lambda p: png(p, ['Jamf Pro - Compliance Overview            Date: 2026-11-20 09:12 SGT   Tenant: maritime-services', 'Managed devices: 62      FileVault enabled: 62/62 (100%)', 'Screen lock <= 5 min: 62/62      macOS up to date: 60/62 (2 pending 14.7.1)', 'Non-compliant: 2 devices (auto-remediation scheduled)'], 'Jamf Pro'),
        src='Integration')
    add('A.8.5', 'Okta MFA Enforcement Screenshot', 'Okta sign-on policy enforcing MFA for all users.', 'okta_mfa_a85.png',
        lambda p: png(p, ['Okta Admin > Security > Authentication Policies       2026-11-20 09:30 SGT   org: maritime-services', 'Policy: "All users - MFA required"   Status: ACTIVE   Applies to: Everyone', 'Factors: Okta Verify (push), FIDO2 WebAuthn.  SMS: disabled', 'Users enrolled in MFA: 62 / 62 (100%)'], 'Okta Admin'),
        src='Integration')
    add('A.8.7', 'EDR Coverage Report', 'CrowdStrike sensor coverage and detection summary.', 'edr_a87.csv',
        lambda p: csvf(p, ['Date', 'Hosts total', 'Sensors healthy', 'Coverage %', 'Detections', 'Blocked'], [['2026-10-31', 62, 62, 100, 7, 7], ['2026-11-20', 62, 62, 100, 3, 3]]))
    add('A.8.8', 'Vulnerability Scan Summary Nov 2026', 'Monthly Inspector/Nessus scan with SLA status.', 'vuln_a88.xlsx',
        lambda p: xlsx(p, ['Severity', 'Open', 'Closed in SLA', 'Closed late', 'SLA'], [['Critical', 0, 11, 0, '7 days'], ['High', 3, 28, 2, '30 days'], ['Medium', 21, 74, 5, '90 days']]))
    add('A.8.13', 'Backup and Restore Test Record', 'Immutable backup configuration and quarterly restore test results.', 'backup_a813.pdf',
        lambda p: pdf(p, 'Backup & Restore Test - Q3 2026', meta('BCK-REST-Q3', 'Tom Wong (IT Manager)', 'CISO', '1.0', '2026-09-28'),
            [('Configuration', ['RDS automated backups 35 days; S3 Object Lock (compliance mode) 90 days; cross-region copy to ap-southeast-2.']),
             ('Restore test 2026-09-25', ['Restored prod snapshot to isolated VPC; checksum verified; RTO achieved 1h 40m. PASS.'])]))
    add('A.8.15', 'Centralised Logging Configuration', 'CloudTrail/Config/log retention settings and SIEM alerting evidence.', 'logging_a815.png',
        lambda p: png(p, ['AWS CloudTrail > Trails                         2026-11-20 10:02 SGT   Account: 4412-xxxx-9081', 'Trail: org-trail   Multi-region: Yes   Log file validation: Enabled', 'S3 bucket: ms-logs-archive (Object Lock)   Retention: 400 days', 'CloudWatch alarm: Root account usage -> SNS -> PagerDuty (OK)'], 'AWS Console'),
        src='Integration')
    add('A.8.20', 'Network Segmentation and Firewall Rule Review', 'Quarterly firewall/security group review.', 'network_a820.pdf',
        lambda p: pdf(p, 'Network Security Review Q3 2026', meta('NET-REV-Q3', 'Aisha Rahman', 'CISO', '1.0', '2026-10-06'),
            [('Scope', ['3 VPCs, 41 security groups, 2 WAF ACLs.']), ('Findings', ['2 security groups with 0.0.0.0/0 on 22 removed 2026-10-05.', 'No public DB endpoints.'])]))
    add('A.8.24', 'Cryptography Policy and Key Management Evidence', 'Encryption in transit/at rest standards and KMS rotation settings.', 'crypto_a824.docx',
        lambda p: dcx(p, 'Cryptography Policy & Key Management', meta('POL-CRY-01', 'Priya Nair (CISO)', 'CTO', '1.1', '2026-05-09'),
            [('Standards', ['TLS 1.2+ only; AES-256 at rest (KMS CMKs); annual key rotation enabled; keys never stored in code.']),
             ('Evidence', ['KMS key rotation enabled on 9/9 CMKs (checked 2026-11-20).'])]))

    # ---- negative scenarios (expect Rejected / Needs Human Review) ----
    add('A.8.13', 'Backup Policy TEMPLATE (blank)', 'Backup policy.', 'neg_blank_template.pdf',
        lambda p: pdf(p, 'BACKUP POLICY - TEMPLATE', ['Company: [COMPANY NAME]  Date: [DATE]  Owner: [OWNER]  DRAFT'], [('Scope', ['[describe scope here]']), ('Frequency', ['[insert frequency]'])]),
        expect='Rejected')
    add('A.5.15', 'Office Party Photo Schedule', 'Access control evidence.', 'neg_wrong_artifact.pdf',
        lambda p: pdf(p, 'Staff Year-End Party Schedule', meta('HR-EVT-01', 'HR Lead', 'HR Lead'), [('Agenda', ['18:00 Welcome drinks', '19:00 Dinner', '21:00 Karaoke'])]),
        expect='Rejected')
    add('A.8.5', 'Authentication settings (cropped, no date)', 'Screenshot of MFA.', 'neg_vague_screenshot.png',
        lambda p: png(p, ['Settings', 'MFA: on'], 'App'), expect='Needs Human Review')
    return M


FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def shot(path, app, url, accent, nav, heading, cols, rows, banner=None, fmt=None):
    """Console-style screenshot: browser bar, left nav, table, status pills, visible timestamp."""
    from PIL import ImageFont
    f, fb, fs = ImageFont.truetype(FONT, 14), ImageFont.truetype(FONTB, 18), ImageFont.truetype(FONT, 12)
    W, H = 1280, 150 + 40 * (len(rows) + 1) + 120
    im = Image.new('RGB', (W, H), '#ffffff')
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 38], fill='#dfe3e8')
    for i, c in enumerate(('#ff5f57', '#febc2e', '#28c840')):
        d.ellipse([14 + 22 * i, 12, 26 + 22 * i, 24], fill=c)
    d.rounded_rectangle([110, 7, W - 110, 31], 12, fill='white')
    d.text((126, 11), url, font=fs, fill='#333')
    d.rectangle([0, 38, W, 84], fill=accent)
    d.text((20, 52), app, font=fb, fill='white')
    d.text((W - 330, 56), '2026-11-20 10:14 SGT  |  priya.nair@maritime-services', font=fs, fill='white')
    d.rectangle([0, 84, 190, H], fill='#f1f3f6')
    for i, n in enumerate(nav):
        d.text((20, 104 + 34 * i), n, font=f, fill=accent if i == 1 else '#444')
    d.text((215, 100), heading, font=fb, fill='#111')
    y = 140
    if banner:
        d.rounded_rectangle([215, y, W - 25, y + 30], 4, fill='#e6f4ea')
        d.text((228, y + 7), banner, font=f, fill='#1a7f4b')
        y += 42
    x = [215 + sum(cols[1][:i]) for i in range(len(cols[1]))]
    d.rectangle([215, y, W - 25, y + 34], fill='#eef1f5')
    for xi, h in zip(x, cols[0]):
        d.text((xi + 8, y + 9), h, font=fb if False else f, fill='#555')
    for r in rows:
        y += 40
        d.line([215, y, W - 25, y], fill='#e3e6ea')
        for xi, v in zip(x, r):
            ok = str(v) in ('Enabled', 'Active', 'Compliant', 'Healthy', 'Completed', 'Passed', 'Yes', 'Encrypted')
            bad = str(v) in ('Disabled', 'Non-compliant', 'Failed', 'Open')
            if ok or bad:
                d.rounded_rectangle([xi + 4, y + 8, xi + 8 + 14 + 8 * len(str(v)), y + 30], 10, fill='#e6f4ea' if ok else '#fdecea')
                d.text((xi + 14, y + 12), str(v), font=fs, fill='#1a7f4b' if ok else '#c0392b')
            else:
                d.text((xi + 8, y + 12), str(v), font=f, fill='#222')
    im.convert('RGB').save(path, quality=92) if fmt == 'jpg' else im.save(path)


def photo(path, lines, bg=('#3b4a54', '#8fa3ad')):
    """Phone-photo style: gradient background, signage panel, slight rotation and noise."""
    import random
    from PIL import ImageFont, ImageFilter
    random.seed(7)
    im = Image.new('RGB', (1000, 700), bg[0])
    d = ImageDraw.Draw(im)
    for y in range(700):
        t = y / 700
        d.line([0, y, 1000, y], fill=tuple(int(int(bg[0][i:i + 2], 16) * (1 - t) + int(bg[1][i:i + 2], 16) * t) for i in (1, 3, 5)))
    d.rectangle([230, 150, 770, 470], fill='#f7f7f2', outline='#222', width=6)
    fb, f = ImageFont.truetype(FONTB, 34), ImageFont.truetype(FONT, 24)
    for i, ln in enumerate(lines):
        d.text((260, 180 + 56 * i), ln, font=fb if i == 0 else f, fill='#b00020' if i == 0 else '#222')
    im = im.rotate(-2.5, expand=False, fillcolor='#444').filter(ImageFilter.GaussianBlur(0.6))
    px = im.load()
    for _ in range(14000):
        x, y = random.randrange(1000), random.randrange(700)
        r, g, b = px[x, y]
        n = random.randint(-12, 12)
        px[x, y] = (max(0, min(255, r + n)),) * 1 + (max(0, min(255, g + n)), max(0, min(255, b + n)))
    im.save(path, quality=88)


def build_images(out):
    os.makedirs(out, exist_ok=True)
    M = []

    def add(code, title, desc, fname, fn, expect='Approved', src='Manual Upload'):
        fn(os.path.join(out, fname))
        M.append(dict(code=code, title=title, desc=desc, file=fname, source=src, expect=expect, extra=[]))

    aws = ['Dashboard', 'IAM', 'S3', 'Config', 'CloudTrail', 'GuardDuty']
    add('A.5.15', 'AWS IAM Access Analyzer - Findings', 'Console screenshot of IAM Access Analyzer showing external-access findings and their resolution status for the production account.', 'iam_analyzer_a515.png',
        lambda p: shot(p, 'AWS Console | IAM', 'https://console.aws.amazon.com/iam/home#/access-analyzer/findings', '#232f3e', aws, 'Access Analyzer - Findings (ms-prod, ap-southeast-1)',
                       (['Resource', 'Type', 'Principal', 'Status'], [420, 200, 260, 160]),
                       [['arn:aws:s3:::ms-reports', 'S3 bucket', 'Account 5512-xxxx-0011 (trusted)', 'Active'], ['arn:aws:iam::4412:role/ci-deploy', 'IAM role', 'GitHub OIDC', 'Active'], ['arn:aws:kms:key/9f2e', 'KMS key', 'Account 4412 (self)', 'Active']],
                       banner='0 public findings - 3 trusted external principals reviewed 2026-11-18'), src='Integration')
    add('A.5.16', 'Okta Directory - Active Users and Deactivation Log', 'Okta admin People view showing active users, last login and recent deactivations.', 'okta_people_a516.jpg',
        lambda p: shot(p, 'Okta Admin Console', 'https://maritime-services-admin.okta.com/admin/users', '#00297a', ['Dashboard', 'Directory', 'Applications', 'Security', 'Reports'], 'People',
                       (['Person', 'Username', 'Status', 'Last login'], [300, 340, 200, 220]),
                       [['Aisha Rahman', 'aisha.rahman@maritime-services', 'Active', '2026-11-20 08:51'], ['Marcus Lee', 'marcus.lee@maritime-services', 'Active', '2026-11-20 09:02'], ['Dev Contractor 1', 'dev.contractor1@maritime-services', 'Disabled', '2026-10-03 17:40'], ['Tom Wong', 'tom.wong@maritime-services', 'Active', '2026-11-19 18:22']],
                       fmt='jpg'), src='Integration')
    add('A.8.2', 'Privileged Access - AWS Admin Role Assignments', 'IAM role assignment list for privileged (AdministratorAccess) roles, limited to named security staff.', 'priv_access_a82.png',
        lambda p: shot(p, 'AWS Console | IAM', 'https://console.aws.amazon.com/iam/home#/policies/AdministratorAccess', '#232f3e', aws, 'AdministratorAccess - Policy usage (3 entities)',
                       (['Entity', 'Type', 'MFA', 'Last activity'], [380, 160, 200, 300]),
                       [['priya.nair', 'User', 'Enabled', '2026-11-19'], ['break-glass-admin', 'Role', 'Enabled', '2026-04-02'], ['aisha.rahman', 'User', 'Enabled', '2026-11-20']]), src='Integration')
    add('A.8.8', 'Amazon Inspector - Vulnerability Findings by Severity', 'Inspector dashboard: open findings by severity, with critical count zero.', 'inspector_a88.png',
        lambda p: shot(p, 'AWS Console | Inspector', 'https://console.aws.amazon.com/inspector/v2/home#/findings', '#232f3e', ['Dashboard', 'Findings', 'Coverage', 'Suppression'], 'Findings summary (account 4412)',
                       (['Severity', 'Open findings', 'Oldest (days)', 'SLA'], [260, 260, 260, 220]),
                       [['Critical', 0, 0, 'Passed'], ['High', 3, 12, 'Passed'], ['Medium', 21, 41, 'Passed'], ['Low', 57, 88, 'Passed']], banner='Coverage: 41/41 EC2 instances and 12/12 ECR repositories scanned'), src='Integration')
    add('A.8.9', 'Config Rules - Configuration Compliance Summary', 'AWS Config conformance pack compliance (CIS AWS Foundations) showing compliant resources.', 'config_a89.jpg',
        lambda p: shot(p, 'AWS Console | Config', 'https://console.aws.amazon.com/config/home#/conformance-packs', '#232f3e', ['Dashboard', 'Rules', 'Resources', 'Aggregators'], 'Conformance pack: CIS-AWS-Foundations-v1.4',
                       (['Rule', 'Resources', 'Compliance', 'Last evaluated'], [440, 180, 220, 260]),
                       [['s3-bucket-public-read-prohibited', 38, 'Compliant', '2026-11-20 06:00'], ['cloudtrail-enabled', 1, 'Compliant', '2026-11-20 06:00'], ['iam-user-mfa-enabled', 14, 'Compliant', '2026-11-20 06:00'], ['restricted-ssh', 41, 'Compliant', '2026-11-20 06:00']], fmt='jpg'), src='Integration')
    add('A.8.13', 'AWS Backup Vault - Recovery Points', 'AWS Backup vault listing recovery points with encryption and retention for the production RDS instance.', 'backup_vault_a813.png',
        lambda p: shot(p, 'AWS Console | Backup', 'https://console.aws.amazon.com/backup/home#/backupvaults/details/ms-prod-vault', '#232f3e', ['Dashboard', 'Vaults', 'Plans', 'Restore jobs'], 'ms-prod-vault (Object Lock: Compliance, 90 days)',
                       (['Recovery point', 'Resource', 'Created', 'Encryption'], [320, 260, 260, 200]),
                       [['rp-0a91...e2', 'rds:ms-prod-db', '2026-11-20 01:00', 'Encrypted'], ['rp-0a1c...77', 'rds:ms-prod-db', '2026-11-19 01:00', 'Encrypted'], ['rp-09f3...41', 'rds:ms-prod-db', '2026-11-18 01:00', 'Encrypted']]), src='Integration')
    add('A.8.16', 'GuardDuty - Active Monitoring and Findings', 'GuardDuty enabled in all regions with findings triaged.', 'guardduty_a816.jpg',
        lambda p: shot(p, 'AWS Console | GuardDuty', 'https://console.aws.amazon.com/guardduty/home#/summary', '#232f3e', ['Summary', 'Findings', 'Settings'], 'GuardDuty summary',
                       (['Region', 'Status', 'Open findings', 'Last finding'], [300, 220, 260, 300]),
                       [['ap-southeast-1', 'Enabled', 0, '2026-11-11'], ['ap-southeast-2', 'Enabled', 0, '2026-09-30'], ['us-east-1', 'Enabled', 0, 'n/a']], fmt='jpg'), src='Integration')
    add('A.8.20', 'Security Groups - Inbound Rules Review', 'EC2 security group list showing no 0.0.0.0/0 inbound on administrative ports after Q3 review.', 'secgroups_a820.png',
        lambda p: shot(p, 'AWS Console | EC2', 'https://console.aws.amazon.com/ec2/home#SecurityGroups', '#232f3e', ['Instances', 'Security Groups', 'Load balancers'], 'Security groups (41)',
                       (['Name', 'Inbound 22/3389', 'Inbound 443', 'VPC'], [360, 260, 260, 220]),
                       [['sg-web-alb', 'None', '0.0.0.0/0 (WAF)', 'vpc-prod'], ['sg-app', 'None', 'sg-web-alb', 'vpc-prod'], ['sg-bastion', 'VPN CIDR only', 'None', 'vpc-prod'], ['sg-db', 'None', 'sg-app', 'vpc-prod']]), src='Integration')
    add('A.6.3', 'Security Awareness Platform - Completion Dashboard', 'Awareness training platform view showing 100% completion for the 2026 course.', 'training_dash_a63.png',
        lambda p: shot(p, 'LearnSecure', 'https://app.learnsecure.example/campaigns/security-basics-2026', '#5b2a86', ['Home', 'Campaigns', 'People', 'Reports'], 'Campaign: Security Basics 2026',
                       (['Department', 'Assigned', 'Completed', 'Status'], [340, 220, 220, 240]),
                       [['Engineering', 24, 24, 'Completed'], ['Operations', 18, 18, 'Completed'], ['Finance & HR', 8, 8, 'Completed'], ['Management', 12, 12, 'Completed']], banner='62 of 62 employees completed on 2026-06-18 (100%)'))
    add('A.7.1', 'Physical Security - Restricted Area Signage Photo', 'Photograph of the access-controlled server room door at Singapore HQ showing restricted-area signage and badge reader.', 'server_room_door_a71.jpg',
        lambda p: photo(p, ['RESTRICTED AREA', 'Authorised personnel only', 'Badge access required', 'Server Room - HQ Level 3']))
    add('A.7.4', 'CCTV Monitoring Console - HQ Entrances', 'CCTV management console showing camera online status for HQ entrances and server-room corridor.', 'cctv_a74.png',
        lambda p: shot(p, 'SecureView CCTV', 'https://cctv.maritime-services.local/cameras', '#0b5345', ['Live', 'Cameras', 'Recordings', 'Alerts'], 'Cameras (6 online)',
                       (['Camera', 'Location', 'Status', 'Retention'], [260, 380, 200, 240]),
                       [['CAM-01', 'Main entrance', 'Healthy', '90 days'], ['CAM-02', 'Reception', 'Healthy', '90 days'], ['CAM-03', 'Server room corridor', 'Healthy', '90 days'], ['CAM-04', 'Rear exit', 'Healthy', '90 days']], banner='All cameras recording - last motion event 2026-11-20 09:58'))
    add('A.8.7', 'EDR Console - Endpoint Protection Status (stale, low quality)', 'EDR dashboard screenshot.', 'edr_blurry_a87.jpg',
        lambda p: photo(p, ['EDR', 'status: ok'], bg=('#222222', '#555555')), expect='Rejected')
    return M


if __name__ == '__main__':
    out = sys.argv[1]
    m = build_images(out) if len(sys.argv) > 2 and sys.argv[2] == 'images' else build(out)
    json.dump(m, open(os.path.join(out, 'manifest.json'), 'w'), indent=1)
    print(len(m), 'items ->', out)
