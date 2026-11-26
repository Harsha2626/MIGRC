"""Synthetic ISO 27001:2022 evidence, slice 1 (clauses 4.1 .. A.5.1) for the Maritime Services TEST org.

Usage: python scripts/gen_iso_evidence_p1.py <out_dir>  -> files + manifest.json (2 per control)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_iso_evidence import pdf, dcx, xlsx, csvf, meta, shot  # noqa: E402

CISO, CEO = 'Priya Nair (CISO)', 'Daniel Tan (CEO)'
CTO, ITM, HR = 'Marcus Lee (CTO)', 'Aisha Rahman (IT Manager)', 'Grace Lim (HR Lead)'
CONTROLS = json.load(open(os.environ.get('CTRL_JSON', '/tmp/claude-1000/-home-ubuntu-MIGRC/33c4d926-1c97-4867-9bd2-33dc89266ed9/scratchpad/controls.json')))[0:31]
AWS = ['Dashboard', 'Documents', 'Policies', 'Reports', 'Settings']


def S(h, *lines):
    return (h, list(lines))


def build(out):
    os.makedirs(out, exist_ok=True)
    M = []
    info = {c['code']: c for c in CONTROLS}

    def add(code, tag, title, fname_ext, writer, expect, src='Manual Upload'):
        fname = f"{code.replace('.', '_')}_{tag}.{fname_ext}"
        writer(os.path.join(out, fname))
        M.append(dict(code=code, title=title, desc=info[code]['desc'], file=fname, source=src, expect=expect, extra=[]))

    def doc(code, tag, title, ext, head, secs, expect):
        w = pdf if ext == 'pdf' else dcx
        add(code, tag, title, ext, lambda p: w(p, title, head, secs), expect)

    def tab(code, tag, title, ext, header, rows, expect):
        w = xlsx if ext == 'xlsx' else csvf
        add(code, tag, title, ext, lambda p: w(p, header, rows), expect)

    def img(code, tag, title, ext, expect, *a, **k):
        add(code, tag, title, ext, lambda p: shot(p, *a, fmt=ext if ext == 'jpg' else None, **k), expect, src='Integration')

    A, R = 'Approved', 'Rejected'

    # ---------------- 4.1
    doc('4.1', 'pass', 'Internal and External Issues Analysis - 2026 Review', 'pdf', meta('ISMS-CTX-02', CISO, CEO, '2.0', '2026-03-12'), [
        S('Method', 'PESTLE and SWOT workshop held 2026-03-05 with CEO, CTO, CISO, Head of Operations and Finance Lead (6 attendees). Output reviewed against ISO 27001 clause 4.1 and the 2025 issues log (ISMS-CTX-01 v1.4).'),
        S('External issues', 'E-01 Regulatory: PDPA 2012 amendments and MPA Maritime Cyber Security Guidelines apply to our fleet-management customers; owner CISO.',
          'E-02 Threat landscape: three ransomware incidents reported in Singapore port logistics Q4 2025; GPS/AIS spoofing advisories from MPA (circular 2026-014).',
          'E-03 Market: 3 of top-5 charterers now mandate ISO 27001 in tenders worth SGD 2.4M ARR.',
          'E-04 Supply chain: dependency on AWS ap-southeast-1, Okta and a third-party AIS data feed.'),
        S('Internal issues', 'I-01 62 staff across Engineering (24), Operations (18), Finance/HR (8), Management (12); 11 joined in H2 2025 so onboarding capacity is a constraint.',
          'I-02 Platform runs on AWS ap-southeast-1 with 41 EC2 instances; Jamf-managed laptops; GitHub for source control.', 'I-03 Rapid growth: customer vessels under management grew from 9 to 14 in 12 months.'),
        S('Outcome', 'Issues carried into risk register R-001..R-014 and objectives OBJ-2026-01..06. Next review 2026-09 and on any material change.', 'Approved at Management Review 2026-03-12. Signed Daniel Tan (CEO), Priya Nair (CISO).')], A)
    doc('4.1', 'fail', 'Strategic Context Overview', 'pdf', meta('ISMS-CTX-01', CISO, CEO, '1.1', '2024-11-04'), [
        S('Purpose', 'This overview records the internal and external factors affecting Maritime Services Pte. Ltd. information security.'),
        S('External issues', 'Regulatory pressure from PDPA; customers asking for ISO 27001 certification; ransomware activity in the shipping sector.'),
        S('Internal issues', 'Company has 41 staff, a single AWS account and a small engineering team.'),
        S('Review', 'Reviewed with management on 2024-11-04. Next review planned 2025-05. No later review recorded.')], R)

    # ---------------- 4.2
    tab('4.2', 'pass', 'Interested Parties and Requirements Register', 'xlsx',
        ['ID', 'Interested party', 'Requirement / expectation', 'Source', 'Addressed by', 'Owner', 'Last reviewed'],
        [['IP-01', 'Charterers (top-5)', 'ISO 27001 certification, 24h breach notification', 'MSA clauses 11.2, 14', 'ISMS, POL-IR-01', 'CEO', '2026-03-12'],
         ['IP-02', 'Maritime and Port Authority of Singapore', 'Maritime cyber guidelines, incident reporting', 'MPA circular 2026-014', 'POL-IR-01, A.5.26', 'CISO', '2026-03-12'],
         ['IP-03', 'PDPC', 'Personal data protection, 3-day breach notification', 'PDPA s26D', 'POL-PRIV-01', 'DPO', '2026-03-12'],
         ['IP-04', 'Employees (62)', 'Clear policies, secure tools, training', 'HR handbook', 'POL-AUP-01', 'HR Lead', '2026-03-12'],
         ['IP-05', 'AWS / Okta / Microsoft', 'Shared responsibility, acceptable use', 'Service terms', 'Supplier register SUP-001..004', 'CTO', '2026-03-12'],
         ['IP-06', 'P&I clubs / insurers', 'Cyber controls evidence at renewal', 'Policy schedule 2026', 'Annual declaration', 'CFO', '2026-03-12']], A)
    doc('4.2', 'fail', 'Interested Parties Register', 'docx', meta('ISMS-IP-01', '[Owner name]', '[Approver name]', '[version]', '[date]'), [
        S('Register', 'Party: [Party name]    Requirement: [Describe requirement]    Source: [Contract / law reference]',
          'Party: [Party name]    Requirement: [Describe requirement]    Source: [Contract / law reference]',
          'Party: [Party name]    Requirement: [Describe requirement]    Source: [Contract / law reference]'),
        S('Instructions', 'List all customers, regulators, suppliers and employees whose needs are relevant to the ISMS. Indicate which requirements will be addressed through the ISMS. Delete this paragraph before approval.'),
        S('Review', 'Reviewed on: [date]    Reviewer: [name]')], R)

    # ---------------- 4.3
    doc('4.3', 'pass', 'ISMS Scope Statement and Boundary Definition v2', 'pdf', meta('ISMS-SCOPE-02', CISO, CEO, '2.0', '2026-04-14'), [
        S('Scope statement', 'The ISMS applies to the design, development, hosting and support of the MarineOps fleet-management SaaS, and the corporate IT services that support it, delivered from Singapore HQ and the AWS ap-southeast-1 region.'),
        S('In scope', 'Locations: 1 Harbourfront Ave (HQ, levels 3-4). Systems: AWS production and staging accounts (4412, 5512), Okta, Microsoft 365, GitHub organisation, Jamf-managed MacBooks (66). People: all 62 employees and 5 contractors.'),
        S('Interfaces and dependencies', 'Customer vessel VPN gateways (ISMS-NET-04), third-party AIS feed (SUP-003), AWS shared-responsibility controls (SOC 2 and ISO 27001 reports on file, retrieved 2026-02-10).'),
        S('Exclusions and justification', 'Vessel-side OT (ECDIS, VSAT) is customer-owned and excluded; data-centre physical security inherited from AWS.'),
        S('Approval', 'Approved by Daniel Tan (CEO) on 2026-04-14 following Management Review minutes MR-2026-02.')], A)
    doc('4.3', 'fail', 'ISMS Scope - Corporate Office IT Only', 'docx', meta('ISMS-SCOPE-03', ITM, CEO, '1.0', '2026-05-06'), [
        S('Scope', 'The ISMS applies to the Singapore HQ office network, staff laptops and Microsoft 365 tenant only.'),
        S('Exclusions', 'The MarineOps production platform, AWS accounts and customer data are excluded from the ISMS and managed under separate engineering procedures. Source code repositories on GitHub are excluded.'),
        S('Rationale', 'Limits audit effort in the first certification year. Certificate wording to reference "corporate IT services".'),
        S('Approval', 'Approved by Daniel Tan (CEO), 2026-05-06.')], R)

    # ---------------- 4.4
    doc('4.4', 'pass', 'ISMS Process Map and Interactions', 'pdf', meta('ISMS-PROC-01', CISO, CEO, '1.2', '2026-02-24'), [
        S('Processes in the ISMS', 'P1 Risk management (owner CISO) -> inputs: asset inventory, threat intel; outputs: risk register, RTP.', 'P2 Access management (IT Manager) -> inputs: HR joiner/leaver feed from Okta; outputs: quarterly access review.',
          'P3 Change and release management (CTO) -> inputs: GitHub pull requests; outputs: CAB records, deployment logs.', 'P4 Incident management (CISO) -> inputs: GuardDuty, EDR, staff reports; outputs: incident tickets, lessons learned.',
          'P5 Supplier management (Procurement) -> outputs: supplier register, annual reviews.', 'P6 Internal audit and management review (CISO/CEO).'),
        S('Interactions', 'Risk register feeds objectives (OBJ-2026-01..06). Audit findings feed corrective actions (CAR log). Metrics from P2-P4 feed the quarterly Management Review.'),
        S('Evidence of operation', 'Process KPIs reported in MR-2026-02 and MR-2026-03. ISMS manual v1.2 approved 2026-02-24 by Daniel Tan (CEO).')], A)
    doc('4.4', 'fail', 'Information Security Management Overview', 'docx', meta('ISMS-OVR-01', CISO, CEO, '1.0', '2026-02-10'), [
        S('Introduction', 'The company has established, implemented, maintained and continually improves an information security management system in line with international standards. The ISMS helps the organisation manage risk and meet its obligations.'),
        S('Approach', 'Management supports the ISMS and provides appropriate resources. Processes are defined as needed and improved over time. Employees are expected to follow procedures and report problems.'),
        S('Benefits', 'A well-run ISMS increases customer trust, reduces incidents and supports compliance.')], R)

    # ---------------- 5.1
    doc('5.1', 'pass', 'Top Management Commitment Statement and ISMS Sponsorship Record', 'docx', meta('ISMS-LEAD-01', CEO, 'Board of Directors', '1.0', '2026-01-19'), [
        S('Commitment', 'I, Daniel Tan, CEO, confirm that top management (a) ensured the information security policy and objectives are compatible with strategy, (b) integrated ISMS requirements into delivery processes, (c) made resources available, and (d) directs and supports persons to contribute to ISMS effectiveness.'),
        S('Evidence of action 2026', 'Approved ISMS budget SGD 186,000 (FY2026-B-014) on 2026-01-15.', 'Appointed Priya Nair as CISO with direct reporting to the CEO (appointment letter 2026-01-08).', 'Chaired Management Reviews on 2026-03-12, 2026-06-18 and 2026-09-24.', 'All-hands address on information security priorities, 2026-02-03 (attendance 58/62).'),
        S('Signatures', 'Signed: Daniel Tan, CEO - 2026-01-19. Countersigned: Chairman of the Board, Elaine Ong - 2026-01-19.')], A)
    doc('5.1', 'fail', 'Leadership Commitment Memo (draft)', 'docx', meta('ISMS-LEAD-00', CEO, '(not yet approved)', '0.3', '2026-02-02'), [
        S('Draft statement', 'Management is committed to information security and will provide the support the ISMS needs. We will take security seriously and encourage everyone to do the same.'),
        S('Status', 'Draft prepared by CISO for CEO review. Awaiting signature. Not yet circulated to staff or the Board.'),
        S('Signature', 'Name: ______________________   Date: ____________')], R)

    # ---------------- 5.2
    doc('5.2', 'pass', 'Information Security Policy v3.1 with Acknowledgement Report', 'pdf', meta('POL-ISP-01', CISO, CEO, '3.1', '2026-01-12'), [
        S('Policy statements', 'Maritime Services Pte. Ltd. commits to protecting client, vessel and employee information; to meeting PDPA, MPA and contractual requirements; to continual improvement of the ISMS; and to setting measurable objectives (OBJ-2026-01..06).'),
        S('Framework for objectives', 'Objectives are set annually, owned by named managers, and reviewed quarterly at Management Review.'),
        S('Communication', 'Published on the intranet 2026-01-15 and emailed to all staff. Acknowledgement report (MIGRC export 2026-01-31): 62 of 62 employees and 5 of 5 contractors acknowledged v3.1. Policy shared with customers via the trust portal on 2026-02-04.'),
        S('Approval', 'Approved and signed by Daniel Tan, CEO, 2026-01-12. Next review due 2027-01-12.')], A)
    doc('5.2', 'fail', 'Information Security Policy v1.0', 'pdf', meta('POL-ISP-01', CISO, CEO, '1.0', '2024-09-02'), [
        S('Purpose', 'This policy sets out the intent of the company to protect information.'),
        S('Statements', 'We will comply with laws. We will protect information. Staff must follow security rules.'),
        S('Review', 'This policy is reviewed every 12 months. Last review 2024-09-02. Review overdue.'),
        S('Approval', 'Approved: Daniel Tan, CEO, 2024-09-02.')], R)

    # ---------------- 5.3
    tab('5.3', 'pass', 'ISMS Roles, Responsibilities and Authorities (RACI)', 'xlsx',
        ['Activity', 'CEO', 'CISO', 'CTO', 'IT Manager', 'HR Lead', 'Asset owners', 'Authority document'],
        [['Approve ISMS policy and objectives', 'A', 'R', 'C', 'I', 'I', 'I', 'POL-ISP-01 s5'],
         ['Maintain risk register', 'I', 'A/R', 'C', 'C', 'I', 'R', 'ISMS-RISK-01'],
         ['Approve access to production', 'I', 'C', 'A', 'R', 'I', 'C', 'POL-AC-01 s4.3'],
         ['Incident declaration and escalation', 'I', 'A/R', 'R', 'C', 'I', 'I', 'POL-IR-01 s3'],
         ['Joiner/mover/leaver processing', 'I', 'C', 'I', 'R', 'A', 'I', 'HR-ONB-02'],
         ['Report ISMS performance to top management', 'A', 'R', 'C', 'C', 'C', 'I', 'ISMS-MR-01'],
         ['Appointed 2026-01-08 by CEO letter; roles communicated 2026-01-20; reviewed 2026-07-06', '', '', '', '', '', '', 'ISMS-ROLES-01 v2.0']], A)
    doc('5.3', 'fail', 'Sales Team Structure and Job Titles', 'docx', meta('HR-ORG-07', HR, CEO, '1.2', '2026-04-20'), [
        S('Sales organisation', 'Head of Sales: Rina Chua. Regional Account Managers (3): APAC, EMEA, Americas. Sales Engineers (2). Sales Operations Analyst (1).'),
        S('Responsibilities', 'Account Managers own renewal targets and pipeline hygiene in CRM. Sales Engineers support demos and technical questionnaires. Sales Operations prepare the weekly forecast.'),
        S('Commission', 'Plan year 1 January - 31 December 2026; quotas reviewed each quarter by the CEO.')], R)

    # ---------------- 6.1.1
    doc('6.1.1', 'pass', 'ISMS Risk and Opportunity Planning Procedure with 2026 Plan', 'pdf', meta('ISMS-RISK-00', CISO, CEO, '2.0', '2026-02-16'), [
        S('Approach', 'Issues (4.1) and interested-party requirements (4.2) are converted into risks and opportunities during the January planning workshop; results are recorded in the register and linked to a treatment action or objective.'),
        S('2026 planning output', 'Risks: 14 information security risks recorded (R-001..R-014); 3 rated high (score >= 15). Opportunities: OPP-01 ISO 27001 certification to unlock SGD 2.4M tender pipeline; OPP-02 automate evidence collection to cut audit effort by 30%; OPP-03 inherit AWS physical controls.'),
        S('Integration into ISMS', 'Actions integrated into the project plan (PRJ-ISMS-26) with owners and dates; effectiveness evaluated at quarterly Management Review (MR-2026-02, MR-2026-03).'),
        S('Approval', 'Approved by Daniel Tan (CEO) 2026-02-16; prepared by Priya Nair (CISO).')], A)
    doc('6.1.1', 'fail', 'Approach to Risks and Opportunities', 'pdf', meta('ISMS-RISK-00', CISO, CEO, '1.0', '2026-02-16'), [
        S('Overview', 'The organisation considers risks and opportunities when planning the ISMS. Risks are anything that could stop the organisation reaching its goals. Opportunities are positive things that could help.'),
        S('Process', 'Managers identify risks and opportunities regularly and decide what to do about them. Important ones are discussed with senior management where appropriate.'),
        S('Responsibility', 'Everyone is responsible for noticing risks. The ISMS owner keeps track.')], R)

    # ---------------- 6.1.2
    doc('6.1.2', 'pass', 'Information Security Risk Assessment Report H1 2026', 'pdf', meta('ISMS-RA-2026H1', CISO, CEO, '1.0', '2026-05-29'), [
        S('Criteria', 'Likelihood 1-5 and impact 1-5 (financial, legal, reputational); acceptance threshold: score < 9. Method ISMS-RISK-01 v2.1 produces comparable results by using a fixed scale per criterion.'),
        S('Scope and participants', '41 assets across AWS, endpoints, SaaS and people processes assessed 2026-04-20..2026-05-22 with 9 risk owners.'),
        S('Results', 'Total risks 14: high (>=15) 3, medium (9-14) 7, low 4. Top risks: R-001 AWS credential compromise (15), R-004 ransomware on platform (10), R-002 S3 data leakage (10).'),
        S('Owners and approval', 'Each risk has a named owner (CISO, CTO, IT Manager, Ops Lead). Risk assessment approved by Priya Nair (CISO); risk acceptance by Daniel Tan (CEO), 2026-05-29. Reassessment scheduled 2026-11-30 and on significant change.')], A)
    tab('6.1.2', 'fail', 'Office Asset Risk Listing', 'csv', ['Risk ID', 'Asset', 'Threat', 'Comment'],
        [['OR-01', 'Reception printer', 'Unattended printouts', 'Scope limited to HQ office assets'],
         ['OR-02', 'Meeting room TV', 'Screen sharing exposure', 'Production AWS excluded'],
         ['OR-03', 'Visitor Wi-Fi', 'Unauthorised access', 'Customer data not assessed'],
         ['OR-04', 'Shred bin', 'Document disposal', 'No likelihood or impact scoring'],
         ['OR-05', 'Whiteboards', 'Information left visible', 'Owner not assigned']], R)

    # ---------------- 6.1.3
    tab('6.1.3', 'pass', 'Risk Treatment Plan Tracker Q3 2026 and Statement of Applicability Cross-reference', 'xlsx',
        ['Risk ID', 'Treatment option', 'Controls selected (Annex A)', 'Action', 'Owner', 'Due', 'Status', 'Residual score', 'Residual accepted by / date'],
        [['R-001', 'Reduce', 'A.5.17, A.8.5', 'Enforce Okta phishing-resistant MFA', CISO, '2026-02-28', 'Done 2026-02-24', 6, 'Daniel Tan 2026-03-30'],
         ['R-002', 'Reduce', 'A.8.3, A.8.9', 'S3 block public access, Config rule', CTO, '2026-03-31', 'Done 2026-03-27', 4, 'Daniel Tan 2026-03-30'],
         ['R-003', 'Reduce', 'A.7.9, A.8.1', 'FileVault enforced via Jamf', ITM, '2026-03-15', 'Done 2026-03-12', 3, 'Daniel Tan 2026-03-30'],
         ['R-004', 'Reduce', 'A.8.13, A.8.7', 'Object Lock backups, CrowdStrike on 100% endpoints', CISO, '2026-05-31', 'Done 2026-05-22', 5, 'Daniel Tan 2026-06-18'],
         ['R-005', 'Reduce', 'A.5.19, A.5.22', 'Second AIS provider contract', 'Ops Lead', '2026-06-30', 'Done 2026-06-26', 4, 'Daniel Tan 2026-07-09'],
         ['R-009', 'Transfer', 'A.5.31', 'Cyber insurance SGD 5M renewed', 'CFO', '2026-08-31', 'Done 2026-08-19', 6, 'Daniel Tan 2026-09-24']], A)
    doc('6.1.3', 'fail', 'Risk Treatment Plan 2026 (pending acceptance)', 'docx', meta('ISMS-RTP-02', CISO, '', '0.9', '2026-06-04'), [
        S('Treatment decisions', 'R-001 Reduce - enforce MFA. R-002 Reduce - S3 hardening. R-004 Reduce - backups. R-005 Reduce - second supplier.'),
        S('Residual risk', 'Residual risk acceptance has not been recorded. Risk owners have not signed. Approval by top management is outstanding.'),
        S('Statement of Applicability', 'Not attached. SoA to be produced after treatment options are confirmed.'),
        S('Approver', '')], R)

    # ---------------- 6.2
    tab('6.2', 'pass', 'Information Security Objectives and KPI Plan 2026', 'xlsx',
        ['Objective ID', 'Objective', 'Measure', 'Target', 'Owner', 'Resources', 'Due', 'Evaluation', 'Q3 actual'],
        [['OBJ-2026-01', 'Enforce MFA for all workforce accounts', '% accounts with MFA', '100%', CISO, 'Okta licences', '2026-03-31', 'Monthly Okta report', '100%'],
         ['OBJ-2026-02', 'Close critical vulnerabilities fast', 'Critical findings open > 7 days', '0', CTO, 'Inspector, 0.5 FTE', 'Continuous', 'Weekly Inspector export', '0'],
         ['OBJ-2026-03', 'Security awareness completion', '% staff trained', '100% by 2026-06-30', HR, 'LearnSecure', '2026-06-30', 'Platform report', '100% (62/62)'],
         ['OBJ-2026-04', 'Incident response readiness', 'Tabletop exercises', '2 per year', CISO, '2 days each', '2026-11-30', 'Exercise reports', '1 done (2026-06-24)'],
         ['OBJ-2026-05', 'Backup restore success', 'Successful restores', '>= 95%', ITM, 'AWS Backup', 'Quarterly', 'Restore log', '100% (4/4)'],
         ['OBJ-2026-06', 'Achieve ISO 27001 certification', 'Stage 2 audit passed', 'Q1 2027', CISO, 'Budget FY2026-B-014', '2027-03-31', 'Management Review', 'Stage 1 booked 2026-12-08']], A)
    tab('6.2', 'fail', 'Security Goals 2025', 'xlsx',
        ['Goal', 'Description', 'Owner', 'Target date'],
        [['G1', 'Improve security', 'IT', '2025-12-31'], ['G2', 'Reduce incidents', '', '2025-12-31'],
         ['G3', 'Train staff', 'HR', '2025-12-31'], ['G4', 'Be compliant', '', '2025-12-31'], ['G5', 'Better backups', 'IT', '2025-12-31']], R)

    # ---------------- 6.3
    doc('6.3', 'pass', 'Change Planning Record CHG-2026-031 - Migration of Okta Tenant to Workforce Identity', 'docx', meta('CHG-2026-031', CTO, CISO, '1.1', '2026-07-22'), [
        S('Change description', 'Planned migration of workforce SSO from legacy Okta Classic policies to Okta Identity Engine, affecting 62 users and 18 integrated applications. Window 2026-08-01 20:00-23:00 SGT.'),
        S('ISMS impact assessment', 'Purpose and consequences: stronger phishing-resistant authentication (FIDO2). Risks: lockout of users (R-011) and loss of SSO to AWS console. Resources: 2 engineers, IT Manager on call. Responsibilities: change owner Marcus Lee; reviewer Priya Nair.'),
        S('Controls and rollback', 'Pilot with 6 users 2026-07-27 (no issues). Rollback: re-enable classic policy set exported 2026-07-21. Break-glass AWS admin verified.'),
        S('Approval and outcome', 'Approved by CAB 2026-07-24 (Priya Nair, Marcus Lee, Daniel Tan). Implemented 2026-08-01 with 0 incidents; post-implementation review 2026-08-05.')], A)
    doc('6.3', 'fail', 'Change Request Form', 'docx', meta('CHG-[number]', '[Requester]', '[Approver]', '[x.y]', '[date]'), [
        S('Change description', '[Describe the change]'), S('Reason for change', '[Business / security reason]'),
        S('Impact on the ISMS', '[Describe impact on risks, resources and responsibilities]'),
        S('Rollback plan', '[Describe rollback]'), S('Approval', 'CAB decision: [Approved / Rejected]   Date: [dd/mm/yyyy]')], R)

    # ---------------- 7.1
    tab('7.1', 'pass', 'ISMS Resource Allocation and Budget FY2026', 'xlsx',
        ['Line', 'Resource', 'Type', 'Allocation', 'Budget (SGD)', 'Owner', 'Approved by / date'],
        [['B-014-01', 'ISMS staffing: CISO (1.0 FTE), ISMS analyst (0.5 FTE)', 'People', '1.5 FTE', 96000, CISO, 'Daniel Tan 2026-01-15'],
         ['B-014-02', 'Okta, CrowdStrike, Jamf licences', 'Technology', '62 seats', 38500, ITM, 'Daniel Tan 2026-01-15'],
         ['B-014-03', 'AWS Inspector, GuardDuty, Config', 'Technology', 'Prod + staging', 14200, CTO, 'Daniel Tan 2026-01-15'],
         ['B-014-04', 'LearnSecure awareness platform', 'Training', '62 users', 4800, HR, 'Daniel Tan 2026-01-15'],
         ['B-014-05', 'Certification audit (stage 1 + 2)', 'External', '8 audit days', 22000, CISO, 'Daniel Tan 2026-01-15'],
         ['B-014-06', 'Penetration assessment (annual)', 'External', '1 engagement', 10500, CTO, 'Daniel Tan 2026-01-15']], A)
    tab('7.1', 'fail', 'Marketing Programme Budget 2024', 'xlsx',
        ['Line', 'Item', 'Channel', 'Budget (SGD)', 'Owner', 'Period'],
        [['M-01', 'SEA Maritime Expo booth', 'Events', 28000, 'Head of Marketing', 'FY2024'], ['M-02', 'Paid search', 'Digital', 18000, 'Head of Marketing', 'FY2024'],
         ['M-03', 'LinkedIn campaigns', 'Digital', 9500, 'Head of Marketing', 'FY2024'], ['M-04', 'Brand refresh', 'Design', 12000, 'Head of Marketing', 'FY2024'],
         ['M-05', 'Webinar series', 'Content', 6000, 'Head of Marketing', 'FY2024']], R)

    # ---------------- 7.2
    tab('7.2', 'pass', 'Security Competence Matrix and Training Records 2026', 'csv',
        ['Employee', 'Role', 'Required competence', 'Evidence', 'Completed', 'Valid until', 'Verified by'],
        [['Priya Nair', 'CISO', 'ISO 27001 Lead Implementer', 'PECB cert LI-884213', '2025-11-14', '2028-11-14', 'Grace Lim'],
         ['Aisha Rahman', 'IT Manager', 'AWS Security Specialty', 'Credly SCS-7731', '2026-02-27', '2029-02-27', 'Priya Nair'],
         ['Marcus Lee', 'CTO', 'Secure SDLC (OWASP)', 'Course cert 2026-03-19', '2026-03-19', '2027-03-19', 'Priya Nair'],
         ['Tom Wong', 'DevOps Engineer', 'AWS Solutions Architect Pro', 'Credly SAP-2290', '2026-04-08', '2029-04-08', 'Marcus Lee'],
         ['Grace Lim', 'HR Lead', 'PDPA practitioner', 'DPO cert PDPA-1180', '2026-01-30', '2028-01-30', 'Priya Nair'],
         ['Internal auditors (3)', 'Auditors', 'ISO 27001 Internal Auditor', 'IRCA certs', '2026-05-20', '2029-05-20', 'Priya Nair']], A)
    doc('7.2', 'fail', 'Security Skills Assessment Results - Engineering', 'docx', meta('HR-SKL-09', HR, '', '1.0', '2026-08-14'), [
        S('Assessment', 'Secure coding assessment taken by 14 engineers on 2026-08-11, pass mark 70%.'),
        S('Results', 'Only 5 of 14 engineers reached the pass mark. Average score 58%. Lowest scores in injection (41%) and secrets management (39%). 9 engineers are therefore not demonstrably competent for production changes.'),
        S('Actions', 'No remediation plan agreed. No re-assessment date set. Findings open.')], R)

    # ---------------- 7.3
    doc('7.3', 'pass', 'Security Awareness Programme Report 2026', 'pdf', meta('ISMS-AWR-26', HR, CISO, '1.0', '2026-07-02'), [
        S('Programme', 'Annual awareness course "Security Basics 2026" (45 min, 8 modules) assigned 2026-05-04 to 62 employees and 5 contractors via LearnSecure. Content covers the information security policy, acceptable use, phishing, data handling, incident reporting and the consequences of non-conformity.'),
        S('Results', 'Completion 67/67 (100%) by 2026-06-18. Average assessment score 91%. New joiners (8 in 2026) complete the course within 14 days of start; average 6 days.'),
        S('Phishing exercise', 'Simulated phishing 2026-06-10: 67 emails, 5 clicks (7.5%), 4 reported to security mailbox within 1 hour. Follow-up coaching delivered 2026-06-17.'),
        S('Approval', 'Report prepared by Grace Lim (HR Lead), approved by Priya Nair (CISO) 2026-07-02.')], A)
    tab('7.3', 'fail', 'Awareness Session Attendance - Q1', 'csv', ['Employee', 'Department', 'Session date', 'Attended'],
        [['Aisha Rahman', 'IT', '2026-03-10', 'Yes'], ['Tom Wong', 'Engineering', '2026-03-10', 'Yes'], ['Rina Chua', 'Sales', '2026-03-10', 'No'],
         ['Alvin Koh', 'Operations', '2026-03-10', 'No'], ['Jia Hui Ng', 'Finance', '2026-03-10', 'No'], ['Sara Ibrahim', 'Operations', '2026-03-10', 'No'],
         ['Summary', '38 of 62 attended', 'Campaign closed 2026-03-31', '24 staff not trained']], R)

    # ---------------- 7.4
    tab('7.4', 'pass', 'ISMS Communication Plan 2026', 'xlsx',
        ['What', 'When', 'To whom', 'Who communicates', 'Channel', 'Evidence of delivery'],
        [['Information security policy update', 'Jan, on change', 'All staff, contractors', 'CISO', 'Email + intranet', 'Acknowledgement report 2026-01-31'],
         ['Quarterly ISMS performance', 'Quarterly', 'Top management', 'CISO', 'Management Review', 'MR-2026-02/03/04 minutes'],
         ['Security incident notification', 'Within 24h of declaration', 'Affected customers', 'CISO / CEO', 'Email, trust portal', 'IR-2026-004 customer notice 2026-06-12'],
         ['Regulatory breach notification', 'Within 3 days', 'PDPC / MPA', 'CISO', 'PDPC portal', 'Procedure POL-IR-01 s7'],
         ['Phishing and threat advisories', 'Monthly', 'All staff', 'Security team', 'Slack #security', 'Monthly digests Jan-Nov'],
         ['Supplier security requirements', 'At onboarding / renewal', 'Suppliers', 'Procurement', 'Contract schedule', 'SUP-001..004']], A)
    doc('7.4', 'fail', 'Communications Guidelines', 'docx', meta('COM-GEN-01', 'Head of Marketing', 'CEO', '1.0', '2026-01-09'), [
        S('Principles', 'Communicate clearly, consistently and promptly. Use the right channel for the audience. Be transparent while protecting confidential details.'),
        S('Channels', 'Email, Slack, intranet and town halls can all be used where appropriate. Managers decide what to share with their teams.'),
        S('Tips', 'Keep messages short. Check spelling. Ask for feedback.')], R)

    # ---------------- 7.5.1
    doc('7.5.1', 'pass', 'Documented Information Procedure and Master Document List', 'pdf', meta('ISMS-DOC-01', CISO, CEO, '2.0', '2026-02-18'), [
        S('Scope', 'Applies to all documented information required by ISO 27001 and determined necessary for ISMS effectiveness; 46 documents registered in SharePoint library "ISMS Controlled".'),
        S('Master list excerpt', 'POL-ISP-01 Information Security Policy v3.1 (2026-01-12); ISMS-SCOPE-02 v2.0 (2026-04-14); ISMS-RISK-01 Risk Methodology v2.1; ISMS-RTP-01 Risk Treatment Plan v4.0; ISMS-SOA-01 SoA v4.0; POL-AC-01 v2.2; POL-IR-01 v2.3; ISMS-AUD-01 Audit Programme v1.0.'),
        S('Level of detail', 'Documents are scaled to the size of the organisation (62 staff), complexity of processes and competence of people; templates TPL-001..TPL-012 define the minimum content.'),
        S('Approval', 'Procedure approved by Daniel Tan (CEO) on 2026-02-18; owner Priya Nair (CISO).')], A)
    doc('7.5.1', 'fail', 'Documentation Standard (unsigned)', 'pdf', meta('ISMS-DOC-00', CISO, '', '0.4', '2026-02-03'), [
        S('Statement', 'The ISMS includes documented information as required by the standard and as needed by the organisation.'),
        S('Master list', 'A master list will be maintained listing all documents, owners and versions. Initial list to be created.'),
        S('Approval', 'Approval signature: [not signed]. No approver identified.')], R)

    # ---------------- 7.5.2
    tab('7.5.2', 'pass', 'Document Revision and Approval Log 2026', 'xlsx',
        ['Doc ID', 'Title', 'Version', 'Change description', 'Author', 'Reviewer', 'Approved by', 'Approval date', 'Format / identification'],
        [['POL-ISP-01', 'Information Security Policy', '3.1', 'Added AI usage clause', CISO, CTO, CEO, '2026-01-12', 'PDF, header ID+version'],
         ['POL-AC-01', 'Access Control Policy', '2.2', 'Quarterly review cadence', CISO, ITM, CEO, '2026-02-20', 'PDF, header ID+version'],
         ['POL-CRY-01', 'Cryptography Policy', '1.1', 'TLS 1.2 minimum', CTO, CISO, CEO, '2026-05-09', 'PDF, header ID+version'],
         ['POL-IR-01', 'Incident Response Plan', '2.3', 'MPA reporting timeline', CISO, CTO, CEO, '2026-06-01', 'PDF, header ID+version'],
         ['ISMS-AUD-01', 'Internal Audit Programme', '1.0', 'Initial issue', CISO, CEO, CEO, '2026-03-02', 'XLSX, title sheet'],
         ['POL-SUP-01', 'Supplier Security Policy', '1.6', 'Added sub-processor clause', 'Procurement', CISO, CEO, '2026-07-14', 'PDF, header ID+version']], A)
    tab('7.5.2', 'fail', 'Policy Change Log', 'csv', ['Doc ID', 'Version', 'Change', 'Author', 'Reviewer', 'Approved by', 'Date'],
        [['POL-ISP-01', '3.1', 'Updated', 'CISO', '', '', ''], ['POL-AC-01', '2.2', 'Updated', 'CISO', '', '', ''],
         ['POL-CRY-01', '1.1', 'Minor edits', 'CTO', '', '', ''], ['POL-IR-01', '2.3', 'Updated', 'CISO', '', '', ''],
         ['POL-SUP-01', '1.6', 'Updated', 'Procurement', '', '', '']], R)

    # ---------------- 7.5.3
    img('7.5.3', 'pass', 'SharePoint ISMS Library - Permissions and Version History', 'png', A,
        'Microsoft SharePoint', 'https://maritimeservices.sharepoint.com/sites/ISMS/_layouts/15/user.aspx', '#036c70', AWS,
        'ISMS Controlled - Permissions (versioning: major/minor, 50 versions)',
        (['Group', 'Permission level', 'Members', 'Status'], [320, 300, 220, 220]),
        [['ISMS Owners', 'Full Control', 2, 'Active'], ['All Employees', 'Read', 62, 'Active'], ['Document Approvers', 'Edit', 3, 'Active'], ['External sharing', 'Disabled', 0, 'Disabled']],
        banner='Check-out required: Yes. Retention label ISMS-7Y applied to 46 of 46 documents.')
    img('7.5.3', 'fail', 'SharePoint Policies Folder - Sharing Settings', 'png', R,
        'Microsoft SharePoint', 'https://maritimeservices.sharepoint.com/sites/Shared/_layouts/15/user.aspx', '#036c70', AWS,
        'Shared Documents / Policies - Permissions',
        (['Group', 'Permission level', 'Members', 'Status'], [320, 300, 220, 220]),
        [['Everyone except external users', 'Edit', 62, 'Open'], ['Anyone with the link', 'Edit', 'n/a', 'Open'], ['Version history', 'Disabled', 0, 'Disabled']])

    # ---------------- 8.1
    doc('8.1', 'pass', 'Operational Planning and Control Plan 2026 - Platform Delivery', 'pdf', meta('ISMS-OPS-01', CTO, CEO, '1.2', '2026-02-27'), [
        S('Process criteria', 'Release management (SOP-REL-03): every production change needs a pull request with 1 reviewer, passing CI (unit, SAST via CodeQL, dependency scan), and CAB approval for medium/high changes. Deployments via GitHub Actions OIDC to AWS.'),
        S('Control of planned changes', 'Change log CHG-2026-001..CHG-2026-044 reviewed monthly by the CISO; 44 changes in H1, 0 unauthorised changes detected by CloudTrail comparison.'),
        S('Documented information', 'Deployment records retained 24 months in GitHub and CloudTrail; evidence reviewed in Management Review MR-2026-02.'),
        S('Outsourced processes', 'Third-party AIS feed (SUP-003) and AWS controlled via supplier agreements and annual review (done 2026-07-14).'),
        S('Approval', 'Approved by Daniel Tan, CEO on 2026-02-27.')], A)
    doc('8.1', 'fail', 'Marketing Campaign Operational Plan Q4', 'docx', meta('MKT-OP-12', 'Head of Marketing', 'CEO', '1.0', '2026-09-30'), [
        S('Campaign', 'Q4 push for MarineOps module launch, targeting 120 shipping companies in APAC.'),
        S('Planning', 'Weeks 1-2 content production; weeks 3-8 email and LinkedIn; week 9 Singapore Maritime Week booth; week 10 follow-up calls.'),
        S('Controls', 'Brand approval by Marketing Lead before publication. Weekly funnel report to CEO.')], R)

    # ---------------- 8.2
    doc('8.2', 'pass', 'Risk Assessment Execution Record - Q3 2026 Cycle', 'docx', meta('ISMS-RA-2026Q3', CISO, CEO, '1.0', '2026-09-18'), [
        S('Trigger and timing', 'Planned quarterly reassessment plus change trigger CHG-2026-031 (Okta migration). Workshop 2026-09-08 and 2026-09-10; 11 participants.'),
        S('Results', '3 new risks added (R-015 container image supply chain, R-016 Okta service outage, R-017 contractor laptop use). 2 risks re-scored down after treatment (R-001 15->6, R-004 10->5). Register now holds 17 risks: 2 high, 8 medium, 7 low.'),
        S('Consistency', 'Same criteria (ISMS-RISK-01 v2.1) applied; scoring reviewed by 2 assessors with variance < 1 point on 15 of 17 risks.'),
        S('Retention', 'Workshop notes and register v2026-09-18 retained in SharePoint. Approved: Priya Nair (CISO) 2026-09-18; risk owners acknowledged by email 2026-09-20.')], A)
    doc('8.2', 'fail', 'Risk Assessment Record Q4 2024', 'docx', meta('ISMS-RA-2024Q4', CISO, CEO, '1.0', '2024-12-06'), [
        S('Summary', 'Annual risk assessment completed 2024-12-02 covering the platform and office. 9 risks identified, 2 high.'),
        S('Next assessment', 'Planned for Q4 2025.'),
        S('Approval', 'Approved by Daniel Tan, 2024-12-06.')], R)

    # ---------------- 8.3
    tab('8.3', 'pass', 'Risk Treatment Implementation Evidence Log 2026', 'xlsx',
        ['Risk ID', 'Treatment implemented', 'Evidence reference', 'Verified by', 'Verification date', 'Result', 'Residual score'],
        [['R-001', 'Okta MFA 100% of 62 users', 'Okta report OKT-2026-02-24', CISO, '2026-02-26', 'Effective', 6],
         ['R-002', 'S3 Block Public Access on all 38 buckets', 'AWS Config conformance 2026-03-27', CTO, '2026-03-30', 'Effective', 4],
         ['R-003', 'FileVault on 66 of 66 Macs', 'Jamf report JMF-0312', ITM, '2026-03-14', 'Effective', 3],
         ['R-004', 'Object Lock vault + EDR 100%', 'AWS Backup vault ms-prod-vault; EDR console 2026-05-22', CISO, '2026-05-25', 'Effective', 5],
         ['R-005', 'Secondary AIS provider live', 'Contract SUP-003B; switchover drill 2026-06-26', 'Ops Lead', '2026-06-28', 'Effective', 4],
         ['R-015', 'Signed container images (cosign) in CI', 'GitHub Actions run #4412', CTO, '2026-10-02', 'Effective', 4]], A)
    tab('8.3', 'fail', 'Treatment Action Tracker', 'xlsx',
        ['Risk ID', 'Action', 'Owner', 'Due date', 'Status', 'Comment'],
        [['R-001', 'Enforce MFA', '', '2026-02-28', 'Overdue', 'Owner not confirmed'], ['R-002', 'S3 hardening', 'CTO', '2026-03-31', 'Overdue', 'Config rule not deployed'],
         ['R-004', 'Immutable backups', '', '2026-05-31', 'Open', 'Budget not released'], ['R-005', 'Second provider', 'Ops Lead', '2026-06-30', 'Open', 'No contract'],
         ['R-009', 'Cyber insurance', '', '2026-08-31', 'Open', 'Not started']], R)

    # ---------------- 9.1
    tab('9.1', 'pass', 'ISMS Performance Metrics - Monthly Monitoring Results Jan-Oct 2026', 'csv',
        ['Month', 'MFA coverage %', 'Critical vulns open >7d', 'Backup restore success %', 'Incidents (sev1-2)', 'Awareness completion %', 'Reviewed by', 'Review date'],
        [['2026-01', 96, 1, 100, 0, 71, CISO, '2026-02-06'], ['2026-02', 100, 0, 100, 0, 71, CISO, '2026-03-05'], ['2026-03', 100, 0, 100, 1, 74, CISO, '2026-04-07'],
         ['2026-04', 100, 0, 100, 0, 80, CISO, '2026-05-06'], ['2026-05', 100, 0, 96, 0, 92, CISO, '2026-06-04'], ['2026-06', 100, 0, 100, 1, 100, CISO, '2026-07-03'],
         ['2026-07', 100, 0, 100, 0, 100, CISO, '2026-08-05'], ['2026-08', 100, 0, 100, 0, 100, CISO, '2026-09-03'], ['2026-09', 100, 0, 100, 0, 100, CISO, '2026-10-06'],
         ['2026-10', 100, 0, 100, 0, 100, CISO, '2026-11-04']], A)
    doc('9.1', 'fail', 'Security Monitoring Approach', 'docx', meta('ISMS-MON-00', CISO, CEO, '1.0', '2026-03-01'), [
        S('Approach', 'Security performance is monitored and measured where practical. Information from tools and reports is reviewed by the security team from time to time to decide whether the ISMS is working.'),
        S('Metrics', 'Suitable metrics will be selected. Results are analysed and shared with management when needed.'),
        S('Evaluation', 'The effectiveness of the ISMS is evaluated annually.')], R)

    # ---------------- 9.2.1
    doc('9.2.1', 'pass', 'Internal Audit Report IA-2026-01 - Access Control and Operations Security', 'pdf', meta('IA-2026-01', 'Rohan Mehta (Internal Auditor)', CEO, '1.0', '2026-08-28'), [
        S('Objective, scope, criteria', 'Audit of ISO 27001:2022 Annex A 5.15-5.18 and 8.2-8.9 and clauses 9.1 and 10.2 against POL-AC-01 v2.2. Fieldwork 2026-08-17..2026-08-21. Auditor independent of the process (Rohan Mehta, Finance; IRCA certified).'),
        S('Findings', 'Conformities: 14 controls reviewed, 11 conforming. Minor NC-2026-07: 3 of 25 leaver accounts disabled after 3 days (policy: 1 day). Minor NC-2026-08: privileged access review for Q2 signed late (2026-07-19). OFI-2026-03: add Jamf compliance report to monthly metrics.'),
        S('Reporting', 'Report issued to process owners and top management 2026-08-28; corrective actions CAR-2026-07/08 raised with due date 2026-10-15; closed 2026-10-09 and verified by the auditor 2026-10-20.'),
        S('Sign-off', 'Auditor: Rohan Mehta, 2026-08-28. Reviewed and accepted: Priya Nair (CISO) and Daniel Tan (CEO), 2026-08-31.')], A)
    doc('9.2.1', 'fail', 'Internal Audit Report - Draft for Review', 'docx', meta('IA-2026-02', 'Internal Auditor', '(none)', 'draft', '2026-09-12'), [
        S('Scope', 'Review of backup and supplier management controls.'),
        S('Observations', 'Backup jobs run daily. Supplier register exists but has not been refreshed. Some staff were unaware of the incident reporting contact.'),
        S('Status', 'Draft. Not issued to management. No auditor sign-off or management response. Findings not classified.')], R)

    # ---------------- 9.2.2
    tab('9.2.2', 'pass', 'Internal Audit Programme 2026', 'xlsx',
        ['Audit ID', 'Scope (clauses / controls)', 'Criteria', 'Method', 'Auditor', 'Planned', 'Actual', 'Report', 'Status'],
        [['IA-2026-01', 'A.5.15-5.18, A.8.2-8.9, 9.1, 10.2', 'POL-AC-01, ISO 27001', 'Interview, record review', 'Rohan Mehta', '2026-08-17', '2026-08-17', 'IA-2026-01', 'Completed'],
         ['IA-2026-02', 'A.5.19-5.23 suppliers, A.8.13 backup', 'POL-SUP-01, POL-BCK-01', 'Document review, walkthrough', 'Li Wei Tan', '2026-09-14', '2026-09-14', 'IA-2026-02', 'Completed'],
         ['IA-2026-03', 'Clauses 4-7, 9.3, A.6, A.7', 'ISO 27001 cl 4-7', 'Interview', 'Rohan Mehta', '2026-10-12', '2026-10-12', 'IA-2026-03', 'Completed'],
         ['IA-2026-04', 'A.8.15-8.28 development security', 'SOP-REL-03', 'Review of 25 pull requests', 'Li Wei Tan', '2026-11-23', '', '', 'Scheduled'],
         ['Frequency', 'All ISMS scope covered at least once per 12 months; results of previous audits and risk ratings drive priority', '', '', 'Approved by Daniel Tan', '2026-03-02', '', '', '']], A)
    tab('9.2.2', 'fail', 'Audit Schedule 2025', 'xlsx',
        ['Audit', 'Area', 'Auditor', 'Planned month', 'Status'],
        [['A1', 'Access control', 'TBC', 'Mar 2025', 'Not performed'], ['A2', 'Suppliers', 'TBC', 'Jun 2025', 'Not performed'], ['A3', 'Backup', 'TBC', 'Sep 2025', 'Not performed'],
         ['A4', 'HR security', 'TBC', 'Nov 2025', 'Not performed'], ['A5', 'Physical', 'TBC', 'Dec 2025', 'Not performed']], R)

    # ---------------- 9.3.1
    doc('9.3.1', 'pass', 'Management Review Minutes MR-2026-03', 'pdf', meta('MR-2026-03', CISO, CEO, '1.0', '2026-06-18'), [
        S('Meeting', 'Held 2026-06-18, 10:00-12:15 SGT, HQ boardroom. Chair: Daniel Tan (CEO). Attendees: Priya Nair (CISO), Marcus Lee (CTO), Aisha Rahman (IT Manager), Grace Lim (HR Lead), Ruth Tan (CFO). Quorum met; apologies: none.'),
        S('Agenda', '1. Actions from MR-2026-02  2. Audit and KPI results  3. Risk register and treatment  4. Resources  5. Improvements and objectives.'),
        S('Decisions', 'D1: approve residual risk for R-004 (after Object Lock go-live). D2: extend ISMS analyst to 1.0 FTE from 2026-07-01 (+SGD 38,000). D3: bring forward the first internal audit to August. D4: approve tabletop exercise on 2026-06-24.'),
        S('Sign-off', 'Minutes recorded by Priya Nair; approved by Daniel Tan, 2026-06-20. Review cadence: quarterly; next MR-2026-04 on 2026-09-24.')], A)
    doc('9.3.1', 'fail', 'Management Meeting Notes - 2 March 2026', 'docx', meta('MGT-2026-02', 'Executive Assistant', '', '1.0', '2026-03-02'), [
        S('Attendees', 'Ruth Tan (CFO), Head of Sales, Head of Operations. CEO and CISO absent.'),
        S('Discussion', 'Quarterly revenue, hiring plan, customer renewals and office lease. Information security mentioned briefly under AOB: "ISO project continues".'),
        S('Actions', 'None recorded.')], R)

    # ---------------- 9.3.2
    doc('9.3.2', 'pass', 'Management Review Input Pack - Q3 2026', 'docx', meta('MR-2026-04-IN', CISO, CEO, '1.0', '2026-09-21'), [
        S('(a) Status of previous actions', '9 of 10 actions from MR-2026-03 closed; 1 in progress (tabletop #2, due 2026-11-30).'),
        S('(b) Changes in issues', 'New MPA circular 2026-014; two new enterprise customers requiring ISO 27001; AIS supplier price change.'),
        S('(c) Performance and trends', 'Nonconformities: 5 raised, 4 closed. Monitoring: MFA 100%, critical vulns 0, restore success 100%. Audit results: IA-2026-01/02 closed with 6 minor NCs. Objectives: 4 of 6 on target.'),
        S('(d) Feedback from interested parties', 'Customer security questionnaires: 17 answered, average turnaround 3.2 days; 1 complaint on report latency.'),
        S('(e) Risk assessment and treatment', '17 risks; 2 high; 14 of 17 treatments implemented.'),
        S('(f) Opportunities for improvement', 'OFI-2026-03 Jamf metric; automate evidence collection via MIGRC.'),
        S('Distribution', 'Issued to Daniel Tan, Marcus Lee, Ruth Tan, Grace Lim, Aisha Rahman on 2026-09-21; approved for tabling by Priya Nair.')], A)
    doc('9.3.2', 'fail', 'Quarterly Business Review - Sales and Finance', 'pdf', meta('QBR-2026-Q3', 'Ruth Tan (CFO)', 'Daniel Tan (CEO)', '1.0', '2026-10-05'), [
        S('Revenue', 'Q3 revenue SGD 2.31M (+14% QoQ). ARR SGD 8.9M. Net revenue retention 108%.'),
        S('Pipeline', 'Weighted pipeline SGD 3.4M; 6 deals in contract stage; win rate 31%.'),
        S('Costs', 'Opex SGD 1.62M; headcount 62; cloud spend SGD 210k (+6%).'),
        S('Outlook', 'Q4 forecast SGD 2.5M; hiring freeze for non-engineering roles.')], R)

    # ---------------- 9.3.3
    tab('9.3.3', 'pass', 'Management Review Outputs and Action Register 2026', 'xlsx',
        ['Action ID', 'Review', 'Decision / output', 'Type', 'Owner', 'Due', 'Status', 'Closure date'],
        [['MR3-01', 'MR-2026-03', 'Approve residual risk R-004', 'Risk decision', CEO, '2026-06-18', 'Closed', '2026-06-18'],
         ['MR3-02', 'MR-2026-03', 'ISMS analyst to 1.0 FTE (+SGD 38,000)', 'Resource', CEO, '2026-07-01', 'Closed', '2026-07-01'],
         ['MR3-03', 'MR-2026-03', 'Bring internal audit forward to August', 'Improvement', CISO, '2026-08-17', 'Closed', '2026-08-17'],
         ['MR3-04', 'MR-2026-03', 'Tabletop exercise 2026-06-24', 'Improvement', CISO, '2026-06-24', 'Closed', '2026-06-24'],
         ['MR4-01', 'MR-2026-04', 'Fund MIGRC evidence automation (SGD 12,000)', 'Resource', ITM, '2026-10-31', 'Closed', '2026-10-28'],
         ['MR4-02', 'MR-2026-04', 'Run tabletop #2 (ransomware)', 'Improvement', CISO, '2026-11-30', 'In progress', '']], A)
    tab('9.3.3', 'fail', 'Review Action Template', 'csv', ['Action ID', 'Decision', 'Owner', 'Due', 'Status'],
        [['[ID]', '[Decision from management review]', '[Name]', '[dd/mm/yyyy]', '[Open/Closed]'],
         ['[ID]', '[Decision from management review]', '[Name]', '[dd/mm/yyyy]', '[Open/Closed]'],
         ['[ID]', '[Decision from management review]', '[Name]', '[dd/mm/yyyy]', '[Open/Closed]'],
         ['[ID]', '[Decision from management review]', '[Name]', '[dd/mm/yyyy]', '[Open/Closed]'],
         ['[ID]', '[Decision from management review]', '[Name]', '[dd/mm/yyyy]', '[Open/Closed]']], R)

    # ---------------- 10.1
    tab('10.1', 'pass', 'Continual Improvement Register 2026', 'xlsx',
        ['Ref', 'Source', 'Improvement', 'Owner', 'Raised', 'Completed', 'Benefit measured'],
        [['CI-001', 'MR-2026-02', 'Automate leaver account disablement via Okta workflow', ITM, '2026-03-12', '2026-05-14', 'Leaver disable time 3 days -> 15 minutes'],
         ['CI-002', 'Internal audit IA-2026-01', 'Add Jamf compliance to monthly metrics', ITM, '2026-08-28', '2026-09-30', 'Jamf compliance 98.5% now reported'],
         ['CI-003', 'Incident IR-2026-004', 'Phishing report button in M365', CISO, '2026-06-14', '2026-07-08', 'Reported phish rate 20% -> 80%'],
         ['CI-004', 'Customer feedback', 'Trust portal with policy downloads', CISO, '2026-04-02', '2026-06-01', 'Questionnaire turnaround 6.1 -> 3.2 days'],
         ['CI-005', 'MR-2026-04', 'Evidence automation in MIGRC', ITM, '2026-09-24', '2026-10-28', 'Evidence prep effort -30%']], A)
    tab('10.1', 'fail', 'Improvement Ideas Log 2024', 'xlsx',
        ['Ref', 'Idea', 'Raised by', 'Date', 'Status'],
        [['I-01', 'Password manager', 'IT', '2024-02-11', 'Idea'], ['I-02', 'Quarterly pizza security quiz', 'HR', '2024-03-04', 'Idea'],
         ['I-03', 'Review firewall rules', 'IT', '2024-05-19', 'Idea'], ['I-04', 'Better onboarding', 'HR', '2024-07-22', 'Idea'], ['I-05', 'Backup report', 'IT', '2024-09-30', 'Idea']], R)

    # ---------------- 10.2
    doc('10.2', 'pass', 'Corrective Action Report CAR-2026-007 - Late Leaver Account Disablement', 'pdf', meta('CAR-2026-007', ITM, CISO, '1.0', '2026-10-20'), [
        S('Nonconformity', 'Raised from internal audit IA-2026-01 (NC-2026-07, 2026-08-28): 3 of 25 leaver accounts disabled after 3 days against the 1-day requirement in POL-AC-01 s6.2.'),
        S('Immediate correction', 'The 3 accounts were disabled on 2026-08-29; sign-in logs reviewed, no activity after termination date.'),
        S('Root cause', '5-Whys: HR notification sent by email to a shared mailbox checked only on weekdays; no automation between HR system and Okta.'),
        S('Corrective action', 'Okta workflow triggered by HR system termination date (live 2026-05-14 for new leavers; back-filled 2026-09-18); HR checklist updated. Owner Aisha Rahman, due 2026-10-15, done 2026-10-09.'),
        S('Effectiveness review', 'Auditor verified 2026-10-20: 12 leavers Sep-Oct all disabled within 1 hour. Closed by Priya Nair (CISO) on 2026-10-20.')], A)
    doc('10.2', 'fail', 'Nonconformity Report NC-2026-011 - Backup Restore Exceptions', 'docx', meta('NC-2026-011', ITM, '', '1.0', '2026-03-09'), [
        S('Nonconformity', 'Quarterly restore exercise on 2026-03-04 recovered 2 of 5 databases within the 4-hour objective. Three restores exceeded the time or returned incomplete data.'),
        S('Root cause', 'Not yet determined.'),
        S('Corrective action', 'None assigned. Due date not set. Previous corrective action CAR-2025-004 for the same issue was marked closed but the same fault recurred, so the action was not effective.'),
        S('Status', 'Open for more than 8 months at report date 2026-11-12.')], R)

    # ---------------- A.5.1
    doc('A.5.1', 'pass', 'Policy Publication and Acknowledgement Record 2026', 'docx', meta('POL-REC-26', CISO, CEO, '1.0', '2026-03-06'), [
        S('Policies defined, approved and published', 'Information Security Policy POL-ISP-01 v3.1 signed by Daniel Tan (CEO) on 2026-01-12. Topic-specific policies approved by CEO: Access Control v2.2 (2026-02-20), Acceptable Use v2.0 (2026-03-05), Backup and Recovery v1.4, Cryptography v1.1, Incident Response v2.3, Supplier Security v1.6.'),
        S('Communication', 'Published to the intranet and trust portal; announced by email 2026-01-15 and 2026-03-06. MIGRC acknowledgement report 2026-03-10: 62 of 62 employees acknowledged all 7 policies; 5 of 5 contractors acknowledged ISP and AUP.'),
        S('Review', 'Planned review dates recorded in the policy register; all policies are reviewed at least annually or on significant change. Trigger reviews 2026: POL-IR-01 after IR-2026-004 (2026-06-01).'),
        S('Approval', 'Record prepared by Priya Nair (CISO); approved Daniel Tan (CEO), 2026-03-06.')], A)
    tab('A.5.1', 'fail', 'Policy Document Inventory', 'csv', ['Policy', 'ID', 'Version', 'Owner', 'Last review', 'Approver'],
        [['Information Security Policy', 'POL-ISP-01', '1.0', 'CISO', '2024-09-02', 'CEO'], ['Access Control Policy', 'POL-AC-01', '1.0', 'CISO', '2024-09-02', 'CEO'],
         ['Acceptable Use Policy', 'POL-AUP-01', '1.1', 'HR Lead', '2024-10-15', 'CEO'], ['Backup Policy', 'POL-BCK-01', '1.0', 'IT Manager', '2024-10-15', 'CEO'],
         ['Cryptography Policy', 'POL-CRY-01', '1.0', 'CTO', '2024-11-20', ''], ['Incident Response Plan', 'POL-IR-01', '1.2', 'CISO', '2024-11-20', 'CEO']], R)
    return M


if __name__ == '__main__':
    out = sys.argv[1]
    m = build(out)
    json.dump(m, open(os.path.join(out, 'manifest.json'), 'w'), indent=1)
    print(len(m), 'items ->', out)
