"""ISO 27001:2022 evidence for the Maritime Services TEST org, controls A.5.2 - A.5.32 (2 docs per control)."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_iso_evidence import pdf, dcx, xlsx, csvf, shot, meta  # noqa: E402

PN, DT, ML, AR, TW = 'Priya Nair (CISO)', 'Daniel Tan (CEO)', 'Marcus Lee (ISMS Manager)', 'Aisha Rahman (Cloud Security Engineer)', 'Tom Wong (IT Manager)'
GL, KO, RM, SK = 'Grace Lim (HR Lead)', 'Kevin Ong (Procurement)', 'Ravi Menon (CTO)', 'Sarah Koh (Legal Counsel)'
AWS = ['Dashboard', 'IAM', 'S3', 'Config', 'CloudTrail', 'GuardDuty']
OKTA = ['Dashboard', 'Directory', 'Applications', 'Security', 'Reports']


def H(did, owner, appr, ver, date):
    return meta(did, owner, appr, ver, date)


# Each spec: (code, passdoc, faildoc). doc = (fmt, title, head_or_header, body)
# fmt pdf/docx: body = [(heading, [lines])]; xlsx/csv: head=header list, body=rows; png/jpg: body = kwargs for shot
SPECS = []


def C(code, p, f):
    SPECS.append((code, p, f))


C('A.5.2',
  ('docx', 'Information Security Roles and Responsibilities Matrix', H('ISMS-ROLE-01', PN, DT, '2.0', '2026-01-26'), [
      ('Defined roles', ['CEO (Daniel Tan): accountable for the ISMS, approves policy and risk acceptance.', 'CISO (Priya Nair): owns the ISMS, reports to the board quarterly, chairs the Security Forum.', 'ISMS Manager (Marcus Lee): maintains documented information, internal audit schedule, SoA.', 'Cloud Security Engineer (Aisha Rahman): AWS guardrails, vulnerability management, logging.', 'IT Manager (Tom Wong): endpoints (Jamf), M365, Okta administration.', 'Asset owners: each system in the asset register has a named owner (see ISMS-AST-01).']),
      ('Allocation and communication', ['Roles allocated by written appointment letters signed 2026-01-20 to 2026-01-26 (APP-2026-001 to APP-2026-006).', 'Responsibilities are included in job descriptions for the 14 ISMS-relevant positions, reviewed by HR (Grace Lim) 2026-02-03.', 'Deputies named for CISO (Marcus Lee) and IT Manager (Aisha Rahman).']),
      ('Approval', ['Approved by Daniel Tan, CEO, 2026-01-26. Reviewed at Management Review 2026-10-08.'])]),
  ('xlsx', 'RACI Draft - Security Functions', ['Activity', 'Responsible', 'Accountable', 'Consulted', 'Informed'], [
      ['Risk assessment', '<Name TBD>', '<Name TBD>', '', ''], ['Access reviews', '<Name TBD>', '', '<Name TBD>', ''], ['Incident response lead', '[insert role]', '[insert role]', '', ''],
      ['Vendor assessments', '<Name TBD>', '', '', ''], ['Backup monitoring', '[insert role]', '<Name TBD>', '', '']]))

C('A.5.3',
  ('xlsx', 'Segregation of Duties Conflict Matrix 2026', ['Duty A', 'Duty B', 'Conflict?', 'Mitigation', 'Role holder A', 'Role holder B', 'Reviewed'], [
      ['Developer commit to main', 'Production deployment approval', 'Yes', 'GitHub branch protection: 1 independent reviewer; CAB approves high-risk', 'Dev team', 'Tom Wong', '2026-09-10'],
      ['AWS IAM administration', 'CloudTrail log review', 'Yes', 'Logs shipped to separate security account; reviewed by CISO', 'Aisha Rahman', 'Priya Nair', '2026-09-10'],
      ['Vendor selection', 'Payment approval', 'Yes', 'Procurement selects, Finance (CFO) approves payments > SGD 5,000', 'Kevin Ong', 'Finance', '2026-09-10'],
      ['User access request', 'User access approval', 'Yes', 'Okta workflow: requester cannot self-approve, manager approves', 'Employee', 'Line manager', '2026-09-10'],
      ['Policy authoring', 'Policy approval', 'Yes', 'CISO authors, CEO approves', 'Priya Nair', 'Daniel Tan', '2026-09-10'],
      ['Backup administration', 'Backup restore approval', 'Yes', 'Restores require ticket approved by system owner', 'Tom Wong', 'Ravi Menon', '2026-09-10']]),
  ('pdf', 'Segregation of Duties Standard (Draft v0.4)', H('ISMS-SOD-01', 'Marcus Lee (ISMS Manager)', 'Approval pending', '0.4', '2026-05-11'), [
      ('Principle', ['Conflicting duties should be separated where practicable to reduce the risk of misuse.', 'Where separation is not practicable, compensating controls such as monitoring should be considered.']),
      ('Status', ['This draft has not been reviewed by the CISO or the CEO.', 'The conflict matrix has not yet been compiled. Owners to be agreed.', 'Signature: ____________________   Date: __________'])]))

C('A.5.4',
  ('pdf', 'Management Directive on Security Compliance and Quarterly Briefing Record', H('MGT-DIR-2026-03', DT, 'Board of Directors', '1.0', '2026-02-09'), [
      ('Directive', ['All personnel and contractors must apply the Information Security Policy (POL-ISP-01) and topic policies. Non-compliance is handled under the Disciplinary Procedure HR-DP-02.', 'Line managers are responsible for ensuring their teams complete training and follow procedures.']),
      ('Evidence of management enforcement', ['Directive emailed to all 62 staff 2026-02-09; read receipts 62/62 by 2026-02-13.', 'Quarterly management briefings held 2026-03-17, 2026-06-16, 2026-09-15 (attendance: 9/9 department heads each).', 'Two policy breaches (unencrypted USB, shared password) handled via HR-DP-02 in 2026; outcomes recorded in HR case log HRC-26-04 and HRC-26-09.']),
      ('Approval', ['Issued by Daniel Tan, CEO, 2026-02-09; endorsed by the board 2026-02-12.'])]),
  ('docx', 'Management Commitment Statement 2024', H('MGT-STMT-2024-01', DT, 'Daniel Tan (CEO)', '1.0', '2024-09-02'), [
      ('Statement', ['Management is committed to information security and expects all personnel to follow company policy.', 'Managers should encourage their teams to apply security practices.']),
      ('Notes', ['Issued to staff by email on 2024-09-02. No later briefings or compliance reviews have been recorded since this date.'])]))

C('A.5.5',
  ('csv', 'Authority Contact Register', ['Authority', 'Purpose', 'Contact', 'Channel', 'Internal owner', 'Last verified', 'Reporting trigger'], [
      ['Singapore Police Force - Commercial Affairs Dept', 'Cybercrime reporting', 'ccid-report@spf.example.sg / 1800-255-0000', 'Phone, online', 'Priya Nair', '2026-09-22', 'Fraud, extortion'],
      ['CSA SingCERT', 'Cyber incident reporting', 'singcert@csa.example.sg', 'Email, portal', 'Priya Nair', '2026-09-22', 'Significant incident'],
      ['PDPC Singapore', 'Personal data breach notification', 'breach.notify@pdpc.example.sg', 'Online form', 'Sarah Koh', '2026-09-22', 'Notifiable breach within 3 days'],
      ['MPA Port Operations Control', 'Maritime cyber incident (MPA circular)', 'poc@mpa.example.sg', 'Phone, email', 'Ravi Menon', '2026-09-22', 'Incident affecting vessel operations'],
      ['AWS Abuse / Support', 'Cloud provider escalation', 'Enterprise Support case', 'Console', 'Aisha Rahman', '2026-09-22', 'Account compromise'],
      ['Cyber insurer (Marsh)', 'Policy notification', 'claims@marsh.example', 'Email', 'Finance', '2026-09-22', 'Any ransomware event']]),
  ('pdf', 'Working with External Authorities', H('ISMS-AUTH-00', 'Marcus Lee (ISMS Manager)', 'Priya Nair (CISO)', '1.0', '2026-03-12'), [
      ('Overview', ['The company recognises the importance of cooperating with relevant authorities and regulators in the event of an incident.', 'Staff should contact the appropriate authority when needed and follow guidance provided.', 'Management will ensure relationships with authorities are kept in good order.'])]))

C('A.5.6',
  ('xlsx', 'Special Interest Group Memberships and Participation 2026', ['Group', 'Type', 'Representative', 'Membership ID', 'Valid to', 'Participation 2026', 'Output'], [
      ['ISACA Singapore Chapter', 'Professional body', 'Priya Nair', 'ISACA-SG-448120', '2026-12-31', 'Attended 3 meetings', 'Notes on MAS TRM update'],
      ['Singapore Shipping Association - Cyber WG', 'Industry forum', 'Ravi Menon', 'SSA-CWG-072', '2026-12-31', 'Attended 4 workshops', 'IMO MSC.428 gap action'],
      ['SingCERT mailing list', 'Alert service', 'Aisha Rahman', 'Subscribed', 'n/a', '27 advisories triaged', 'Patch ticket PCH-1182'],
      ['OWASP Singapore', 'Security community', 'Dev lead', 'Member', '2026-12-31', 'Attended 2 meetups', 'Secure coding brown-bag 2026-06-04'],
      ['Maritime ISAC', 'Sector sharing', 'Priya Nair', 'MISAC-2291', '2027-03-31', 'Received 11 bulletins', 'GPS spoofing awareness note']]),
  ('csv', 'Security Community Memberships (legacy list)', ['Group', 'Representative', 'Membership ID', 'Valid to', 'Last activity'], [
      ['ISACA Singapore Chapter', 'Former CISO', 'ISACA-SG-331090', '2024-12-31', '2024-06-12'], ['Singapore Shipping Association - Cyber WG', 'Former CTO', 'SSA-CWG-040', '2024-12-31', '2024-03-20'],
      ['SANS Newsletter', 'IT team', 'Subscribed', 'n/a', '2024-08-01'], ['Maritime ISAC', 'Former CISO', 'MISAC-1180', '2024-09-30', '2024-05-02'], ['OWASP Singapore', 'Dev lead', 'Member', '2024-12-31', '2024-04-18']]))

C('A.5.7',
  ('pdf', 'Monthly Threat Intelligence Brief - October 2026', H('TI-2026-10', AR, PN, '1.0', '2026-11-03'), [
      ('Sources', ['SingCERT advisories (9), Maritime ISAC bulletins (3), AWS Security Bulletins, CISA KEV catalogue, vendor feeds (Okta, GitHub).']),
      ('Analysis', ['T1: Ransomware group targeting port operators via VPN appliance CVE-2026-1182. Relevance: High - we operate site-to-site VPN for vessel links.', 'T2: GPS spoofing activity in the Strait of Malacca (MPA advisory 2026-10-14). Relevance: Medium - customer-side, awareness note issued.', 'T3: Phishing kit impersonating M365 sign-in. Relevance: High - 4 lookalike domains blocked.']),
      ('Actions taken', ['VPN appliance patched 2026-10-19 (CHG-2268). Lookalike domains added to Defender blocklist 2026-10-21. IOC list loaded into GuardDuty threat list (47 IPs).', 'Brief reviewed at Security Forum 2026-11-05. Approved by Priya Nair.'])]),
  ('docx', 'Vulnerability Scan Summary - Q3 2026', H('VM-2026-Q3', AR, PN, '1.0', '2026-10-05'), [
      ('Summary', ['Amazon Inspector scanned 41 EC2 instances and 12 ECR repositories. Critical: 0, High: 3, Medium: 21, Low: 57.', 'Median time to remediate High findings: 9 days.']),
      ('Notes', ['This report lists technical vulnerabilities in our own assets only. It does not include external threat information or adversary analysis.'])]))

C('A.5.8',
  ('docx', 'Security Review Checklist - PRJ-2026-014 Fleet Telemetry API v3', H('PM-SEC-014', RM, PN, '1.2', '2026-04-14'), [
      ('Project', ['PRJ-2026-014: Fleet Telemetry API v3. Sponsor: Ravi Menon. Project manager: Dev Patel. Go-live 2026-06-30.']),
      ('Security integration at each phase', ['Initiation (2026-03-02): classification of data (Confidential - vessel positions), risk entry R-014 added to register.', 'Design (2026-03-23): threat model STRIDE completed by Aisha Rahman; 11 threats, 11 mitigations.', 'Build: SAST (CodeQL) and dependency scan gates in CI; 0 high findings at release.', 'Pre-go-live (2026-06-18): external penetration assessment, 2 medium findings fixed 2026-06-24; security sign-off by Priya Nair.']),
      ('Approval', ['Security gate approved 2026-06-25, Priya Nair (CISO). Process applies to all projects per PM-SEC-00.'])]),
  ('pdf', 'Project Governance Standard - Security Review Thresholds', H('PM-SEC-00', RM, PN, '1.1', '2026-02-16'), [
      ('Scope', ['Security review applies to projects with a budget above SGD 50,000.', 'Projects below this value, internal tooling projects, and all pilot projects are exempt from the security gate and threat modelling to avoid delays.']),
      ('Note', ['Project managers may decide for themselves whether data classification is needed for exempt projects. Currently 9 of 17 active projects are exempt.'])]))

C('A.5.9',
  ('xlsx', 'Information and Asset Inventory 2026', ['Asset ID', 'Asset', 'Type', 'Classification', 'Owner', 'Location', 'Last reviewed'], [
      ['AST-001', 'MarineOps production database (RDS ms-prod-db)', 'Information system', 'Confidential', 'Ravi Menon', 'AWS ap-southeast-1', '2026-10-12'],
      ['AST-002', 'Customer vessel telemetry (S3 ms-telemetry)', 'Data', 'Confidential', 'Ravi Menon', 'AWS ap-southeast-1', '2026-10-12'],
      ['AST-003', 'Source code (GitHub org maritime-services)', 'Information', 'Internal', 'Dev lead', 'GitHub', '2026-10-12'],
      ['AST-004', 'Employee records (HRIS)', 'Data', 'Restricted', 'Grace Lim', 'SaaS HRIS', '2026-10-12'],
      ['AST-005', 'Okta tenant', 'Service', 'Confidential', 'Tom Wong', 'Okta', '2026-10-12'],
      ['AST-006', 'Laptops (62 units, Jamf)', 'Hardware', 'Internal', 'Tom Wong', 'Staff / HQ', '2026-10-12'],
      ['AST-007', 'Signed customer contracts', 'Information', 'Confidential', 'Sarah Koh', 'M365 SharePoint', '2026-10-12']]),
  ('csv', 'Asset List Export', ['Asset ID', 'Asset', 'Type', 'Owner', 'Classification'], [
      ['AST-101', 'Laptop MBP-0041', 'Hardware', '', ''], ['AST-102', 'Laptop MBP-0042', 'Hardware', '', ''], ['AST-103', 'Laptop MBP-0043', 'Hardware', '', ''],
      ['AST-104', 'Monitor 27in', 'Hardware', '', ''], ['AST-105', 'Docking station', 'Hardware', '', ''], ['AST-106', 'Mobile phone', 'Hardware', '', '']]))

C('A.5.10',
  ('pdf', 'Acceptable Use Policy', H('POL-AUP-01', GL, DT, '2.0', '2026-03-05'), [
      ('Scope', ['Applies to all employees, contractors and interns using company information, devices, M365, GitHub, AWS and Okta.']),
      ('Rules', ['1. Company devices are managed by Jamf; disk encryption and screen lock (5 min) must not be disabled.', '2. Customer and vessel data may only be stored in approved systems (M365, AWS, GitHub); personal cloud storage is prohibited.', '3. Passwords and MFA tokens must not be shared. Use the approved password manager.', '4. Handling of Confidential and Restricted information follows POL-CLS-01.', '5. Personal use is permitted if it does not harm security or productivity; activity may be monitored per PDPA notice.', '6. Report suspected incidents to security@maritime-services within 1 hour.']),
      ('Acknowledgement', ['Acknowledged by 62/62 staff in MIGRC between 2026-03-06 and 2026-03-31. Approved by Daniel Tan, CEO, 2026-03-05.'])]),
  ('docx', 'Acceptable Use Policy (template)', ['Company: [Company Name]', 'Document ID: [POL-XXX]   Version: [x.x]   Date: [dd/mm/yyyy]', 'Owner: [Owner]   Approved by: [Approver]'], [
      ('Scope', ['This policy applies to [all staff / contractors].']),
      ('Rules', ['1. [Insert rules for use of company devices.]', '2. [Insert rules for use of email and internet.]', '3. [Insert handling rules for information.]']),
      ('Approval', ['Signed: [Name], [Title], [Date]'])]))

C('A.5.11',
  ('csv', 'Leaver Asset Return Log 2026', ['Leaver ID', 'Role', 'Last day', 'Assets issued', 'Assets returned', 'Return date', 'Verified by', 'Accounts disabled'], [
      ['E-0872', 'Operations Analyst', '2026-02-27', 'MacBook Pro MBP-0017, badge B-212', 'Both', '2026-02-27', 'Tom Wong', '2026-02-27'],
      ['E-0915', 'Backend Engineer', '2026-04-30', 'MacBook Pro MBP-0033, YubiKey Y-044', 'Both', '2026-04-29', 'Tom Wong', '2026-04-30'],
      ['E-0930', 'Account Manager', '2026-06-12', 'MacBook Air MBA-0009, badge B-230', 'Both', '2026-06-12', 'Tom Wong', '2026-06-12'],
      ['E-0947', 'QA Engineer', '2026-07-31', 'MacBook Pro MBP-0038, badge B-241', 'Both', '2026-07-30', 'Tom Wong', '2026-07-31'],
      ['E-0961', 'Contractor - DevOps', '2026-09-15', 'Loaner laptop LNR-003, YubiKey Y-051', 'Both', '2026-09-15', 'Aisha Rahman', '2026-09-15'],
      ['E-0978', 'Support Lead', '2026-10-30', 'MacBook Pro MBP-0044, badge B-255', 'Both', '2026-10-30', 'Tom Wong', '2026-10-30']]),
  ('xlsx', 'Offboarding Asset Status Report - Q3 2026', ['Leaver ID', 'Last day', 'Assets issued', 'Returned?', 'Days outstanding', 'Status', 'Owner'], [
      ['E-0947', '2026-07-31', 'MacBook Pro MBP-0038', 'No', 112, 'Open', 'Tom Wong'], ['E-0952', '2026-08-14', 'YubiKey Y-049, badge B-244', 'No', 98, 'Open', 'Tom Wong'],
      ['E-0961', '2026-09-15', 'Loaner laptop LNR-003', 'Partial', 66, 'Open', 'Aisha Rahman'], ['E-0966', '2026-09-30', 'MacBook Air MBA-0012', 'No', 51, 'Open', 'Tom Wong'],
      ['E-0970', '2026-10-09', 'Badge B-250', 'Yes', 0, 'Closed', 'Tom Wong']]))

C('A.5.12',
  ('pdf', 'Information Classification Policy', H('POL-CLS-01', PN, DT, '2.1', '2026-02-24'), [
      ('Classification levels', ['Restricted: employee/personal data, credentials, keys. Impact if disclosed: severe, regulatory exposure (PDPA).', 'Confidential: customer vessel data, contracts, source code, risk register. Impact: serious commercial/contractual harm.', 'Internal: policies, internal procedures, org charts. Impact: minor.', 'Public: marketing material, published website content.']),
      ('Responsibilities', ['Information owners classify at creation; default is Internal. Classification reviewed annually with the asset inventory (AST list). Reclassification requires owner approval.']),
      ('Criteria', ['Legal (PDPA), contractual (charterer NDAs), business value, and availability needs are considered per ISO 27001 A.5.12.', 'Approved by Daniel Tan, CEO, 2026-02-24.'])]),
  ('docx', 'Data Handling Guidance', H('GUID-DH-01', 'IT team', 'Daniel Tan (CEO)', '1.0', '2026-06-01'), [
      ('Guidance', ['Employees should think about how sensitive the information is and handle it accordingly.', 'Sensitive information should be protected appropriately. Ask your manager if you are not sure.', 'Information that is not sensitive can be shared more freely.'])]))

C('A.5.13',
  ('docx', 'Information Labelling Procedure', H('PRC-LBL-01', ML, PN, '1.3', '2026-03-18'), [
      ('Labelling rules', ['Documents: classification in header and footer (M365 sensitivity labels: Public, Internal, Confidential, Restricted). Default label for new files: Internal.', 'Email: Outlook sensitivity label adds [CONF] tag in subject for Confidential and Restricted.', 'Cloud data: S3 buckets and RDS carry tag data-classification=<level>, enforced by AWS Config rule required-tags (compliance 100% on 2026-11-18).', 'Source repositories: GitHub topics classification-confidential / internal.', 'Physical media: coloured sticker (red = Restricted, orange = Confidential).']),
      ('Implementation evidence', ['Purview label policy published to 62/62 users 2026-03-25; 3,418 documents auto-labelled by 2026-11-01.', 'Approved by Priya Nair, CISO, 2026-03-18.'])]),
  ('pdf', 'Brand and Document Formatting Standard', H('MKT-FMT-02', 'Marketing Lead', 'Daniel Tan (CEO)', '2.0', '2026-01-30'), [
      ('Purpose', ['Standard fonts, logo placement and header/footer layout for company documents and presentations.']),
      ('Rules', ['Use Calibri 11pt for body text. Logo top left, document title centred. Footer shows page number and company UEN.', 'Slides use the corporate template from SharePoint/Brand. Colours: navy #1f3a5f, teal #1d7f8c.'])]))

C('A.5.14',
  ('pdf', 'Information Transfer Policy and Secure Transfer Register', H('POL-TRF-01', PN, DT, '1.4', '2026-04-08'), [
      ('Rules by channel', ['Email: TLS enforced (MTA-STS); Confidential attachments via M365 Message Encryption; Restricted data must not be emailed.', 'File exchange with charterers: SFTP (AWS Transfer Family, key-based) or customer portal over HTTPS; no consumer file-sharing.', 'API integrations: TLS 1.2+ with mutual authentication for AIS and port-system partners.', 'Removable media: prohibited unless encrypted and approved by IT.']),
      ('Agreements', ['Transfer agreements in place with 9 external parties (NDAs / DPAs): register TRF-REG-2026 with IDs NDA-0211 to NDA-0219, signed between 2026-01-15 and 2026-09-02.']),
      ('Approval', ['Approved by Daniel Tan, CEO, 2026-04-08.'])]),
  ('csv', 'DLP Outbound Transfer Review - Q3 2026', ['Event ID', 'Date', 'Channel', 'Data type', 'Encrypted', 'Agreement on file', 'Status'], [
      ['DLP-3301', '2026-07-08', 'Email', 'Crew list (Restricted)', 'No', 'No', 'Open'], ['DLP-3312', '2026-07-22', 'Personal Dropbox', 'Vessel schedules', 'No', 'No', 'Open'],
      ['DLP-3340', '2026-08-19', 'USB', 'Source code archive', 'No', 'n/a', 'Open'], ['DLP-3377', '2026-09-03', 'Email', 'Customer contract', 'No', 'Yes', 'Open'], ['DLP-3391', '2026-09-24', 'WeTransfer', 'Telemetry export', 'No', 'No', 'Open']]))

C('A.5.15',
  ('png', 'AWS IAM Identity Center - Permission Sets and Assignments', 'AWS Console | IAM Identity Center', 'https://console.aws.amazon.com/singlesignon/home#/accounts', '#232f3e', AWS,
   'Permission sets and assignments (ms-prod, ms-security, ms-dev)', (['Permission set', 'Assigned to', 'Account', 'Session', 'Status'], [280, 260, 200, 150, 120]),
   [['ReadOnlyAccess', 'grp-engineering (22)', 'ms-prod', '4h', 'Active'], ['PowerUserDev', 'grp-engineering (22)', 'ms-dev', '8h', 'Active'], ['SecurityAudit', 'grp-security (3)', 'all accounts', '4h', 'Active'], ['Administrator', 'priya.nair, aisha.rahman', 'ms-prod', '1h', 'Active']],
   'Least privilege: production access limited to read-only; admin restricted to 2 named users, reviewed 2026-11-18'),
  ('docx', 'Access Control Policy Draft', H('POL-AC-02', 'Tom Wong (IT Manager)', 'Not yet approved', '0.2', '2026-08-03'), [
      ('Principles', ['Access to systems should be based on business need.', 'Users should be given the access they need to do their jobs.']),
      ('Open items', ['Physical access rules for HQ and server room: not yet defined.', 'Approval workflow: to be confirmed. Review frequency: to be confirmed.', 'No sign-off recorded; policy is not yet published to staff.'])]))

C('A.5.16',
  ('jpg', 'Okta Admin - Lifecycle Management: Joiner/Mover/Leaver Events', 'Okta Admin Console', 'https://maritime-services-admin.okta.com/admin/reports/system-log', '#00297a', OKTA,
   'Lifecycle events - last 90 days (HRIS-driven)', (['Event', 'User ID', 'Source', 'Result', 'Timestamp'], [300, 220, 240, 160, 240]),
   [['User created', 'E-0981 (j.ong)', 'HRIS (SCIM)', 'Completed', '2026-11-02 09:00'], ['Group change', 'E-0902 (r.chia)', 'HRIS (SCIM)', 'Completed', '2026-10-19 09:00'], ['User deactivated', 'E-0978 (s.tay)', 'HRIS (SCIM)', 'Completed', '2026-10-30 18:05'], ['User deactivated', 'E-0961 (contractor)', 'HRIS (SCIM)', 'Completed', '2026-09-15 17:30']], None),
  ('csv', 'Identity Reconciliation - HRIS vs Okta vs AWS (Q3 2026)', ['Account', 'Identity source', 'HRIS status', 'Okta status', 'AWS IAM status', 'Finding'], [
      ['d.lim', 'Okta', 'Terminated 2026-06-30', 'Active', 'Active', 'Orphaned account - open'], ['svc-reports', 'None', 'No owner', 'n/a', 'Active', 'Shared identity, no owner - open'],
      ['k.tan2', 'Okta', 'Active', 'Active', 'Active', 'Duplicate identity for E-0912 - open'], ['contractor.dev3', 'Okta', 'Terminated 2026-08-15', 'Active', 'Active', 'Orphaned account - open'], ['admin-shared', 'None', 'No owner', 'n/a', 'Active', 'Shared admin login - open']]))

C('A.5.17',
  ('pdf', 'Authentication Standard and Credential Management Procedure', H('STD-AUTH-01', AR, PN, '1.5', '2026-05-12'), [
      ('Requirements', ['Passwords: minimum 14 characters, checked against breached-password list, no forced periodic rotation; lockout after 10 attempts.', 'MFA: mandatory for all users in Okta (FastPass / WebAuthn; SMS not permitted) and for AWS root and IAM users.', 'Initial credentials: delivered via Okta activation link valid 7 days; must be changed on first login.', 'Secrets: stored in AWS Secrets Manager, rotated every 90 days (automated); no secrets in GitHub (push protection enabled 2026-03-01).']),
      ('Evidence', ['Okta policy export 2026-11-10: 62/62 users enrolled in MFA. Secrets scanning: 0 open alerts on 2026-11-12.', 'Approved by Priya Nair, CISO, 2026-05-12.'])]),
  ('png', 'Okta Authentication Policy - Password Settings', 'Okta Admin Console', 'https://maritime-services-admin.okta.com/admin/access/authenticators', '#00297a', OKTA,
   'Password policy - Default Policy', (['Setting', 'Value', 'Applies to', 'Status'], [340, 280, 260, 200]),
   [['Minimum length', '6 characters', 'All users', 'Active'], ['Complexity', 'None', 'All users', 'Disabled'], ['Multi-factor authentication', 'Optional', 'All users', 'Disabled'], ['Lockout after invalid attempts', 'Unlimited', 'All users', 'Disabled']], None))

C('A.5.18',
  ('xlsx', 'Quarterly User Access Review - Q3 2026 (AWS, GitHub, M365)', ['System', 'Reviewer', 'Accounts reviewed', 'Access removed', 'Excess privileges reduced', 'Completed', 'Approved by'], [
      ['AWS (ms-prod, ms-dev)', 'Aisha Rahman', 38, 3, 2, '2026-10-06', 'Priya Nair'], ['GitHub org', 'Ravi Menon', 31, 2, 4, '2026-10-07', 'Priya Nair'],
      ['M365 / SharePoint', 'Tom Wong', 62, 5, 7, '2026-10-08', 'Priya Nair'], ['Okta admin roles', 'Priya Nair', 6, 1, 1, '2026-10-08', 'Daniel Tan'], ['Jamf', 'Tom Wong', 4, 0, 0, '2026-10-09', 'Priya Nair'],
      ['Production database', 'Ravi Menon', 7, 2, 2, '2026-10-09', 'Priya Nair']]),
  ('pdf', 'User Access Review Summary - Q1 2025', H('UAR-2025-Q1', TW, 'Not signed', '1.0', '2025-03-28'), [
      ('Scope', ['Quarterly review of access to AWS and M365 for Q1 2025. 52 accounts reviewed.']),
      ('Results', ['4 accounts had access removed. 2 privileges reduced.', 'Reviewer sign-off: pending. Approver: not recorded.', 'No later review has been filed.'])]))

C('A.5.19',
  ('pdf', 'Supplier Security Policy and Supplier Risk Register 2026', H('POL-SUP-01', KO, PN, '1.6', '2026-07-14'), [
      ('Process', ['Suppliers are tiered (Critical, High, Standard) by data access and service dependency. Critical/High suppliers undergo security due diligence before onboarding and annually.']),
      ('Register excerpt', ['Amazon Web Services - Critical - ISO 27001/SOC 2 reports on file (2026-03).', 'Okta - Critical - SOC 2 Type II (2026-04). Microsoft 365 - Critical - ISO 27001 cert reviewed 2026-04.', 'GitHub - High - SOC 2 reviewed 2026-05. AIS data provider (MarineTraffic API) - High - questionnaire SQ-2026-07 scored 88/100.', 'Jamf - High - SOC 2 reviewed 2026-05.']),
      ('Approval', ['Approved by Priya Nair, CISO, 2026-07-14; supplier register owned by Kevin Ong.'])]),
  ('xlsx', 'Supplier Onboarding Checklist', ['Supplier', 'Tier', 'Due diligence completed', 'Risk rating', 'Owner', 'Date'], [
      ['[Supplier name]', '[Tier]', '[Y/N]', '[ ]', '[Owner]', '[date]'], ['[Supplier name]', '[Tier]', '[Y/N]', '[ ]', '[Owner]', '[date]'], ['[Supplier name]', '[Tier]', '[Y/N]', '[ ]', '[Owner]', '[date]'],
      ['[Supplier name]', '[Tier]', '[Y/N]', '[ ]', '[Owner]', '[date]'], ['[Supplier name]', '[Tier]', '[Y/N]', '[ ]', '[Owner]', '[date]']]))

C('A.5.20',
  ('docx', 'Data Processing and Security Addendum - AIS Data Provider (SA-2026-07)', H('SA-2026-07', SK, DT, '1.0', '2026-06-10'), [
      ('Parties', ['Maritime Services Pte. Ltd. and MarineTraffic Data Services Ltd. Effective 2026-06-10, term 24 months.']),
      ('Security requirements agreed', ['Supplier maintains ISO 27001 or SOC 2 Type II; annual report provided within 30 days of issue.', 'Encryption in transit (TLS 1.2+) and at rest; access limited to named personnel with MFA.', 'Security incident notification to Maritime Services within 24 hours; cooperation in investigation.', 'Sub-processors listed in Schedule 2 and require prior written notice of change; right to audit once per year with 30 days notice.', 'Return or deletion of data within 30 days of termination with written certification.']),
      ('Execution', ['Signed for Maritime Services: Daniel Tan, CEO, 2026-06-10. Signed for supplier: M. Ortega, Director, 2026-06-09.'])]),
  ('pdf', 'Master Services Agreement - Office Cleaning and Facilities', H('SA-2026-02', KO, 'Unsigned', '1.0', '2026-02-18'), [
      ('Parties', ['Maritime Services Pte. Ltd. and BrightSpace Facilities Pte. Ltd. Term 12 months from 2026-03-01.']),
      ('Terms', ['Services: weekly cleaning of HQ. Fees: SGD 1,850 per month. Payment 30 days.', 'Either party may terminate with 60 days notice. Confidentiality clause applies to information seen on premises.']),
      ('Signature block', ['For Maritime Services: ____________________   For BrightSpace: ____________________'])]))

C('A.5.21',
  ('pdf', 'ICT Supply Chain Security Review - Software Dependencies 2026', H('SCS-2026-02', AR, RM, '1.0', '2026-09-28'), [
      ('Scope', ['All 14 production repositories in GitHub org maritime-services; container base images in 12 ECR repositories; 3 critical SaaS/IaaS providers.']),
      ('Controls', ['Dependabot and GitHub dependency review on 14/14 repositories; SBOM (CycloneDX) generated per release and stored in S3 ms-sbom.', 'Only signed base images from approved registries (cosign verify in CI); 2 images replaced after provenance gaps found in Q2.', 'Third-party components must meet licence and vulnerability criteria (no unresolved Critical/High).']),
      ('Results', ['1,204 dependencies tracked; 0 Critical, 2 High (patched 2026-09-12 and 2026-09-14). Review owner Aisha Rahman; approved by Ravi Menon 2026-09-28.'])]),
  ('csv', 'Dependency Scan Results - Repository Coverage', ['Repository', 'Dependabot enabled', 'SBOM generated', 'Open High/Critical', 'Reviewed'], [
      ['marineops-api', 'Yes', 'Yes', 0, '2026-08-11'], ['marineops-web', 'Yes', 'No', 3, 'Not reviewed'], ['telemetry-ingest', 'No', 'No', 'Unknown', 'Not reviewed'],
      ['reports-service', 'No', 'No', 'Unknown', 'Not reviewed'], ['notification-svc', 'No', 'No', 'Unknown', 'Not reviewed'], ['infra-terraform', 'Yes', 'Yes', 0, '2026-08-11']]))

C('A.5.22',
  ('xlsx', 'Supplier Service Review Register - H1/H2 2026', ['Supplier', 'Review date', 'Evidence reviewed', 'SLA met', 'Issues', 'Changes noted', 'Reviewer'], [
      ['Amazon Web Services', '2026-09-16', 'SOC 2 Type II (period 2025-10 to 2026-03), SLA reports', 'Yes (99.99%)', 'None', 'New region features, no impact', 'Aisha Rahman'],
      ['Okta', '2026-09-17', 'SOC 2 Type II 2026, incident notices', 'Yes (99.99%)', '1 minor outage 2026-07-03', 'Admin console redesign', 'Tom Wong'],
      ['Microsoft 365', '2026-09-17', 'ISO 27001 cert, SLA dashboard', 'Yes', 'None', 'MFA enforcement changes', 'Tom Wong'],
      ['MarineTraffic AIS API', '2026-09-22', 'ISO 27001 cert, uptime report', 'Yes (99.7%)', 'Latency spike 2026-08-14', 'New API version v3', 'Ravi Menon'],
      ['GitHub', '2026-09-23', 'SOC 2 Type II 2026', 'Yes', 'None', 'Secret scanning default on', 'Aisha Rahman']]),
  ('docx', 'Supplier Review - Cloud Hosting Provider', H('SRV-2024-05', KO, 'Priya Nair (CISO)', '1.0', '2025-01-20'), [
      ('Review', ['Supplier: regional hosting provider (backup site). Review date 2025-01-20. Assurance report reviewed: SOC 2 Type II covering 2022-07-01 to 2023-06-30.']),
      ('Conclusion', ['The report period ended more than 18 months before this review and no bridge letter was obtained. The supplier is assessed as acceptable. Next review not scheduled.'])]))

C('A.5.23',
  ('pdf', 'Cloud Services Security Standard and Exit Strategy', H('STD-CLD-01', AR, RM, '1.3', '2026-04-27'), [
      ('Acquisition', ['New cloud services require a security assessment (data classification, region, certifications, shared-responsibility mapping) and CISO approval before purchase. Approved services: AWS, Okta, M365, GitHub, Jamf Cloud.']),
      ('Use and management', ['AWS: Control Tower landing zone with SCP guardrails, CloudTrail organisation trail, Config conformance packs, data residency limited to ap-southeast-1 (SCP deny other regions except global services).', 'Customer data encrypted with customer-managed KMS keys; keys rotated annually (rotation CHG-2261, 2026-10-21).']),
      ('Exit', ['Exit plans documented per Critical service: AWS data export via S3/RDS snapshots to alternate region within 14 days; Okta user export via API; estimated exit effort reviewed 2026-04-20. Approved by Ravi Menon, CTO.'])]),
  ('pdf', 'Cloud Usage Guidelines', H('GUID-CLD-00', 'IT team', 'Management', '1.0', '2026-05-04'), [
      ('Overview', ['The company uses cloud services to run its business and staff should use them responsibly.', 'Cloud security is important and everyone should be aware of risks when using online services.', 'Contact IT for assistance with cloud tools.'])]))

C('A.5.24',
  ('docx', 'Information Security Incident Response Plan', H('POL-IR-01', PN, DT, '2.3', '2026-06-01'), [
      ('Roles', ['Incident Commander: Priya Nair (deputy Marcus Lee). Technical lead: Aisha Rahman. Communications: Sarah Koh. Executive sponsor: Daniel Tan.']),
      ('Process', ['Reporting channel: security@maritime-services, Slack #sec-incident, 24x7 on-call phone +65 6000 0112.', 'Phases: detect, triage (severity SEV1-SEV4), contain, eradicate, recover, review. SEV1 requires CEO notification within 1 hour and regulator assessment within 24 hours.', 'Playbooks: ransomware, credential compromise, data leak, vessel-link outage (IR-PB-01 to IR-PB-06).']),
      ('Preparation', ['Plan exercised by tabletop 2026-05-20 (12 participants); on-call rota published monthly. Approved by Daniel Tan 2026-06-01.'])]),
  ('csv', 'Security On-Call Roster - Q4 2026', ['Week starting', 'Primary', 'Secondary', 'Phone'], [
      ['2026-10-05', 'Aisha Rahman', 'Tom Wong', '+65 8000 0101'], ['2026-10-12', 'Tom Wong', 'Aisha Rahman', '+65 8000 0102'], ['2026-10-19', 'Aisha Rahman', 'Marcus Lee', '+65 8000 0101'],
      ['2026-10-26', 'Marcus Lee', 'Tom Wong', '+65 8000 0103'], ['2026-11-02', 'Tom Wong', 'Aisha Rahman', '+65 8000 0102']]))

C('A.5.25',
  ('xlsx', 'Security Event Triage Log Q3 2026', ['Event ID', 'Detected', 'Source', 'Description', 'Assessed by', 'Classification', 'Decision', 'Closed'], [
      ['EVT-0412', '2026-07-09 03:12', 'GuardDuty', 'Unusual API calls from new IP', 'Aisha Rahman', 'Event - false positive', 'Close; IP allow-listed', '2026-07-09'],
      ['EVT-0431', '2026-07-30 14:40', 'Defender', 'Phishing email reported by user', 'Tom Wong', 'Incident SEV3', 'Escalate to INC-2026-017', '2026-08-02'],
      ['EVT-0455', '2026-08-18 22:05', 'CloudTrail alarm', 'Console login without MFA (break-glass)', 'Aisha Rahman', 'Event - authorised', 'Close; ticket CHG-2249 matched', '2026-08-19'],
      ['EVT-0478', '2026-09-04 09:30', 'Okta', 'Impossible travel alert', 'Tom Wong', 'Incident SEV3', 'Escalate to INC-2026-021', '2026-09-05'],
      ['EVT-0502', '2026-10-12 11:18', 'Inspector', 'Critical CVE on bastion host', 'Aisha Rahman', 'Incident SEV2', 'Escalate to INC-2026-026', '2026-10-14']]),
  ('docx', 'Tabletop Exercise Report - Event Classification', H('EX-2026-03', ML, 'Priya Nair (CISO)', '1.0', '2026-08-26'), [
      ('Exercise', ['Scenario run 2026-08-20 with 8 participants: five simulated alerts to be classified as event or incident.']),
      ('Results', ['Only 2 of 5 alerts were classified correctly. The ransomware precursor (alert 3) was closed as a false positive and the exposed credential alert (alert 5) was not escalated.', 'Criteria in SEC-EVT-01 were not known to 5 of 8 participants.', 'Open actions: A1 update triage criteria, A2 retrain on-call staff, A3 re-run exercise. All three are open with no due dates.'])]))

C('A.5.26',
  ('pdf', 'Incident Report INC-2026-021 - Impossible Travel / Credential Compromise', H('INC-2026-021', AR, PN, '1.0', '2026-09-12'), [
      ('Summary', ['Severity SEV3. Detected 2026-09-04 09:30 (Okta impossible-travel alert). Affected: one employee account (E-0933). No customer data accessed.']),
      ('Timeline', ['09:42 Account suspended and sessions revoked by Tom Wong. 10:05 Password reset, MFA factors re-enrolled.', '10:40 CloudTrail and M365 audit logs reviewed: one sign-in from a foreign IP, no mailbox rules or data downloads.', '13:15 Phishing site identified and takedown requested. 2026-09-05 Account restored.']),
      ('Response per IR-PB-02', ['Containment 12 minutes after detection; eradication complete same day; user notified and briefed.', 'Closed 2026-09-12 and approved by Priya Nair, CISO.'])]),
  ('pdf', 'Incident Record INC-2026-024', H('INC-2026-024', 'Not assigned', 'Not recorded', '0.1', '2026-10-01'), [
      ('Summary', ['Unusual outbound traffic reported from a laptop on 2026-09-29. Status: Investigating.']),
      ('Notes', ['Laptop was left connected to the network. No containment action recorded.', 'No timeline, severity, root cause or closure recorded. Incident commander not assigned.'])]))

C('A.5.27',
  ('docx', 'Post-Incident Review - INC-2026-021', H('PIR-2026-021', ML, PN, '1.0', '2026-09-19'), [
      ('Root cause', ['User entered credentials on a lookalike M365 sign-in page; SMS fallback was still allowed for 6 accounts.']),
      ('Lessons and improvements', ['L1: Disable SMS as a factor and enforce phishing-resistant MFA - done 2026-09-22 (CHG-2255), owner Tom Wong.', 'L2: Add lookalike-domain blocklist and brand monitoring - done 2026-10-21.', 'L3: Add phishing report button to Outlook - done 2026-09-30.', 'L4: Update Security Awareness module with this scenario - delivered 2026-10-07 to 62/62 staff.']),
      ('Follow-up', ['Effectiveness check on 2026-11-10: 0 SMS-factor logins, phishing reports up 40% month on month. Approved by Priya Nair 2026-09-19; actions closed 2026-11-10.'])]),
  ('csv', 'Incident Corrective Action Tracker', ['Action ID', 'Incident', 'Action', 'Owner', 'Due', 'Status', 'Days overdue'], [
      ['CA-101', 'INC-2026-011', 'Rotate exposed API key', 'Aisha Rahman', '2026-05-15', 'Open', 190], ['CA-102', 'INC-2026-011', 'Add secret scanning to CI', 'Dev lead', '2026-05-30', 'Open', 175],
      ['CA-109', 'INC-2026-017', 'Mail filter rule update', 'Tom Wong', '2026-08-20', 'Open', 92], ['CA-114', 'INC-2026-017', 'Training refresh', 'Grace Lim', '2026-09-01', 'Open', 80],
      ['CA-120', 'INC-2026-021', 'Disable SMS MFA', 'Tom Wong', '2026-10-01', 'Open', 50]]))

C('A.5.28',
  ('pdf', 'Digital Evidence Collection Procedure and Chain-of-Custody Record', H('PRC-FOR-01', PN, DT, '1.2', '2026-03-24'), [
      ('Procedure', ['Evidence is collected by trained responders (Aisha Rahman, Marcus Lee). Volatile data first, then disk snapshots (EBS snapshots with legal hold tag) and log export (CloudTrail, Okta System Log) to the write-once evidence bucket ms-evidence (Object Lock, Compliance mode).', 'Each item is hashed (SHA-256) at collection and recorded; originals are never analysed directly.']),
      ('Chain-of-custody example: INC-2026-021', ['EV-021-01 Okta System Log export, collected 2026-09-04 10:20 by Aisha Rahman, SHA-256 9c1e...a7f2, stored ms-evidence.', 'EV-021-02 M365 audit export, collected 2026-09-04 10:50, SHA-256 41bd...0c88; transferred to Marcus Lee 2026-09-05 09:00, receipt signed.']),
      ('Approval', ['Approved by Daniel Tan, CEO, 2026-03-24. Legal review by Sarah Koh.'])]),
  ('docx', 'Evidence Handling Form', ['Company: Maritime Services Pte. Ltd.', 'Form ID: [FRM-EV-__]   Date: [dd/mm/yyyy]', 'Collected by: [name]   Authorised by: [name]'], [
      ('Item details', ['Incident reference: [INC-____]', 'Description of evidence: [ ]', 'Collection method: [ ]', 'Hash value: [ ]']),
      ('Custody log', ['Released by: [ ]   Received by: [ ]   Date/time: [ ]', 'Storage location: [ ]'])]))

C('A.5.29',
  ('pdf', 'Security During Disruption - Continuity Security Plan', H('BCP-SEC-01', PN, DT, '1.1', '2026-05-26'), [
      ('Objective', ['Maintain information security controls while operating in degraded or recovery mode (cloud region impairment, office loss, ransomware).']),
      ('Provisions', ['Break-glass AWS admin role (2 holders, hardware MFA, sealed in HQ safe and password manager) with every use alerted and reviewed within 24 hours.', 'Remote working under disruption: Jamf-managed laptops only, Okta MFA, no personal devices; VPN-less zero-trust access.', 'Backups held in immutable S3 Object Lock vault (90 days) and a second region copy (ap-southeast-2) for recovery; logging continues to separate security account.', 'Alternate-site procedures cover HQ loss: staff work remotely, badge systems not required.']),
      ('Roles', ['Crisis team: Daniel Tan, Priya Nair, Ravi Menon, Tom Wong. Plan reviewed 2026-11-04; approved by Daniel Tan 2026-05-26.'])]),
  ('xlsx', 'Business Continuity Contact and Procedure List 2024', ['Item', 'Description', 'Owner', 'Last updated', 'Security considerations'], [
      ['Crisis call tree', 'Phone numbers of crisis team', 'Former COO', '2024-03-04', 'None documented'], ['Office evacuation', 'Fire and evacuation plan', 'Facilities', '2024-03-04', 'None documented'],
      ['Server room', 'Procedures for on-prem servers (decommissioned 2025)', 'Former IT Manager', '2024-03-04', 'None documented'], ['Supplier list', 'Key suppliers', 'Procurement', '2024-03-04', 'None documented'],
      ['Backup tapes', 'Weekly tape rotation', 'Former IT Manager', '2024-03-04', 'None documented']]))

C('A.5.30',
  ('xlsx', 'Disaster Recovery Exercise Results - 2026', ['Date', 'Scenario', 'System', 'RTO target', 'RTO achieved', 'RPO target', 'RPO achieved', 'Result', 'Approved by'], [
      ['2026-04-22', 'RDS restore from vault', 'MarineOps DB (ms-prod-db)', '4h', '2h 35m', '24h', '1h', 'Met', 'Ravi Menon'],
      ['2026-04-22', 'Rebuild ECS services via Terraform', 'MarineOps API/Web', '4h', '1h 50m', 'n/a', 'n/a', 'Met', 'Ravi Menon'],
      ['2026-08-12', 'Regional switchover to ap-southeast-2', 'Telemetry ingest', '8h', '5h 10m', '24h', '2h', 'Met', 'Priya Nair'],
      ['2026-08-12', 'Okta outage - break-glass access', 'Admin access', '2h', '45m', 'n/a', 'n/a', 'Met', 'Priya Nair'],
      ['2026-10-14', 'Ransomware recovery from immutable backup', 'File shares / M365 exports', '12h', '8h 20m', '24h', '4h', 'Met', 'Daniel Tan']]),
  ('pdf', 'DR Exercise Report - Regional Switchover 2026-09-09', H('DR-2026-04', TW, 'Priya Nair (CISO)', '1.0', '2026-09-14'), [
      ('Objective', ['Switch MarineOps production to ap-southeast-2 within the 8 hour RTO.']),
      ('Results', ['Switchover took 14h 20m. RTO breached by 6h 20m. RDS cross-region replica was 19h behind (RPO target 4h) because replication was paused after CHG-2231.', 'Terraform state for the secondary region was out of date; 3 manual fixes required. DNS TTL of 24h delayed client traffic.']),
      ('Findings', ['F1 replication monitoring - Open. F2 Terraform drift - Open. F3 DNS TTL reduction - Open. Re-run of the exercise is not yet scheduled.'])]))

C('A.5.31',
  ('xlsx', 'Legal, Statutory, Regulatory and Contractual Requirements Register 2026', ['Ref', 'Requirement', 'Source', 'Applicability', 'Owner', 'Controls / evidence', 'Last review'], [
      ['LR-01', 'Personal Data Protection Act 2012', 'PDPC Singapore', 'All personal data of staff/customers', 'Sarah Koh', 'Privacy policy, DPO, breach procedure IR-PB-03', '2026-10-05'],
      ['LR-02', 'Cybersecurity Act 2018 / CSA Codes', 'CSA', 'Voluntary alignment', 'Priya Nair', 'ISMS (ISO 27001)', '2026-10-05'],
      ['LR-03', 'MPA Maritime Cybersecurity guidelines; IMO MSC.428(98)', 'MPA / IMO', 'Customer-driven obligations', 'Ravi Menon', 'Cyber risk register, customer clauses', '2026-10-05'],
      ['LR-04', 'Charterer security addenda (3 contracts)', 'Contracts', 'Contractual', 'Sarah Koh', 'Contract register CR-2026', '2026-10-05'],
      ['LR-05', 'Computer Misuse Act 1993', 'Statute', 'Awareness / disciplinary', 'Grace Lim', 'POL-AUP-01, HR-DP-02', '2026-10-05'],
      ['LR-06', 'Employment Act (records retention)', 'MOM', 'HR records', 'Grace Lim', 'Retention schedule RET-01', '2026-10-05']]),
  ('docx', 'Compliance Obligations Overview 2024', H('LEG-2024-01', SK, 'Daniel Tan (CEO)', '1.0', '2024-10-14'), [
      ('Overview', ['The company is subject to the Personal Data Protection Act and various contractual obligations with customers.', 'Legal counsel monitors changes in regulation.']),
      ('Status', ['This overview was prepared in October 2024 and has not been reviewed since. It does not list the MPA guidelines adopted afterwards or customer contract addenda signed in 2025 and 2026.'])]))

C('A.5.32',
  ('pdf', 'Intellectual Property Rights and Software Licence Compliance Procedure', H('PRC-IPR-01', SK, DT, '1.2', '2026-03-31'), [
      ('Procedure', ['Software is only installed from approved sources; Jamf blocks unapproved installers. Open-source use follows the OSS policy (approved licences: MIT, Apache-2.0, BSD; copyleft requires Legal approval).', 'Licence entitlements are tracked in the software asset register SWR-2026 and reconciled quarterly against Jamf and M365 usage.', 'Customer and supplier IP is protected by NDA and contract clauses; employee IP assignment is in the employment contract template.']),
      ('Most recent reconciliation (2026-10-15)', ['Microsoft 365: 65 licences vs 62 users - compliant. Jetbrains: 18 vs 18. Figma: 6 vs 6. Docker: 22 vs 20. No over-deployment found; 3 unused M365 licences reclaimed.', 'Reviewed by Tom Wong; approved by Daniel Tan, CEO.'])]),
  ('csv', 'Software Licence Reconciliation - Q3 2026', ['Software', 'Licences owned', 'Installations detected', 'Variance', 'Action', 'Status'], [
      ['Adobe Acrobat Pro', 10, 17, -7, 'Purchase or remove', 'Open'], ['JetBrains IDE', 18, 26, -8, 'Purchase or remove', 'Open'], ['Docker Desktop', 20, 31, -11, 'Purchase or remove', 'Open'],
      ['Figma', 6, 9, -3, 'Purchase or remove', 'Open'], ['Microsoft 365 E3', 65, 62, 3, 'None', 'Closed']]))


FORBID = re.compile(r'test|sample|fake|fail', re.I)


def _write(path, doc):
    fmt, title = doc[0], doc[1]
    if fmt in ('pdf', 'docx'):
        (pdf if fmt == 'pdf' else dcx)(path, title, doc[2], doc[3])
    elif fmt in ('xlsx', 'csv'):
        (xlsx if fmt == 'xlsx' else csvf)(path, doc[2], doc[3])
    else:
        _, _, app, url, accent, nav, heading, cols, rows, banner = doc[:10]
        shot(path, app, url, accent, nav, heading, cols, rows, banner=banner, fmt='jpg' if fmt == 'jpg' else None)


def build(out):
    os.makedirs(out, exist_ok=True)
    ctl = {c['code']: c for c in json.load(open(os.environ.get('CONTROLS_JSON', '/tmp/claude-1000/-home-ubuntu-MIGRC/33c4d926-1c97-4867-9bd2-33dc89266ed9/scratchpad/controls.json')))}
    M = []
    for code, p, f in SPECS:
        for kind, doc, exp in (('pass', p, 'Approved'), ('fail', f, 'Rejected')):
            assert not FORBID.search(repr(doc)), (code, kind, FORBID.search(repr(doc)).group())
            fname = f"{code.replace('.', '_')}_{kind}.{doc[0]}"
            _write(os.path.join(out, fname), doc)
            src = 'Integration' if doc[0] in ('png', 'jpg') else 'Manual Upload'
            M.append(dict(code=code, title=doc[1], desc=ctl[code]['desc'][:200], file=fname, source=src, expect=exp, extra=[]))
    return M


if __name__ == '__main__':
    out = sys.argv[1]
    m = build(out)
    json.dump(m, open(os.path.join(out, 'manifest.json'), 'w'), indent=1)
    print(len(m), 'items ->', out)
