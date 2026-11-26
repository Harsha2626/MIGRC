"""Evidence set p3: ISO 27001:2022 controls A.5.33 .. A.8.4 (2 documents each) for Maritime Services Pte. Ltd."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from gen_iso_evidence import pdf, dcx, xlsx, csvf, png, shot, photo, meta  # noqa: E402,F401

PN, DT, TW, MK, AR = 'Priya Nair (CISO)', 'Daniel Tan (CEO)', 'Tom Wong (IT Manager)', 'Marcus Lee (ISMS Manager)', 'Aisha Rahman (Cloud Security Eng.)'


def doc(fmt, title, did, owner, appr, ver, date, secs):
    f = pdf if fmt == 'pdf' else dcx
    return lambda p: f(p, title, meta(did, owner, appr, ver, date), secs)


def tab(fmt, header, rows):
    return lambda p: (xlsx if fmt == 'xlsx' else csvf)(p, header, rows)


def S(app, url, accent, nav, heading, cols, rows, banner=None, fmt=None):
    return lambda p: shot(p, app, url, accent, nav, heading, cols, rows, banner, fmt)


def build(out):
    os.makedirs(out, exist_ok=True)
    M = []

    def add(code, desc, kind, title, fmt, fn, expect, src='Manual Upload'):
        fname = f"{code.replace('.', '_')}_{kind}.{fmt}"
        fn(os.path.join(out, fname))
        M.append(dict(code=code, title=title, desc=desc, file=fname, source=src, expect=expect, extra=[]))

    def pair(code, desc, pt, pfmt, pfn, ft, ffmt, ffn, src='Manual Upload'):
        add(code, desc, 'pass', pt, pfmt, pfn, 'Approved', src)
        add(code, desc, 'fail', ft, ffmt, ffn, 'Rejected', src)

    # ---- A.5.33
    pair('A.5.33', 'Records are protected from loss, destruction, falsification, unauthorized access and release.',
         'Records Protection and Retention Schedule 2026', 'pdf',
         doc('pdf', 'Records Protection and Retention Schedule', 'ISMS-REC-01', PN, DT, '2.0', '2026-03-12', [
             ('Record classes and retention', ['Financial records: 7 years (Singapore Companies Act). Customer contracts: 6 years after termination. Vessel telemetry logs: 24 months. HR files: 5 years after exit. Audit logs (CloudTrail): 13 months online, 7 years in archive.']),
             ('Protection controls', ['Contracts and finance exports stored in S3 bucket ms-records-prod (ap-southeast-1) with Object Lock in compliance mode (retention 7y), versioning and SSE-KMS (key alias/ms-records).', 'Access limited to the Records Custodian group in Okta (11 members); quarterly review last done 2026-09-30.', 'Integrity: SHA-256 manifest generated nightly and stored in a separate account (audit-vault, 291044118302).']),
             ('Evidence', ['Restore exercise of record set REC-0914 on 2026-08-19 succeeded in 14 minutes; no deletions of locked objects recorded by CloudTrail in the period.', 'Next review: 2027-03.'])]),
         'Document Retention Register (2024 edition)', 'xlsx',
         tab('xlsx', ['Record type', 'Owner', 'Retention', 'Location', 'Last reviewed'],
             [['Customer contracts', 'Legal', '6 years', 'SharePoint /Legal', '2024-03-04'], ['Invoices', 'Finance', '7 years', 'Xero export', '2024-03-04'],
              ['HR personnel files', 'HR Lead', '5 years', 'HR cabinet', '2024-03-04'], ['Vessel telemetry', 'CTO', '24 months', 'S3 ms-telemetry', '2024-03-04'], ['Audit logs', 'IT Manager', '12 months', 'CloudWatch', '2024-03-04']]))
    # ---- A.5.34
    pair('A.5.34', 'Requirements for privacy and PII protection per applicable laws are identified and met.',
         'PDPA Compliance Register and Data Inventory', 'docx',
         doc('docx', 'PDPA Compliance Register and Personal Data Inventory', 'PRV-REG-01', 'Lin Mei Ling (Data Protection Officer)', PN, '1.5', '2026-06-22', [
             ('Legal requirements', ['Singapore Personal Data Protection Act 2012 (PDPA) - Consent, Purpose Limitation, Protection, Retention, Transfer, Access, Breach Notification. DPO registered with PDPC on 2025-12-03 (ACRA filing DPO-2025-4471).']),
             ('Personal data inventory', ['1. Crew manifests (name, passport no., rank) - 14 customer vessels - basis: contract - retention 24 months - S3 SSE-KMS.', '2. Employee HR data (NRIC, bank details) - 62 staff - basis: employment - retention 5 years after exit.', '3. Customer user accounts (email, phone) - 410 users - Okta CIC, encrypted at rest.']),
             ('Controls and results', ['DSAR handled: 3 requests in 2026, all closed within 30 days (DSAR-2026-001 to 003).', 'Transfer assessment for Irish-hosted support tool completed 2026-04-15 (contractual clauses signed).', 'PIA completed for the new crew-rotation module on 2026-08-02.'])]),
         'Privacy Statement', 'pdf',
         doc('pdf', 'Privacy Statement', 'WEB-PRV-1', 'Marketing', 'Marketing', '1.0', '2026-05-02', [
             ('Our commitment', ['We take privacy very seriously and respect your personal information. We only collect data that is necessary and we handle it with care.', 'We may share data with trusted partners where appropriate. We use reasonable security measures to protect information.', 'For more information about how we use data, please contact us.'])]))
    # ---- A.5.35
    pair('A.5.35', 'The organization approach to managing information security is independently reviewed at planned intervals.',
         'Independent ISMS Review Report - Harbourline Assurance', 'pdf',
         doc('pdf', 'Independent Review of the Information Security Programme', 'EXT-REV-2026-01', 'Harbourline Assurance LLP (external)', DT, '1.0', '2026-09-18', [
             ('Engagement', ['Independent review performed 2026-08-24 to 2026-09-04 by Harbourline Assurance LLP (lead reviewer: Grace Ong, CISA, CISSP). The reviewers have no role in operating the ISMS.']),
             ('Scope and method', ['ISMS scope per ISMS-SCOPE-01; 41 controls examined; interviews with 9 staff; technical walkthrough of AWS and Okta configuration.']),
             ('Results', ['3 minor nonconformities: NC-1 vendor reviews late for 2 suppliers; NC-2 incomplete laptop disposal record; NC-3 DR exercise evidence not signed. 6 observations.', 'Management response and corrective actions with due dates (all by 2026-12-15) approved by CEO on 2026-09-25.']),
             ('Sign-off', ['Reviewed and signed: Grace Ong (Harbourline), Daniel Tan (CEO).'])]),
         'ISMS Self-Assessment Review', 'docx',
         doc('docx', 'ISMS Review by Security Team', 'ISMS-SAR-02', PN, PN, '1.0', '2026-10-01', [
             ('Review', ['This review of the ISMS was performed by the CISO and the ISMS Manager, who also designed and operate the controls assessed.', 'We reviewed the policies and concluded that the ISMS is operating effectively.']),
             ('Note', ['No external or independent reviewer was engaged for this period. Approval: Priya Nair (CISO).'])]))
    # ---- A.5.36
    pair('A.5.36', 'Compliance with the organization policies, rules and standards is regularly reviewed.',
         'Quarterly Policy Compliance Check Log 2026', 'xlsx',
         tab('xlsx', ['Check ID', 'Date', 'Policy', 'Method', 'Records reviewed', 'Result', 'Reviewer', 'Actions'],
             [['PC-Q1-01', '2026-03-27', 'Access Control POL-AC-01', 'Okta access export vs HR list', '62 users', 'Compliant', 'Marcus Lee', 'None'],
              ['PC-Q1-02', '2026-03-27', 'Acceptable Use POL-AUP-01', 'Jamf app inventory', '58 laptops', '2 deviations', 'Marcus Lee', 'Apps removed 2026-04-02'],
              ['PC-Q2-01', '2026-06-26', 'Backup POL-BCK-01', 'AWS Backup report', '14 plans', 'Compliant', 'Tom Wong', 'None'],
              ['PC-Q2-02', '2026-06-26', 'Cryptography POL-CRY-01', 'S3/RDS encryption scan', '37 resources', 'Compliant', 'Aisha Rahman', 'None'],
              ['PC-Q3-01', '2026-09-25', 'Incident Response POL-IR-01', 'Ticket review', '8 incidents', 'Compliant', 'Priya Nair', 'None'],
              ['PC-Q3-02', '2026-09-25', 'Supplier POL-SUP-01', 'Vendor file review', '12 vendors', '2 late reviews', 'Priya Nair', 'Closed 2026-10-20']]),
         'Policy Compliance Check Results', 'csv',
         tab('csv', ['Check', 'Policy', 'Date', 'Result', 'Status', 'Owner'],
             [['PC-01', 'Access Control', '2026-06-10', 'Non-compliant: 7 leavers still active', 'Open', 'Unassigned'], ['PC-02', 'Backup', '2026-06-10', 'Non-compliant: 3 DBs unprotected', 'Open', 'Unassigned'],
              ['PC-03', 'Acceptable Use', '2026-06-10', 'Non-compliant: shadow IT found', 'Open', 'Unassigned'], ['PC-04', 'Cryptography', '2026-06-10', 'Non-compliant: 5 unencrypted volumes', 'Open', 'Unassigned'],
              ['PC-05', 'Supplier', '2026-06-10', 'Non-compliant: no reviews done', 'Open', 'Unassigned']]))
    # ---- A.5.37
    pair('A.5.37', 'Operating procedures for information processing facilities are documented and available.',
         'Production Operations Runbook - Deployment and Backup', 'pdf',
         doc('pdf', 'Production Operations Runbook: Deployment and Backup', 'OPS-RB-03', TW, PN, '3.1', '2026-05-20', [
             ('Deployment procedure', ['1. Merge approved PR (1 review + green CI) to main in GitHub. 2. GitHub Actions builds image and pushes to ECR (ms-fleet-api). 3. Deploy to staging, run smoke suite (42 checks). 4. Production rollout via ECS blue/green, 10% canary for 15 minutes. 5. Rollback: re-point listener to previous task set; target < 10 minutes.']),
             ('Backup procedure', ['RDS automated snapshots daily 02:00 SGT, retention 35 days; weekly copy to ap-southeast-2. Monitoring: AWS Backup alarm to #ops-alerts; if the job errors on-call engineer reruns the job and raises a ticket.', 'Restore drill quarterly; last executed 2026-08-19 (RTO 42 min, RPO 24 h).']),
             ('Access and distribution', ['Stored in Confluence space OPS (read: all engineers; edit: IT team). Procedure review annually; reviewed 2026-05-20.'])]),
         'Standard Operating Procedure - Server Maintenance', 'docx',
         doc('docx', 'Standard Operating Procedure - Server Maintenance', 'SOP-[number]', '[Owner name]', '[Approver name]', '[version]', '[dd/mm/yyyy]', [
             ('Purpose', ['[Describe the purpose of this procedure]']), ('Scope', ['[Systems covered]']),
             ('Steps', ['1. [Step one]', '2. [Step two]', '3. [Step three]']), ('Responsibilities', ['[Insert roles]']), ('Approval', ['Signature: ____________  Date: ____________'])]))
    # ---- A.6.1
    pair('A.6.1', 'Background verification checks on all candidates are carried out prior to joining, proportionate to risk.',
         'Pre-Employment Screening Log 2026', 'csv',
         tab('csv', ['Candidate ID', 'Role', 'Offer date', 'Checks performed', 'Provider ref', 'Result', 'Cleared date', 'Approved by'],
             [['C-2601', 'Backend Engineer', '2026-01-14', 'ID, education, employment x2, criminal record', 'VF-88213', 'Clear', '2026-01-23', 'HR Lead'],
              ['C-2602', 'Cloud Security Engineer', '2026-02-03', 'ID, education, employment x2, criminal record', 'VF-88540', 'Clear', '2026-02-12', 'CISO'],
              ['C-2603', 'Support Analyst', '2026-03-09', 'ID, education, employment', 'VF-89102', 'Clear', '2026-03-16', 'HR Lead'],
              ['C-2604', 'Fleet Ops Lead', '2026-05-18', 'ID, education, employment x2, credit check', 'VF-90377', 'Clear', '2026-05-29', 'CISO'],
              ['C-2605', 'DevOps Engineer', '2026-08-03', 'ID, education, employment x2, criminal record', 'VF-91450', 'Clear', '2026-08-12', 'CISO']]),
         'Background Check Vendor Agreement', 'pdf',
         doc('pdf', 'Background Verification Services Agreement', 'CON-HR-07', 'HR Lead', 'Daniel Tan (CEO)', '1.0', '2024-07-01', [
             ('Term', ['Verifile Pte Ltd will provide employment background screening services to Maritime Services Pte. Ltd. from 2024-07-01 to 2025-06-30.']),
             ('Services', ['Identity verification, education verification, previous employer checks, criminal record checks (with candidate consent).']),
             ('Renewal', ['This agreement expired on 2025-06-30 and has not been renewed as at the date of this copy.'])]))
    # ---- A.6.2
    pair('A.6.2', 'Employment agreements state personnel and the organization responsibilities for information security.',
         'Employment Contract - Security Clauses and Signed Acknowledgement', 'pdf',
         doc('pdf', 'Employment Agreement - Information Security Terms (executed)', 'HR-EMP-TPL-4', 'HR Lead', DT, '4.0', '2026-01-08', [
             ('Clause 12 Information security', ['12.1 The Employee shall comply with the Information Security Policy (POL-ISP-01) and Acceptable Use Policy (POL-AUP-01).', '12.2 The Employee shall keep confidential all customer, vessel and company information during and after employment.', '12.3 Breach of security obligations may result in disciplinary action under the Disciplinary Procedure (HR-DISC-02), up to dismissal.', '12.4 Security responsibilities continue for 24 months after termination for confidential information.']),
             ('Execution', ['Template v4.0 approved by CEO 2026-01-08. Executed contracts for the 5 hires in 2026 (E-1058 to E-1062) signed by employee and Daniel Tan; acknowledgement stored in HRIS.'])]),
         'Letter of Employment - Draft', 'docx',
         doc('docx', 'Letter of Employment (Draft)', 'HR-EMP-DRAFT', 'HR Lead', '(pending approval)', '0.3', '2026-04-10', [
             ('Terms', ['Position: Software Engineer. Salary: SGD 7,200 per month. Probation: 3 months. Annual leave: 18 days. Working hours: 9am to 6pm.']),
             ('Signatures', ['Employer: ______________   Employee: ______________'])]))
    # ---- A.6.3
    pair('A.6.3', 'Personnel receive appropriate security awareness, education and training and regular updates.',
         'Security Awareness Completion Matrix FY2026', 'xlsx',
         tab('xlsx', ['Department', 'Headcount', 'Security Basics 2026 completed', 'Completion %', 'Phishing sim Q3 clicks', 'Role training', 'Owner'],
             [['Engineering', 24, 24, '100%', 1, 'Secure coding (OWASP) 24/24', 'CTO'], ['Operations', 14, 14, '100%', 1, 'Incident response drill 14/14', 'Ops Lead'],
              ['Support', 9, 9, '100%', 0, 'PII handling 9/9', 'Support Lead'], ['Sales & Finance', 8, 8, '100%', 1, 'Fraud/BEC awareness 8/8', 'Finance Mgr'],
              ['Management & Security', 7, 7, '100%', 0, 'ISO 27001 LI/LA refresh 3/3', 'CISO']]),
         'Awareness Programme Progress Report Q3', 'pdf',
         doc('pdf', 'Awareness Programme Progress Report Q3', 'HR-SAT-Q3', 'HR Lead', PN, '1.0', '2026-10-05', [
             ('Progress', ['Annual module assigned 2026-05-01 to all 62 staff. As at 2026-10-03 only 38 of 62 staff (61%) have completed the module.', 'Engineering 10/24, Operations 9/14, Support 9/9, Sales and Finance 6/8, Management 4/7.']),
             ('Gaps', ['24 staff overdue, including 14 engineers with production access. Reminders sent 2026-08-15 and 2026-09-15. No phishing simulation was run in Q2 or Q3.'])]))
    # ---- A.6.4
    pair('A.6.4', 'A formal disciplinary process exists and is communicated to personnel who commit a security policy violation.',
         'Disciplinary Procedure for Security Violations', 'pdf',
         doc('pdf', 'Disciplinary Procedure - Information Security Violations', 'HR-DISC-02', 'HR Lead', DT, '2.0', '2026-02-16', [
             ('Process', ['1. Report to CISO or HR. 2. Preliminary assessment within 3 working days. 3. Investigation by HR with CISO input; employee informed in writing and may respond. 4. Disciplinary panel (HR Lead, line manager, CISO) decides outcome.', 'Sanctions: verbal warning, written warning, suspension, termination, referral to authorities. Graduated by severity, intent and repeat occurrence.']),
             ('Communication', ['Published on the intranet 2026-02-20; acknowledged by 62/62 staff by 2026-03-31. Cited in employment contract clause 12.3.']),
             ('Record', ['Cases in 2026: DISC-2026-01 (USB policy breach, written warning 2026-07-09). Approved by Daniel Tan, CEO, 2026-02-16.'])]),
         'Annual Leave and Attendance Policy', 'docx',
         doc('docx', 'Annual Leave and Attendance Policy', 'HR-LEV-01', 'HR Lead', DT, '1.8', '2026-01-10', [
             ('Entitlement', ['Employees receive 18 days of annual leave, rising to 21 days after 5 years of service. Unused leave of up to 7 days may be carried forward until 31 March.']),
             ('Attendance', ['Core hours are 10:00 to 16:00. Employees must notify their line manager before 09:30 on the first day of any unplanned absence. Medical certificates are required for absences of more than one day.'])]))
    # ---- A.6.5
    pair('A.6.5', 'Security responsibilities that remain valid after termination or change of employment are defined and enforced.',
         'Leaver Offboarding Checklists - 2026', 'xlsx',
         tab('xlsx', ['Leaver', 'Last day', 'Okta deactivated', 'AWS/GitHub removed', 'Laptop returned (Jamf)', 'NDA reminder signed', 'Verified by'],
             [['E-1013', '2026-02-27', '2026-02-27 17:40', '2026-02-27', '2026-02-27 (SN C02XK7QH)', 'Yes', 'Tom Wong'], ['E-1024', '2026-04-30', '2026-04-30 18:05', '2026-04-30', '2026-05-04 (SN C02ZM3LA)', 'Yes', 'Tom Wong'],
              ['E-1031', '2026-06-12', '2026-06-12 12:10', '2026-06-12', '2026-06-12 (SN C02YH9PD)', 'Yes', 'Tom Wong'], ['E-1040', '2026-08-28', '2026-08-28 17:55', '2026-08-28', '2026-08-31 (SN C02WQ1RT)', 'Yes', 'Marcus Lee']]),
         'Leaver Access Revocation Exceptions Log', 'csv',
         tab('csv', ['Leaver', 'Last day', 'Account', 'Still active at', 'Days after exit', 'Status'],
             [['E-1013', '2026-02-27', 'Okta', '2026-04-02', 34, 'Open'], ['E-1024', '2026-04-30', 'AWS IAM user', '2026-06-18', 49, 'Open'],
              ['E-1031', '2026-06-12', 'GitHub', '2026-08-01', 50, 'Open'], ['E-1040', '2026-08-28', 'VPN', '2026-10-10', 43, 'Open']]))
    # ---- A.6.6
    pair('A.6.6', 'Confidentiality or non-disclosure agreements reflecting information protection needs are identified, documented and signed.',
         'NDA Template and Executed NDA Register 2026', 'docx',
         doc('docx', 'Mutual Non-Disclosure Agreement Template and Register', 'LEG-NDA-02', 'Legal Counsel (Joyce Lim)', DT, '2.2', '2026-01-30', [
             ('Template terms', ['Definition of Confidential Information including vessel positions, customer manifests and source code; obligations to use only for the Purpose; 5-year confidentiality period; return or destruction on request; Singapore law, SIAC arbitration. Reviewed by external counsel (Rajah Advisory) 2026-01-28.']),
             ('Executed NDAs 2026', ['NDA-2026-011 Pacific Charterers Ltd - signed 2026-02-09 both parties.', 'NDA-2026-014 AIS Data Provider Co - signed 2026-03-17.', 'NDA-2026-019 Harbourline Assurance LLP - signed 2026-08-12.', 'NDA-2026-022 Contractor Kenji Ito (freelance) - signed 2026-09-01.', 'All 62 employees also bound via contract clause 12.2; register reviewed 2026-10-30.'])]),
         'NDA Register', 'pdf',
         doc('pdf', 'NDA Register', 'LEG-NDA-REG', 'Legal Counsel', 'Daniel Tan (CEO)', '1.0', '2023-11-02', [
             ('Register', ['NDA-2022-004 Pacific Charterers - signed 2022-06-01 - expires 2024-06-01 - EXPIRED.', 'NDA-2022-007 AIS Data Provider - signed 2022-08-15 - expires 2024-08-15 - EXPIRED.', 'NDA-2023-002 Contractor - signed 2023-02-10 - expires 2025-02-10 - EXPIRED.', 'No renewals recorded. Last updated 2023-11-02.'])]))
    # ---- A.6.7
    pair('A.6.7', 'Security measures are implemented when personnel work remotely to protect information accessed, processed or stored.',
         'Remote Working Security Standard', 'pdf',
         doc('pdf', 'Remote Working Security Standard', 'POL-RW-01', PN, DT, '1.4', '2026-03-03', [
             ('Requirements', ['Only Jamf-managed laptops may access company data; FileVault enforced and verified at each check-in (compliance 62/62 on 2026-10-30).', 'Remote access exclusively via Okta-protected ZTNA/VPN with phishing-resistant MFA (Okta Verify FastPass); split tunnelling disabled.', 'Home Wi-Fi must use WPA2/WPA3; public Wi-Fi only through the VPN; screen lock 5 minutes; no printing of customer data at home.']),
             ('Monitoring', ['VPN logs reviewed monthly; 3 policy exceptions in 2026 (travel to Manila - approved by CISO, EXC-2026-05).', 'Remote-working training included in Security Basics 2026. Approved by Daniel Tan 2026-03-03.'])]),
         'Jamf Pro - Remote Device Compliance', 'png',
         S('Jamf Pro', 'https://maritime.jamfcloud.com/computers.html?smartGroup=remote-nonCompliant', '#0b5c8e', ['Dashboard', 'Computers', 'Smart Groups', 'Policies'],
           'Remote laptops - Compliance (14 of 62 not compliant)', (['Device', 'User', 'FileVault', 'VPN profile'], [260, 300, 220, 260]),
           [['MS-LT-017', 'e.1017', 'Disabled', 'Disabled'], ['MS-LT-022', 'e.1022', 'Disabled', 'Active'], ['MS-LT-031', 'e.1031', 'Disabled', 'Disabled'], ['MS-LT-044', 'e.1044', 'Active', 'Disabled'], ['MS-LT-051', 'e.1051', 'Disabled', 'Disabled']]),
         src='Integration')
    # ---- A.6.8
    pair('A.6.8', 'A mechanism is provided for personnel to report observed or suspected information security events in a timely manner.',
         'Security Event Reports Register 2026', 'xlsx',
         tab('xlsx', ['Event ID', 'Reported', 'Reporter', 'Channel', 'Type', 'Triage', 'Closed', 'Outcome'],
             [['SEV-2026-004', '2026-02-11 09:14', 'E-1019', 'security@ mailbox', 'Phishing email', 'Priya Nair 09:40', '2026-02-11', 'Blocked in M365, 2 recipients warned'],
              ['SEV-2026-009', '2026-04-22 15:02', 'E-1033', 'Slack #report-security', 'Lost laptop', 'Tom Wong 15:20', '2026-04-23', 'Remote wipe via Jamf'],
              ['SEV-2026-013', '2026-06-30 11:47', 'E-1008', 'Hotline +65 6000 0182', 'Tailgating at HQ', 'Marcus Lee 12:10', '2026-07-02', 'Reminder to staff'],
              ['SEV-2026-017', '2026-08-14 08:31', 'E-1045', 'security@ mailbox', 'Suspicious login', 'Aisha Rahman 08:50', '2026-08-14', 'Password reset, MFA re-enrolled'],
              ['SEV-2026-021', '2026-10-09 16:20', 'E-1002', 'Slack #report-security', 'Misdirected email', 'Lin Mei Ling 16:45', '2026-10-12', 'Recall, DPO assessed no PDPA breach']]),
         'Incident Reporting Guidance', 'docx',
         doc('docx', 'Incident Reporting Guidance', 'GEN-IR-1', 'Management', 'Management', '1', '2026-02-01', [
             ('Overview', ['Employees are encouraged to report any incidents they notice. Reporting helps the company stay safe and should be done as soon as reasonably possible.', 'Reports may be made to a manager or to the relevant team. The company will look into reports and take appropriate action where necessary.'])]))
    # ---- A.7.1
    pair('A.7.1', 'Security perimeters are defined and used to protect areas that contain information and other associated assets.',
         'HQ Level 3 Server Room Door - Badge Reader Photo', 'jpg',
         lambda p: photo(p, ['SERVER ROOM - LEVEL 3', 'Restricted: badge + PIN required', 'Reader ID: HQ-L3-SR-01', 'Inspected 2026-11-18 (P. Nair)']),
         'Level 3 Maintenance Corridor Door Photo', 'jpg',
         lambda p: photo(p, ['SERVICE DOOR', 'Lock under repair', 'Wedged open - no reader fitted', 'Photographed 2026-10-30'], bg=('#3a3a3a', '#7b7b6a')))
    # ---- A.7.2
    pair('A.7.2', 'Secure areas are protected by appropriate entry controls and access points.',
         'HQ Badge Access Log - Server Room Extract Oct 2026', 'csv',
         tab('csv', ['Timestamp', 'Door', 'Badge holder', 'Method', 'Result', 'Escort/Visitor ID'],
             [['2026-10-05 08:52', 'HQ-L3-SR-01', 'Tom Wong', 'Badge+PIN', 'Granted', '-'], ['2026-10-05 14:10', 'HQ-L3-SR-01', 'Contractor - CoolAir (V-0412)', 'Visitor badge+PIN', 'Granted', 'Escort Tom Wong'],
              ['2026-10-12 10:03', 'HQ-L3-SR-01', 'E-1049', 'Badge', 'Denied (no PIN)', '-'], ['2026-10-19 09:30', 'HQ-L3-SR-01', 'Aisha Rahman', 'Badge+PIN', 'Granted', '-'],
              ['2026-10-27 16:45', 'HQ-L3-SR-01', 'E-1021', 'Badge', 'Denied (not authorised)', '-'], ['2026-10-30 11:12', 'HQ-L1-MAIN', 'Visitor V-0431 (Harbourline)', 'Reception badge', 'Granted', 'Escort Marcus Lee']]),
         'Visitor Register', 'pdf',
         doc('pdf', 'Visitor Register - Reception', 'REC-VIS-01', 'Reception', '(not reviewed)', '-', '2026-03-12', [
             ('Entries', ['Visitor 1 - arrived 09:10 - company: n/a - host: ? - badge: none - departure: not recorded.', 'Visitor 2 - arrived 10:25 - company: n/a - host: ? - badge: none - departure: not recorded.', 'Visitor 3 - arrived 13:40 - name illegible - host: ? - departure: not recorded.'])]))
    # ---- A.7.3
    pair('A.7.3', 'Physical security for offices, rooms and facilities is designed and implemented.',
         'HQ Reception and Office Entrance Photo', 'jpg',
         lambda p: photo(p, ['HQ OFFICE - LEVEL 3', 'Staff entrance: badge only', 'Visitors report to reception', 'CCTV in operation 24h'], bg=('#2f4858', '#9fb8c4')),
         'Office Physical Security Review - Draft', 'docx',
         doc('docx', 'Office Physical Security Review (Draft for comment)', 'FAC-PSR-DRAFT', 'Facilities Coordinator', '(awaiting CISO approval)', '0.2', '2026-09-14', [
             ('Observations', ['Reception desk unattended 12:00-13:00. Meeting rooms on Level 2 not lockable. Fire door on Level 3 east side propped open by occupants.']),
             ('Status', ['Draft only. Not reviewed or approved. Recommendations to be agreed.'])]))
    # ---- A.7.4
    pair('A.7.4', 'Premises are continuously monitored for unauthorized physical access.',
         'CCTV Management Console - Camera Status 20 Nov 2026', 'png',
         S('SecureView CCTV', 'https://cctv.maritime-services.local/cameras', '#0b5345', ['Live', 'Cameras', 'Recordings', 'Alerts'], 'Cameras (6 of 6 online)',
           (['Camera', 'Location', 'Status', 'Retention'], [260, 380, 200, 240]),
           [['CAM-01', 'Main entrance', 'Healthy', '90 days'], ['CAM-02', 'Reception', 'Healthy', '90 days'], ['CAM-03', 'Server room corridor', 'Healthy', '90 days'], ['CAM-04', 'Rear exit', 'Healthy', '90 days'], ['CAM-05', 'Loading bay', 'Healthy', '90 days'], ['CAM-06', 'Level 3 stairwell', 'Healthy', '90 days']],
           banner='All cameras recording - last motion event 2026-11-20 09:58'),
         'CCTV Console - Camera Health', 'png',
         S('SecureView CCTV', 'https://cctv.maritime-services.local/cameras', '#7b241c', ['Live', 'Cameras', 'Recordings', 'Alerts'], 'Cameras (3 of 6 online)',
           (['Camera', 'Location', 'Status', 'Retention'], [260, 380, 200, 240]),
           [['CAM-01', 'Main entrance', 'Healthy', '90 days'], ['CAM-02', 'Reception', 'Disabled', '0 days'], ['CAM-03', 'Server room corridor', 'Disabled', '0 days'], ['CAM-04', 'Rear exit', 'Disabled', '0 days'], ['CAM-05', 'Loading bay', 'Healthy', '7 days']],
           banner=None), src='Integration')
    # ---- A.7.5
    pair('A.7.5', 'Protection against physical and environmental threats such as natural disasters is designed and implemented.',
         'Fire and Environmental Protection Inspection Report 2026', 'pdf',
         doc('pdf', 'HQ Fire and Environmental Protection Inspection Report', 'FAC-ENV-2026-02', 'Facilities Coordinator (Ben Koh)', PN, '1.0', '2026-07-22', [
             ('Inspection', ['Carried out 2026-07-15 by SafeGuard Fire Services (cert. SCDF-FSC-77231, valid to 2027-07-14).', 'Server room: FM-200 clean-agent suppression pressure checked (350 psi, in range); smoke detectors checked 12/12; water-leak sensors 4/4 operational; temperature 21.4 C, humidity 46%.']),
             ('Controls', ['Environmental monitoring alerts to on-call phone at 27 C / 70% RH. Flood risk: HQ on Level 3, no basement equipment. Production is in AWS ap-southeast-1 (3 AZs) so physical hazards to HQ do not affect service.']),
             ('Actions', ['Replace 2 expired extinguishers - completed 2026-07-20. Next inspection 2027-01-15.'])]),
         'Fire Safety Inspection Log', 'xlsx',
         tab('xlsx', ['Date', 'Item', 'Inspector', 'Result', 'Certificate valid to'],
             [['2024-01-10', 'Extinguishers', 'SafeGuard', 'Pass', '2024-12-31'], ['2024-01-10', 'Smoke detectors', 'SafeGuard', 'Pass', '2024-12-31'],
              ['2024-01-10', 'Suppression system', 'SafeGuard', 'Pass', '2024-12-31'], ['2024-07-12', 'Extinguishers', 'SafeGuard', 'Pass', '2024-12-31'], ['2024-07-12', 'Water leak sensors', 'SafeGuard', 'Pass', '2024-12-31']]))
    # ---- A.7.6
    pair('A.7.6', 'Security measures for working in secure areas are designed and implemented.',
         'Secure Area Working Procedure - Server Room', 'docx',
         doc('docx', 'Secure Area Working Procedure - Server Room (HQ Level 3)', 'FAC-SA-01', TW, PN, '1.3', '2026-04-08', [
             ('Rules', ['1. Entry only for the 5 named personnel on the authorised list (reviewed quarterly, last 2026-10-01). 2. Visitors and contractors must be escorted at all times and sign the visitor log with host name, purpose and times. 3. No photography, personal storage media or personal devices. 4. Work performed under an approved change ticket; unattended room is locked and alarm set.']),
             ('Monitoring', ['Door log and CCTV (CAM-03) retained 90 days. Monthly review by Marcus Lee: 6 reviews done, 0 unescorted entries found.']),
             ('Approval', ['Approved by Priya Nair, CISO, 2026-04-08. Acknowledged by all authorised personnel.'])]),
         'Contractor Entry Log - Server Room', 'csv',
         tab('csv', ['Date', 'Contractor', 'Area', 'Escort', 'Time in', 'Time out', 'Finding'],
             [['2026-05-14', 'CoolAir Services', 'Server room', 'None', '10:05', '12:40', 'Unescorted - finding open'], ['2026-06-18', 'NetCable Pte', 'Server room', 'None', '14:00', '16:30', 'Unescorted - finding open'],
              ['2026-08-07', 'CoolAir Services', 'Server room', 'None', '09:50', '11:15', 'Unescorted - finding open'], ['2026-09-23', 'PowerTech', 'Server room', 'Not recorded', '15:10', 'n/a', 'Log incomplete - finding open'], ['2026-10-16', 'NetCable Pte', 'Server room', 'None', '13:20', '15:00', 'Unescorted - finding open']]))
    # ---- A.7.7
    pair('A.7.7', 'Clear desk rules for papers and removable storage media, and clear screen rules, are defined and enforced.',
         'Clear Desk and Clear Screen Spot-Check Results Q3 2026', 'pdf',
         doc('pdf', 'Clear Desk and Clear Screen Spot-Check Results Q3 2026', 'ISMS-CDS-Q3', MK, PN, '1.0', '2026-09-29', [
             ('Method', ['Unannounced walk-through of HQ floors on 2026-09-22 (19:00) and 2026-09-24 (12:30) against Clear Desk Standard POL-CD-01 section 4.']),
             ('Results', ['48 desks inspected; 46 compliant (95.8%). Exceptions: 1 unattended unlocked laptop (screen lock not active), 1 customer printout left on a printer tray.', 'Screen lock after 5 minutes enforced by Jamf profile on 62/62 laptops. Confidential waste bins emptied weekly by certified shredder.']),
             ('Follow-up', ['Both staff coached on 2026-09-25. Re-check on 2026-10-20: 48/48 compliant.'])]),
         'Desk Check Photo - Level 2 Open Area', 'jpg',
         lambda p: photo(p, ['DESK 2-14', 'Password on sticky note', 'Laptop unlocked, unattended', 'Customer printout on desk'], bg=('#4a3b2f', '#a89a85')))
    # ---- A.7.8
    pair('A.7.8', 'Equipment is sited securely and protected.',
         'Equipment Siting and Protection Standard - HQ', 'docx',
         doc('docx', 'Equipment Siting and Protection Standard - HQ', 'FAC-EQ-01', TW, PN, '1.2', '2026-03-24', [
             ('Siting', ['Network and server equipment is housed in a locked 42U rack (RACK-A) in the Level 3 server room, away from windows and water pipes, raised 15 cm off the floor. Screens of workstations handling customer data face away from public areas and reception.']),
             ('Protection', ['Rack fitted with UPS (APC 3 kVA), surge protection and environmental sensors (temperature, humidity, leak). Equipment inventory (14 items) tagged MS-ASSET-xxx; verified 2026-09-10.', 'Food and drink prohibited within 3 m of the equipment rack.']),
             ('Approval', ['Approved by Priya Nair 2026-03-24; reviewed annually.'])]),
         'Disaster Recovery Plan Overview', 'pdf',
         doc('pdf', 'Disaster Recovery Plan Overview - MarineOps Platform', 'BCP-DR-02', 'CTO', PN, '1.1', '2026-04-14', [
             ('Recovery strategy', ['Warm standby in AWS ap-southeast-2. RTO 4 hours, RPO 1 hour. Database replication via cross-region read replica.', 'Switchover steps: promote replica, update Route 53 weighted records, scale ECS service to 6 tasks, notify customers via status page.']),
             ('Exercises', ['Annual DR exercise scheduled each October; communications tree maintained by Ops Lead.'])]))
    # ---- A.7.9
    pair('A.7.9', 'Off-premises assets are protected taking into account the different risks of working outside the premises.',
         'Off-Premises Laptop and Mobile Asset Register', 'xlsx',
         tab('xlsx', ['Asset tag', 'Device', 'Assigned to', 'Encryption', 'MDM', 'Remote wipe verified', 'Last check-in', 'Insurance'],
             [['MS-LT-001', 'MacBook Pro 14', 'E-1001', 'FileVault on', 'Jamf', '2026-06-04', '2026-11-19', 'Yes'], ['MS-LT-002', 'MacBook Pro 14', 'E-1002', 'FileVault on', 'Jamf', '2026-06-04', '2026-11-20', 'Yes'],
              ['MS-LT-017', 'MacBook Air M2', 'E-1017', 'FileVault on', 'Jamf', '2026-06-04', '2026-11-18', 'Yes'], ['MS-MB-004', 'iPhone 15', 'E-1004', 'Device encryption', 'Jamf', '2026-06-04', '2026-11-20', 'Yes'],
              ['MS-LT-033', 'MacBook Pro 16', 'E-1033', 'FileVault on', 'Jamf', '2026-06-04', '2026-11-19', 'Yes'], ['MS-LT-058', 'MacBook Air M3', 'E-1058', 'FileVault on', 'Jamf', '2026-08-12', '2026-11-20', 'Yes']]),
         'Laptop Asset Listing - Engineering Only', 'csv',
         tab('csv', ['Asset tag', 'Assigned to', 'Team', 'Encryption', 'MDM'],
             [['MS-LT-001', 'E-1001', 'Engineering', 'FileVault on', 'Jamf'], ['MS-LT-002', 'E-1002', 'Engineering', 'FileVault on', 'Jamf'], ['MS-LT-003', 'E-1003', 'Engineering', 'Unknown', 'Not enrolled'],
              ['MS-LT-004', 'E-1004', 'Engineering', 'FileVault on', 'Jamf'], ['MS-LT-005', 'E-1005', 'Engineering', 'Unknown', 'Not enrolled'], ['Listing excludes Operations, Support, Sales (42 devices)', '', '', '', '']]))
    # ---- A.7.10
    pair('A.7.10', 'Storage media is managed through its life cycle of acquisition, use, transportation and disposal.',
         'Removable Media Handling Standard', 'pdf',
         doc('pdf', 'Removable Media and Storage Media Handling Standard', 'POL-MED-01', TW, PN, '1.2', '2026-02-26', [
             ('Rules', ['USB mass storage is blocked on all Jamf-managed laptops by configuration profile "MS-Restrict-USB" (62/62 devices, verified 2026-11-02). Exceptions require CISO approval and encrypted devices; 2 exceptions active (EXC-2026-03, -07), expiry 2026-12-31.', 'Media containing Confidential data is encrypted (AES-256), labelled, logged in the media register, and carried by named courier only.']),
             ('Lifecycle', ['Acquisition via IT procurement only; reuse after secure wipe (NIST 800-88 Clear); disposal by certified vendor with destruction certificate (see A.7.14).', 'Annual media audit on 2026-10-14: 7 encrypted drives accounted for, 0 missing.']),
             ('Approval', ['Approved by Priya Nair, CISO, 2026-02-26.'])]),
         'Media Handling Guideline', 'docx',
         doc('docx', 'Media Handling Guideline', 'POL-MED-DRAFT', TW, '(unsigned)', '0.1', '2026-08-18', [
             ('Guideline', ['Staff should be careful when using USB drives and other media. Avoid storing sensitive files on removable media where possible.', 'Media that is no longer needed should be disposed of appropriately.']),
             ('Approval', ['Approval signature: __________    Date: __________'])]))
    # ---- A.7.11
    pair('A.7.11', 'Information processing facilities are protected from power outages and other disruptions caused by utilities failures.',
         'UPS and Generator Load Run Report - HQ Server Room', 'pdf',
         doc('pdf', 'UPS and Backup Power Load Run Report', 'FAC-PWR-2026-03', 'Facilities Coordinator (Ben Koh)', TW, '1.0', '2026-08-03', [
             ('Load run', ['Performed 2026-07-28 by PowerTech Engineering (job PT-44871). Mains isolation simulated at 14:00 SGT for 20 minutes.']),
             ('Results', ['UPS APC Smart-UPS SRT 3000 transferred in 0 ms; load 41% (1.2 kW); runtime on battery estimated 38 minutes. Battery health 94%, installed 2024-11 (replace by 2028-11).', 'Diesel generator (Kohler 20 kW) started in 9 s and took load; fuel 82%; 30-minute run completed with no alarms.']),
             ('Conclusion', ['All utilities protections operate as designed. Next run 2027-01. Production workloads run in AWS with multi-AZ power redundancy.'])]),
         'UPS and Generator Run Result - HQ', 'pdf',
         doc('pdf', 'UPS and Generator Run Result', 'FAC-PWR-2026-02', 'Facilities Coordinator (Ben Koh)', TW, '1.0', '2026-05-12', [
             ('Result', ['Run on 2026-05-07: mains isolation simulated. UPS battery supplied load for only 3 minutes 10 seconds against a design target of 30 minutes; battery health measured at 38%.', 'Diesel generator did not start on 3 attempts (starter fault, error code E-27); server room load dropped at 14:04.']),
             ('Findings', ['FINDING-1 (High): UPS batteries require replacement - OPEN. FINDING-2 (High): generator not operational - OPEN. No remediation date agreed at time of report.'])]))
    # ---- A.7.12
    pair('A.7.12', 'Cables carrying power, data or supporting information services are protected from interception, interference or damage.',
         'Server Room Cabling Inspection Photo - Rack A Patch Panel', 'jpg',
         lambda p: photo(p, ['RACK A - PATCH PANEL 1', 'Cables labelled & in trays', 'Power / data segregated', 'Inspected 2026-10-21'], bg=('#1f2d3a', '#6e8798')),
         'Cabling Inspection Checklist', 'docx',
         doc('docx', 'Cabling Inspection Checklist', 'FAC-CAB-[xx]', '[Inspector]', '[Approver]', '[ver]', '[date]', [
             ('Checklist', ['Power cables segregated from data cables: [Yes/No]', 'Patch panels labelled: [Yes/No]', 'Cable trays secured: [Yes/No]', 'Comms cabinets locked: [Yes/No]']),
             ('Notes', ['[Insert notes]'])]))
    # ---- A.7.13
    pair('A.7.13', 'Equipment is maintained correctly to ensure availability, integrity and confidentiality of information.',
         'Equipment Maintenance Log 2026', 'xlsx',
         tab('xlsx', ['Work order', 'Date', 'Equipment', 'Activity', 'Performed by', 'Data handling', 'Result', 'Approved by'],
             [['WO-2601', '2026-02-10', 'Core switch Cisco C9200 SN FOC2519X1AB', 'Firmware 17.9.4a upgrade', 'NetCable Pte', 'Config backup taken', 'Success', 'Tom Wong'], ['WO-2604', '2026-04-14', 'UPS APC SRT3000', 'Battery inspection', 'PowerTech', 'No data', 'Pass', 'Tom Wong'],
              ['WO-2607', '2026-06-09', 'Firewall Fortinet 60F SN FGT60FTK21', 'FortiOS patch 7.2.9', 'Aisha Rahman', 'Config exported to vault', 'Success', 'Priya Nair'], ['WO-2611', '2026-08-25', 'Rack A cooling unit', 'Service and filter change', 'CoolAir', 'Escorted visit', 'Pass', 'Tom Wong'],
              ['WO-2615', '2026-10-13', 'NAS Synology RS1221', 'Disk health check + firmware', 'Tom Wong', 'Encrypted volumes', 'Success', 'Marcus Lee']]),
         'Equipment Service History', 'csv',
         tab('csv', ['Work order', 'Date', 'Equipment', 'Activity', 'Performed by'],
             [['WO-2301', '2023-02-10', 'Core switch', 'Firmware upgrade', 'NetCable'], ['WO-2304', '2023-04-14', 'UPS', 'Battery inspection', 'PowerTech'], ['WO-2307', '2023-06-09', 'Firewall', 'Patch', 'IT'],
              ['WO-2311', '2023-08-25', 'Cooling unit', 'Service', 'CoolAir'], ['WO-2402', '2024-02-02', 'NAS', 'Disk check', 'IT']]))
    # ---- A.7.14
    pair('A.7.14', 'Equipment containing storage media is verified to ensure sensitive data and licensed software has been removed or securely overwritten prior to disposal or re-use.',
         'Certificate of Data Destruction - ITAD Batch 2026-07', 'pdf',
         doc('pdf', 'Certificate of Data Destruction - Batch ITAD-2026-07', 'ITAD-CERT-8841', TW, PN, '1.0', '2026-07-31', [
             ('Details', ['Vendor: GreenCycle ITAD Pte Ltd (NEA licence ITAD-3392). Collected 2026-07-24 from HQ. Method: NIST 800-88 Purge (cryptographic erase for SSD) then physical shredding of drives, witnessed by Tom Wong.']),
             ('Assets', ['MS-LT-006 MacBook Pro SN C02TN4KD - drive wiped, verified.', 'MS-LT-009 MacBook Pro SN C02TQ8MW - drive wiped, verified.', 'MS-LT-012 MacBook Air SN C02UH6VF - drive wiped, verified.', 'MS-SRV-02 Dell R640 SN 7H4K2Q3 - 4 SSD shredded.']),
             ('Sign-off', ['Certificate signed by Wei Jie Tan, GreenCycle (2026-07-30) and verified by Tom Wong, IT Manager, and Priya Nair, CISO (2026-07-31). Asset register updated: status Disposed.'])]),
         'Equipment Disposal Certificate', 'docx',
         doc('docx', 'Equipment Disposal Certificate', 'ITAD-CERT-DRAFT', 'IT Manager', '(not signed)', '1.0', '2026-09-02', [
             ('Statement', ['Several old laptops and one server were collected for recycling on 2026-09-01. The drives have been wiped and the equipment disposed of responsibly.']),
             ('Notes', ['Serial numbers and wipe method not recorded. Vendor signature and verifier signature: not provided.'])]))
    # ---- A.8.1
    pair('A.8.1', 'Information stored on, processed by or accessible via user endpoint devices is protected.',
         'Jamf Pro - Computer Compliance Overview 20 Nov 2026', 'jpg',
         S('Jamf Pro', 'https://maritime.jamfcloud.com/computers.html', '#0b5c8e', ['Dashboard', 'Computers', 'Smart Groups', 'Policies'], 'Computers - Compliance (62 of 62 compliant)',
           (['Check', 'Compliant devices', 'Status', 'Last evaluated'], [320, 220, 220, 260]),
           [['FileVault disk encryption', '62 / 62', 'Compliant', '2026-11-20 09:30'], ['macOS 14.7+ patched', '62 / 62', 'Compliant', '2026-11-20 09:30'], ['Screen lock <= 5 min', '62 / 62', 'Compliant', '2026-11-20 09:30'], ['CrowdStrike sensor active', '62 / 62', 'Compliant', '2026-11-20 09:30'], ['USB storage blocked', '62 / 62', 'Compliant', '2026-11-20 09:30']], fmt='jpg'),
         'Jamf Pro - Endpoint Compliance Summary', 'jpg',
         S('Jamf Pro', 'https://maritime.jamfcloud.com/computers.html', '#0b5c8e', ['Dashboard', 'Computers', 'Smart Groups', 'Policies'], 'Computers - Compliance (41 of 62 compliant)',
           (['Check', 'Compliant devices', 'Status', 'Last evaluated'], [320, 220, 220, 260]),
           [['FileVault disk encryption', '44 / 62', 'Non-compliant', '2026-11-20 09:30'], ['macOS 14.7+ patched', '47 / 62', 'Non-compliant', '2026-11-20 09:30'], ['Screen lock <= 5 min', '55 / 62', 'Non-compliant', '2026-11-20 09:30'], ['CrowdStrike sensor active', '50 / 62', 'Non-compliant', '2026-11-20 09:30']], fmt='jpg'),
         src='Integration')
    # ---- A.8.2
    pair('A.8.2', 'The allocation and use of privileged access rights is restricted and managed.',
         'Privileged Access Review Q3 2026', 'xlsx',
         tab('xlsx', ['Account', 'System', 'Privilege', 'Business justification', 'Last used', 'Reviewer decision', 'Review date', 'Reviewer'],
             [['aisha.rahman', 'AWS ms-prod', 'AdministratorAccess (via SSO, 1h session)', 'Cloud security admin', '2026-11-12', 'Retain', '2026-09-30', 'Priya Nair'], ['tom.wong', 'Okta', 'Super Administrator', 'IT Manager', '2026-11-18', 'Retain', '2026-09-30', 'Priya Nair'],
              ['dev.lead', 'GitHub org', 'Owner', 'Engineering lead', '2026-11-19', 'Retain', '2026-09-30', 'Priya Nair'], ['ex.contractor1', 'AWS ms-prod', 'PowerUserAccess', 'Project ended', '2026-06-02', 'Revoked 2026-10-01', '2026-09-30', 'Priya Nair'],
              ['break-glass-01', 'AWS ms-prod', 'AdministratorAccess', 'Emergency, MFA hardware key, sealed', 'never', 'Retain', '2026-09-30', 'Priya Nair'], ['marcus.lee', 'M365', 'Global Reader', 'ISMS audit', '2026-11-10', 'Downgraded from Global Admin', '2026-09-30', 'Priya Nair']]),
         'AWS IAM - AdministratorAccess Policy Usage', 'png',
         S('AWS Console | IAM', 'https://console.aws.amazon.com/iam/home#/policies/AdministratorAccess', '#232f3e', ['IAM', 'Users', 'Roles', 'Policies', 'Access Analyzer'], 'AdministratorAccess - attached to 17 entities (ms-prod)',
           (['Entity', 'Type', 'Last activity', 'MFA'], [300, 200, 260, 200]),
           [['dev-ci-deploy', 'User', '2026-11-19', 'Disabled'], ['jenkins-legacy', 'User', '2026-11-02', 'Disabled'], ['contractor-ops', 'User', '2026-07-14', 'Disabled'], ['intern-2025', 'User', '2026-03-01', 'Disabled'], ['analytics-role', 'Role', '2026-11-20', 'Open']],
           banner=None), src='Integration')
    # ---- A.8.3
    pair('A.8.3', 'Access to information and other associated assets is restricted in accordance with the access control policy.',
         'Information Access Restriction Matrix and Quarterly Review', 'docx',
         doc('docx', 'Information Access Restriction Matrix and Quarterly Review', 'ISMS-ACM-02', PN, DT, '2.4', '2026-10-02', [
             ('Matrix', ['Customer vessel data (S3 ms-fleet-data): read - Platform Engineers (Okta group eng-platform, 11), Support Tier 2 (read-only, masked); write - Fleet API service role only.', 'HR records (SharePoint /HR): HR Lead and CEO only. Finance (Xero): Finance Manager, CEO. Source code: engineering team per repo team. Production database: DBA role via SSO with JIT approval, 4 h expiry.']),
             ('Review', ['Quarterly review 2026-09-30: 14 group memberships removed (role changes), 2 exceptions documented. Okta group-rule export attached to ticket SEC-3318.']),
             ('Approval', ['Approved by Daniel Tan (CEO) 2026-10-02; owner Priya Nair.'])]),
         'Access Control Matrix 2024', 'pdf',
         doc('pdf', 'Access Control Matrix', 'ISMS-ACM-01', 'Marcus Lee', 'Priya Nair', '1.0', '2024-09-10', [
             ('Matrix (as at 2024-09)', ['Customer data: Engineering, Support, Ops. HR records: HR. Finance: Finance Manager. Production DB: DBA team (4 named staff).', 'Staff list includes personnel who have since left and does not cover systems adopted after September 2024 (Okta, GitHub Enterprise, Jamf).']),
             ('Review', ['Next review due 2025-09-10 - not performed.'])]))
    # ---- A.8.4
    pair('A.8.4', 'Read and write access to source code, development tools and software libraries is appropriately managed.',
         'GitHub Branch Protection and Repository Access - ms-fleet-api', 'png',
         S('GitHub | maritime-services', 'https://github.com/maritime-services/ms-fleet-api/settings/branches', '#24292f', ['Code', 'Settings', 'Branches', 'Collaborators', 'Security'], 'Branch protection rule: main (ms-fleet-api)',
           (['Setting', 'Value', 'Status', 'Updated'], [380, 260, 200, 260]),
           [['Require pull request (1 approving review)', 'On', 'Enabled', '2026-02-11'], ['Require status checks (CI, SAST)', 'On', 'Enabled', '2026-02-11'], ['Restrict force pushes / deletions', 'On', 'Enabled', '2026-02-11'], ['Require signed commits', 'On', 'Enabled', '2026-02-11'], ['Admin bypass', 'Off', 'Enabled', '2026-02-11'], ['SSO (Okta SAML) enforced for org', 'On', 'Enabled', '2026-01-20']],
           banner='Branch protection active - 11 collaborators, all via Okta SAML'),
         'GitHub Repository Settings - ms-legacy-portal', 'png',
         S('GitHub | maritime-services', 'https://github.com/maritime-services/ms-legacy-portal/settings/branches', '#24292f', ['Code', 'Settings', 'Branches', 'Collaborators', 'Security'], 'Branch protection: main (ms-legacy-portal) - none configured',
           (['Setting', 'Value', 'Status', 'Updated'], [380, 260, 200, 260]),
           [['Require pull request', 'Off', 'Disabled', 'n/a'], ['Require status checks', 'Off', 'Disabled', 'n/a'], ['Restrict force pushes', 'Off', 'Disabled', 'n/a'], ['Collaborators with Admin', '9 of 14', 'Open', 'n/a']],
           banner=None), src='Integration')
    return M


if __name__ == '__main__':
    out = sys.argv[1]
    m = build(out)
    json.dump(m, open(os.path.join(out, 'manifest.json'), 'w'), indent=1)
    print(len(m), 'items ->', out)
