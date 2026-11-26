"""ISO 27001:2022 evidence, part 4 (Annex A 8.6 - 8.34 minus controls already paired). Maritime Services org."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from gen_iso_evidence import pdf, dcx, xlsx, csvf, png, shot, photo, meta

AWS = ['Dashboard', 'Services', 'Config', 'CloudTrail', 'Security Hub']
BAD = ('test', 'sample', 'fake', 'fail')


def build(out):
    os.makedirs(out, exist_ok=True)
    M = []

    def add(code, title, desc, kind, fmt, *a, expect='Approved', src='Manual Upload', **kw):
        fn = code.replace('.', '_') + ('_pass.' if expect == 'Approved' else '_fail.') + fmt
        blob = (title + desc + repr(a) + repr(kw)).lower()
        assert not any(b in blob for b in BAD), (code, [b for b in BAD if b in blob])
        p = os.path.join(out, fn)
        if fmt in ('png', 'jpg'):
            shot(p, *a, fmt='jpg' if fmt == 'jpg' else None, **kw)
        else:
            {'pdf': pdf, 'docx': dcx, 'xlsx': xlsx, 'csv': csvf}[fmt](p, *a)
        M.append(dict(code=code, title=title, desc=desc, file=fn, source=src, expect=expect, extra=[]))

    P, F = 'Approved', 'Rejected'
    O = 'Priya Nair (CISO)'; C = 'Daniel Tan (CEO)'

    # ---- A.8.6 Capacity management
    add('A.8.6', 'Quarterly Capacity Review Q3 2026', 'Capacity monitoring and forecast for production platform.', 'd', 'pdf',
        'Quarterly Capacity Review - Q3 2026', meta('OPS-CAP-2026Q3', 'Tom Wong (IT Manager)', 'Priya Nair (CISO)', '1.0', '2026-10-06'),
        [('Monitoring', ['CloudWatch alarms CPU>75%, memory>80%, disk>85% on all 41 EC2 instances and RDS ms-prod-db (db.r6g.xlarge).', 'Alarms routed to PagerDuty service MS-Platform; 6 alarms fired in Q3, all resolved within SLA.']),
         ('Utilisation (Q3 average / peak)', ['EKS node pool: CPU 52% / 71%; memory 58% / 76%.', 'RDS: CPU 34% / 63%; storage 410 GB of 800 GB (51%).', 'S3 vessel telemetry: 18.2 TB, growth 6.1% per month.']),
         ('Forecast and decisions', ['AIS ingest volume expected +30% from Nov 2026 (4 new charterer fleets). Decision CAP-2026-09: add 2 EKS nodes (m6i.2xlarge) by 2026-11-01 - completed 2026-10-28 (change CHG-2291).', 'RDS storage autoscaling max raised to 1.5 TB.']),
         ('Approval', ['Reviewed by Priya Nair 2026-10-08 and noted in Management Review.'])])
    add('A.8.6', 'Infrastructure Capacity Report 2024', 'Capacity report for the platform.', 'd', 'pdf',
        'Infrastructure Capacity Report - FY2024', meta('OPS-CAP-2024Q1', 'Tom Wong (IT Manager)', 'Priya Nair (CISO)', '1.0', '2024-03-28'),
        [('Monitoring', ['CPU and memory thresholds monitored on production hosts via CloudWatch.']),
         ('Utilisation (Q1 2024)', ['App servers CPU 44% average; RDS storage 190 GB of 400 GB.', 'Forecast: add capacity before Q4 2024 peak season.']),
         ('Approval', ['Reviewed 2024-04-02.'])], expect=F)

    # ---- A.8.7 Malware
    edr = ['Dashboard', 'Endpoints', 'Detections', 'Policies']
    add('A.8.7', 'CrowdStrike Falcon - Sensor Coverage', 'EDR sensor coverage across all managed endpoints.', 's', 'png',
        'CrowdStrike Falcon', 'https://falcon.crowdstrike.com/hosts/sensors', '#c8102e', edr, 'Host management - sensor status',
        (['Group', 'Hosts', 'Sensor', 'Policy'], [300, 200, 240, 360]),
        [['macOS laptops (Jamf)', 58, 'Active', 'Prevention - Strict'], ['AWS EC2 Linux', 41, 'Active', 'Prevention - Strict'], ['Windows jump hosts', 4, 'Active', 'Prevention - Strict'], ['Executive devices', 6, 'Active', 'Prevention - Strict']],
        banner='109 of 109 managed hosts reporting; 0 detections unresolved (updated 2026-11-20 10:10)', src='Integration')
    add('A.8.7', 'CrowdStrike Falcon - Host Groups', 'EDR host group view.', 's', 'png',
        'CrowdStrike Falcon', 'https://falcon.crowdstrike.com/hosts/sensors', '#c8102e', edr, 'Host management - sensor status',
        (['Group', 'Hosts', 'Sensor', 'Policy'], [300, 200, 240, 360]),
        [['macOS laptops (Jamf)', 58, 'Active', 'Detect only'], ['AWS EC2 Linux', 41, 'Disabled', 'None'], ['Windows jump hosts', 4, 'Disabled', 'None'], ['Contractor devices', 9, 'Disabled', 'None']], expect=F, src='Integration')

    # ---- A.8.8 Vuln mgmt
    add('A.8.8', 'Vulnerability Remediation SLA Tracker 2026', 'Vulnerability register with severity, SLA and closure dates.', 't', 'xlsx',
        ['Finding ID', 'Asset', 'CVE', 'Severity', 'Detected', 'SLA due', 'Closed', 'Owner', 'Status'],
        [['VUL-0412', 'eks-node-pool-a', 'CVE-2026-1182', 'Critical', '2026-02-09', '2026-02-16', '2026-02-12', 'Aisha Rahman', 'Closed'],
         ['VUL-0455', 'api-gateway', 'CVE-2026-2290', 'High', '2026-03-22', '2026-04-21', '2026-04-03', 'Aisha Rahman', 'Closed'],
         ['VUL-0501', 'rds ms-prod-db', 'CVE-2026-3017', 'High', '2026-05-14', '2026-06-13', '2026-05-30', 'Marcus Lee', 'Closed'],
         ['VUL-0577', 'macOS laptops', 'CVE-2026-4410', 'Critical', '2026-07-01', '2026-07-08', '2026-07-05', 'Tom Wong', 'Closed'],
         ['VUL-0634', 'nginx ingress', 'CVE-2026-5521', 'Medium', '2026-09-18', '2026-12-17', '', 'Aisha Rahman', 'Open (in SLA)'],
         ['VUL-0651', 'ecr/fleet-api', 'CVE-2026-5930', 'High', '2026-10-27', '2026-11-26', '2026-11-10', 'Aisha Rahman', 'Closed']])
    add('A.8.8', 'External Vulnerability Scan Results October 2026', 'Scanner output for external perimeter.', 'd', 'pdf',
        'External Vulnerability Scan - Perimeter 2026-10-21', meta('SCAN-EXT-1021', 'Aisha Rahman', 'n/a', '1.0', '2026-10-21'),
        [('Summary', ['Targets: 14 public IPs. Result: 3 Critical, 7 High, 22 Medium open.', 'Scanner policy: SLA breach flagged for any Critical older than 7 days.']),
         ('Open Critical findings', ['VUL-0610 OpenSSH 8.2 on bastion-2 - detected 2026-08-30 - 52 days open - no remediation ticket.', 'VUL-0611 Log4j 2.14 in legacy-reports - detected 2026-09-02 - 49 days open - owner unassigned.', 'VUL-0618 Expired TLS chain on vessel-portal - detected 2026-10-01 - open.']),
         ('Status', ['Remediation plan not yet agreed. Escalation to be raised at next security meeting.'])], expect=F)

    # ---- A.8.9 Config mgmt
    add('A.8.9', 'Secure Configuration Baseline Standard', 'Approved hardening baselines and change-controlled configuration management.', 'd', 'docx',
        'Secure Configuration Baseline Standard', meta('STD-CFG-01', 'Aisha Rahman', 'Priya Nair (CISO)', '2.0', '2026-03-12'),
        [('Baselines', ['Linux (Amazon Linux 2023): CIS Level 1 via Ansible role ms-hardening v3.4; SSH root login disabled, password auth disabled.', 'macOS: CIS Level 1 via Jamf profiles (FileVault, firewall, 5 min screen lock).', 'AWS: CIS Foundations v1.4 conformance pack in AWS Config, 51 rules, evaluated daily.']),
         ('Management', ['All configuration lives in GitHub repo ms-infra (Terraform + Ansible); changes by pull request with 1 reviewer, tracked in change log.', 'Drift detection: Config rule non-compliance raises ticket automatically; 3 drift items in Q3, all closed.']),
         ('Review', ['Baselines reviewed annually. Next review 2027-03.', 'Approved: Priya Nair, CISO, 2026-03-12.'])])
    add('A.8.9', 'Configuration Management Procedure Draft', 'Configuration standard template.', 'd', 'docx',
        'Configuration Management Procedure', ['Company: Maritime Services Pte. Ltd.', 'Document ID: [DOC-ID]   Version: [VERSION]   Date: [DATE]', 'Owner: [OWNER NAME]   Approved by: [APPROVER NAME]'],
        [('Baselines', ['Baseline for [SYSTEM TYPE] is based on [BENCHMARK] version [X.X].', 'Configuration items are stored in [REPOSITORY].']),
         ('Management', ['Changes are approved by [ROLE] and recorded in [TOOL].', 'Drift is checked every [FREQUENCY].']),
         ('Review', ['Next review: [DATE]'])], expect=F)

    # ---- A.8.10 Information deletion
    add('A.8.10', 'Data Deletion and Media Sanitisation Log 2026', 'Deletion records with certificates for data and media.', 'd', 'pdf',
        'Data Deletion and Media Sanitisation Log - 2026', meta('REC-DEL-2026', 'Marcus Lee (ISMS Manager)', 'Priya Nair (CISO)', '1.0', '2026-11-12'),
        [('Method', ['Cloud data: S3 lifecycle rules expire customer exports after 90 days; RDS snapshots after 35 days; deletion confirmed by S3 inventory report.', 'Devices: Jamf erase-device command followed by Apple Configurator reset; certificate retained.']),
         ('Records', ['DEL-2026-014 | 2026-03-04 | Charterer Oceanic Lines offboarding | 1.2 GB S3 prefix /oceanic/ | verified by inventory report | M. Lee',
                      'DEL-2026-021 | 2026-05-19 | PDPA erasure request ER-0087 | 3 user records, backups purged at expiry 2026-06-23 | verified | M. Lee',
                      'DEL-2026-033 | 2026-08-11 | 6 retired MacBooks (SN C02Z...) | secure erase, certificate ERS-0811 | T. Wong',
                      'DEL-2026-040 | 2026-10-30 | Q3 export bucket ms-exports-q3 | lifecycle expiry confirmed | A. Rahman']),
         ('Approval', ['Reviewed and approved by Priya Nair, 2026-11-12.'])])
    add('A.8.10', 'Information Deletion Overview', 'Overview of deletion approach.', 'd', 'pdf',
        'Information Deletion Overview', ['Maritime Services Pte. Ltd.'],
        [('Overview', ['Information should be deleted when it is no longer needed. Staff are expected to delete data that is not required.', 'Deletion should be done securely in line with good practice and applicable laws.', 'Records of deletion may be kept where appropriate.', 'Managers are responsible for making sure that their teams follow the process.'])], expect=F)

    # ---- A.8.11 Data masking
    add('A.8.11', 'Data Masking Standard and Verification Results', 'Masking rules and verification of masked non-production data.', 'd', 'pdf',
        'Data Masking Standard and Verification 2026', meta('STD-MASK-01', 'Aisha Rahman', 'Priya Nair (CISO)', '1.2', '2026-06-22'),
        [('Rules', ['Crew NRIC/passport numbers: irreversible hash (SHA-256 + salt). Names: replaced from synthetic dictionary. Email: user###@example.invalid. Vessel IMO numbers retained (non-personal).', 'Support console shows only last 4 characters of identifiers to roles other than Compliance Admin (RBAC policy POL-AC-01).']),
         ('Verification 2026-06-20', ['Staging DB ms-stg-db refreshed from production with masking job mask-etl v1.7.', 'Scan of 14 tables / 212 columns: 0 clear-text NRIC, 0 clear-text email. 100% of 38 flagged columns masked.', 'Run by A. Rahman; reviewed by M. Lee.']),
         ('Approval', ['Approved: Priya Nair, CISO, 2026-06-22.'])])
    add('A.8.11', 'Staging Data Masking Verification Report', 'Verification of masking in staging.', 'd', 'pdf',
        'Staging Data Masking Verification', meta('REP-MASK-0912', 'Aisha Rahman', 'Priya Nair (CISO)', '1.0', '2026-09-12'),
        [('Scope', ['Staging DB ms-stg-db refreshed 2026-09-10 from production.']),
         ('Results', ['crew_profile.nric: 1,204 of 1,204 rows contain clear-text values (masking job did not run).', 'support_tickets.reporter_email: clear-text in 5,810 rows.', 'vessel_contacts.phone: clear-text in 322 rows.', 'Conclusion: 3 of 5 high-risk tables unmasked. Findings MSK-1, MSK-2, MSK-3 open; owner Aisha Rahman; target date not set.'])], expect=F)

    # ---- A.8.12 DLP
    add('A.8.12', 'Microsoft Purview DLP - Policy Status', 'DLP policies enforcing on Exchange, SharePoint and endpoints.', 's', 'png',
        'Microsoft Purview', 'https://compliance.microsoft.com/datalossprevention/policies', '#0f4c81', ['Home', 'DLP', 'Alerts', 'Activity explorer'], 'Data loss prevention policies',
        (['Policy', 'Locations', 'Status', 'Matches (30d)'], [380, 340, 200, 200]),
        [['PII - NRIC and passport', 'Exchange, SharePoint, OneDrive, Devices', 'Active', 17], ['Customer vessel data', 'SharePoint, Teams', 'Active', 9], ['Credentials and API keys', 'Exchange, Devices', 'Active', 4], ['USB and cloud upload block', 'Endpoint (58 Macs)', 'Active', 12]],
        banner='All 4 policies enforcing (block with override); 42 alerts reviewed in 30 days', src='Integration')
    add('A.8.12', 'DLP Solution Proposal', 'Proposal for DLP rollout.', 'd', 'docx',
        'Data Leakage Prevention - Proposal', ['Company: Maritime Services Pte. Ltd.', 'Document ID: PRJ-DLP-01   Version: 0.2 (draft)   Date: 2026-04-14', 'Owner: Tom Wong   Approved by: (not yet reviewed)'],
        [('Background', ['Management asked IT to evaluate options for monitoring data leaving the company via email and removable media.']),
         ('Options', ['Option A: Microsoft Purview DLP (included in E5 uplift, est. SGD 14,400 per year).', 'Option B: Third-party endpoint agent (est. SGD 21,000 per year).']),
         ('Next steps', ['Obtain budget approval; pilot with Finance team; decision pending.', 'No policies are currently deployed.'])], expect=F)

    # ---- A.8.14 Redundancy
    add('A.8.14', 'High Availability Architecture and Switchover Drill', 'Multi-AZ design and switchover exercise results.', 'd', 'pdf',
        'High Availability Architecture and Switchover Drill 2026', meta('ARCH-HA-02', 'Aisha Rahman', 'Priya Nair (CISO)', '2.1', '2026-09-24'),
        [('Design', ['Production runs across ap-southeast-1a/1b/1c: EKS node groups in 3 AZs, RDS PostgreSQL Multi-AZ, ALB cross-zone, NAT gateway per AZ.', 'Availability target 99.9% (SLA to charterers); measured YTD 99.97%.']),
         ('Switchover drill 2026-09-17', ['RDS forced switchover: 62 s to promote standby, 0 transactions lost; application reconnected automatically.', 'AZ-1a isolation exercise: EKS rescheduled 34 pods within 4 min; ALB error rate peaked at 0.4%.']),
         ('Actions', ['Raised connection-retry timeout (ACT-118) - done 2026-09-22.', 'Approved: Priya Nair, CISO, 2026-09-24.'])])
    add('A.8.14', 'Platform Redundancy Review', 'Redundancy review of the platform.', 'x', 'xlsx',
        ['Component', 'Redundancy', 'Reviewed', 'Reviewer', 'Valid until'],
        [['RDS ms-prod-db', 'Multi-AZ', '2025-02-11', 'Tom Wong', '2026-02-11 (expired)'], ['EKS nodes', '2 AZ', '2025-02-11', 'Tom Wong', '2026-02-11 (expired)'], ['ALB', 'Cross-zone', '2025-02-11', 'Tom Wong', '2026-02-11 (expired)'],
         ['NAT gateway', 'Single AZ', '2025-02-11', 'Tom Wong', '2026-02-11 (expired)'], ['AIS feed', 'Single provider', '2025-02-11', 'Tom Wong', '2026-02-11 (expired)']], expect=F)

    # ---- A.8.15 Logging
    add('A.8.15', 'CloudTrail - Organization Trail Configuration', 'CloudTrail multi-region organization trail with log validation.', 's', 'png',
        'AWS Console | CloudTrail', 'https://console.aws.amazon.com/cloudtrail/home#/trails', '#232f3e', AWS, 'Trails',
        (['Trail', 'Scope', 'Logging', 'Log file validation'], [320, 320, 200, 260]),
        [['ms-org-trail', 'All regions, org-wide', 'Enabled', 'Enabled'], ['ms-s3-data-events', 'S3 data events (prod)', 'Enabled', 'Enabled'], ['ms-kms-events', 'KMS management', 'Enabled', 'Enabled']],
        banner='Logs delivered to s3://ms-log-archive (Object Lock, 400-day retention); last delivery 2026-11-20 10:05', src='Integration')
    add('A.8.15', 'CloudTrail Trails - Development Account', 'CloudTrail trail list.', 's', 'png',
        'AWS Console | CloudTrail', 'https://console.aws.amazon.com/cloudtrail/home#/trails', '#232f3e', AWS, 'Trails (ms-dev account)',
        (['Trail', 'Scope', 'Logging', 'Log file validation'], [320, 320, 200, 260]),
        [['dev-trail', 'ap-southeast-1 only', 'Disabled', 'Disabled'], ['legacy-trail', 'ap-southeast-1 only', 'Disabled', 'Disabled']], expect=F, src='Integration')

    # ---- A.8.16 Monitoring
    add('A.8.16', 'Security Monitoring Weekly Report - Week 46 2026', 'Weekly security monitoring and triage report.', 'd', 'pdf',
        'Security Monitoring Weekly Report - 2026 Week 46', meta('SOC-WK46', 'Aisha Rahman', 'Priya Nair (CISO)', '1.0', '2026-11-16'),
        [('Coverage', ['Sources: CloudTrail, GuardDuty (3 regions), VPC flow logs, Okta system log, M365 audit, CrowdStrike. Forwarded to Elastic SIEM (index ms-sec-*).', '37 detection rules active; on-call via PagerDuty 24x7.']),
         ('Week 9-15 Nov 2026', ['Alerts: 118 total, 4 escalated, 0 incidents. Mean time to triage 11 min.', 'ALR-8841 impossible-travel login (Okta) - confirmed contractor on VPN, closed.', 'ALR-8852 GuardDuty Recon:EC2/Portscan from external IP 203.0.113.44 - blocked at WAF, closed.', 'Rule tuning: suppressed 2 noisy rules (RULE-31, RULE-19) after review.']),
         ('Sign-off', ['Reviewed by Priya Nair, CISO, 2026-11-16.'])])
    add('A.8.16', 'Website Traffic Monitoring Report October 2026', 'Monthly traffic monitoring report.', 'd', 'pdf',
        'Website Traffic Monitoring Report - October 2026', meta('MKT-WEB-1026', 'Marketing Lead', 'Head of Sales', '1.0', '2026-11-03'),
        [('Traffic', ['Sessions: 18,420 (+7.2% month on month). Unique visitors: 11,903. Bounce rate 41%.', 'Top sources: organic search 48%, LinkedIn 22%, direct 19%.']),
         ('Campaigns', ['Webinar "Fleet analytics 2026" produced 212 sign-ups; conversion 3.1%.', 'Page load p95: 1.9 s on the marketing site.'])], expect=F)

    # ---- A.8.17 Clock sync
    add('A.8.17', 'NTP Synchronisation Status Report', 'Clock offsets from approved time sources across servers.', 't', 'csv',
        ['Host', 'Environment', 'Time source', 'Offset (ms)', 'Stratum', 'Checked'],
        [['eks-node-a1', 'prod', 'Amazon Time Sync 169.254.169.123', 0.4, 3, '2026-11-18'], ['eks-node-a2', 'prod', 'Amazon Time Sync 169.254.169.123', 0.6, 3, '2026-11-18'], ['rds-ms-prod-db', 'prod', 'AWS managed', 0.3, 3, '2026-11-18'],
         ['bastion-1', 'prod', 'Amazon Time Sync 169.254.169.123', 0.5, 3, '2026-11-18'], ['siem-01', 'sec', 'Amazon Time Sync 169.254.169.123', 0.7, 3, '2026-11-18'], ['ci-runner-3', 'ci', 'Amazon Time Sync 169.254.169.123', 1.1, 3, '2026-11-18']])
    add('A.8.17', 'NTP Check - Selected Hosts', 'Clock check on a few hosts.', 't', 'csv',
        ['Host', 'Environment', 'Time source', 'Offset (ms)', 'Note'],
        [['eks-node-a1', 'prod', 'Amazon Time Sync', 0.4, 'ok'], ['eks-node-a2', 'prod', 'Amazon Time Sync', 0.6, 'ok'], ['bastion-1', 'prod', 'Amazon Time Sync', 0.5, 'ok'], ['ci-runner-3', 'ci', 'Amazon Time Sync', 1.1, 'ok'],
         ['(37 other servers)', 'prod/sec', 'not enrolled', 'n/a', 'not checked']], expect=F)

    # ---- A.8.18 Privileged utilities
    add('A.8.18', 'Privileged Utility Register and Approval', 'Register of privileged utilities with approved users and logging.', 'x', 'xlsx',
        ['Utility', 'System', 'Authorised users', 'Control', 'Approved by', 'Approval date', 'Next review'],
        [['AWS SSM Session Manager', 'EC2 fleet', 'Cloud security team (3)', 'Session logs to S3, MFA', 'Priya Nair', '2026-02-24', '2027-02-24'],
         ['psql superuser', 'RDS ms-prod-db', 'DBA role (2)', 'Break-glass via Vault, logged', 'Priya Nair', '2026-02-24', '2027-02-24'],
         ['kubectl exec', 'EKS prod', 'SRE on-call (4)', 'RBAC role sre-oncall, audit log', 'Priya Nair', '2026-02-24', '2027-02-24'],
         ['Jamf Pro admin console', 'macOS fleet', 'IT team (2)', 'Okta SSO + MFA', 'Priya Nair', '2026-02-24', '2027-02-24'],
         ['Okta super admin', 'Identity', 'CISO, IT Manager', 'Phishing-resistant MFA', 'Daniel Tan', '2026-02-24', '2027-02-24']])
    add('A.8.18', 'Privileged Utility Approvals', 'Approved privileged utilities.', 'd', 'pdf',
        'Privileged Utility Approvals', meta('REG-PUT-01', 'Priya Nair (CISO)', 'Daniel Tan (CEO)', '1.0', '2024-11-05'),
        [('Approved utilities', ['AWS SSM Session Manager - cloud security team - session logging enabled.', 'psql superuser - DBA role - break-glass.', 'kubectl exec - SRE on-call.']),
         ('Validity', ['Approval valid for 12 months from 2024-11-05; expired 2025-11-05. Renewal not recorded.'])], expect=F)

    # ---- A.8.19 Software installation
    add('A.8.19', 'Software Installation Control Procedure', 'Rules for installing software on operational systems.', 'd', 'pdf',
        'Software Installation Control Procedure', meta('PRC-SW-01', 'Tom Wong (IT Manager)', 'Priya Nair (CISO)', '1.5', '2026-04-27'),
        [('Servers', ['Production hosts are immutable: software is baked into AMIs by Packer pipeline, built from GitHub ms-images; no interactive installs (SSH disabled, SSM only).', 'Every AMI change needs a reviewed pull request and passes Inspector scan before promotion.']),
         ('Endpoints', ['macOS: standard users cannot install outside the Jamf Self Service catalogue (82 approved titles); Gatekeeper enforced; other software via request ticket approved by IT Manager.', 'Quarterly review of the approved list: last done 2026-10-05, 3 titles removed.']),
         ('Approval', ['Approved: Priya Nair, CISO, 2026-04-27.'])])
    add('A.8.19', 'Jamf Pro - Restricted Software Compliance', 'Jamf smart group of devices with non-approved software.', 's', 'png',
        'Jamf Pro', 'https://maritime.jamfcloud.com/smartComputerGroups.html', '#2b5797', ['Computers', 'Smart groups', 'Policies', 'Reports'], 'Smart group: Restricted software installed',
        (['Device', 'User', 'Application', 'Status'], [260, 260, 360, 200]),
        [['MBP-0112', 'Developer', 'uTorrent 3.6', 'Non-compliant'], ['MBP-0127', 'Developer', 'Unknown VPN client', 'Non-compliant'], ['MBP-0140', 'Sales', 'Crypto miner (XMRig)', 'Non-compliant'], ['MBP-0151', 'Operations', 'AnyDesk 7.1', 'Non-compliant']],
        expect=F, src='Integration')

    # ---- A.8.21 Network services
    add('A.8.21', 'Network Service Providers - Security Requirements Register', 'Security mechanisms and service levels for network services.', 'd', 'docx',
        'Network Services Security Requirements Register', meta('REG-NET-01', 'Tom Wong (IT Manager)', 'Priya Nair (CISO)', '1.3', '2026-05-18'),
        [('Services', ['Singtel Business Internet (HQ) - 1 Gbps dual-link, 99.95% SLA, DDoS scrubbing included, contract MS-NET-2025-07.', 'AWS Direct Connect / Site-to-Site VPN to customer yards - IPSec AES-256, IKEv2, monitored by CloudWatch tunnel-state alarms.', 'Cloudflare WAF and DNS - TLS 1.2+, SOC 2 report reviewed 2026-04-30.']),
         ('Requirements', ['Encryption in transit mandatory; providers must notify incidents within 24 hours; SLA breaches reviewed monthly.', 'Q3 service levels: Singtel 99.98%, VPN 99.93%, Cloudflare 100%.']),
         ('Approval', ['Approved: Priya Nair, CISO, 2026-05-18. Next review 2027-05.'])])
    add('A.8.21', 'Internet Service Agreement Summary', 'Summary of ISP service levels.', 'd', 'pdf',
        'Internet Service Agreement Summary', ['Company: Maritime Services Pte. Ltd.', 'Document ID: SUP-ISP-03   Version: 1.0   Date: 2026-03-02', 'Owner: Tom Wong   Approved by: '],
        [('Services', ['Business internet 1 Gbps, 99.95% availability target, 4-hour fix time.']),
         ('Security', ['Security features to be agreed. No review of the provider security controls has been signed off.']),
         ('Approval', ['Approver signature: ____________    Date: ____________'])], expect=F)

    # ---- A.8.22 Segregation
    add('A.8.22', 'AWS VPC Segregation - Subnets and Network ACLs', 'Production, staging and management segregation.', 's', 'png',
        'AWS Console | VPC', 'https://console.aws.amazon.com/vpc/home#subnets', '#232f3e', AWS, 'Subnets by environment (ap-southeast-1)',
        (['VPC / Subnet group', 'CIDR', 'Network ACL', 'Route to other env'], [340, 220, 260, 300]),
        [['vpc-prod / private-app', '10.10.0.0/20', 'nacl-prod-app', 'None'], ['vpc-prod / private-data', '10.10.16.0/20', 'nacl-prod-data', 'None'], ['vpc-stg / all', '10.20.0.0/16', 'nacl-stg', 'None'], ['vpc-mgmt / bastion', '10.30.0.0/24', 'nacl-mgmt', 'Prod via TGW (VPN only)']],
        banner='3 VPCs, no peering between prod and non-prod; Config rule vpc-peering-restricted: Compliant', src='Integration')
    add('A.8.22', 'Network Architecture Overview', 'Network diagram summary.', 'd', 'pdf',
        'Network Architecture Overview', meta('ARCH-NET-01', 'Tom Wong', 'Priya Nair (CISO)', '1.1', '2026-05-06'),
        [('Layout', ['Single VPC vpc-main (10.0.0.0/16) hosts production, staging and development workloads.', 'All subnets share route table rtb-main with full east-west connectivity; security groups sg-default allow all internal traffic.']),
         ('Notes', ['Segregation by naming convention only. Management access to all environments from the same bastion.', 'Improvement idea: split into separate VPCs (not scheduled).'])], expect=F)

    # ---- A.8.23 Web filtering
    add('A.8.23', 'Cisco Umbrella - DNS Security Policy', 'Web content filtering policy applied to all staff devices.', 's', 'png',
        'Cisco Umbrella', 'https://dashboard.umbrella.com/o/8821/#/policies', '#049fd9', ['Overview', 'Policies', 'Reports', 'Deployments'], 'Policy: Corporate-Default (applies to 62 identities)',
        (['Category group', 'Action', 'Requests blocked (30d)', 'Status'], [340, 220, 260, 200]),
        [['Malware and phishing', 'Block', 1182, 'Active'], ['Newly seen domains', 'Block', 640, 'Active'], ['Adult and gambling', 'Block', 215, 'Active'], ['File sharing (unsanctioned)', 'Block', 98, 'Active']],
        banner='Roaming client deployed on 58 of 58 Macs; policy last changed 2026-09-03 (CHG-2240)', src='Integration')
    add('A.8.23', 'Web Filtering Standard', 'Standard for web filtering.', 'd', 'docx',
        'Web Filtering Standard', ['Company: Maritime Services Pte. Ltd.', 'Document ID: STD-WEB-[NN]   Version: [x.y]   Date: [dd-mm-yyyy]', 'Owner: [name]   Approved by: [name]'],
        [('Scope', ['This standard applies to [user group] using [filtering product].']),
         ('Blocked categories', ['[category 1], [category 2], [category 3]']),
         ('Exceptions', ['Exceptions are requested via [process] and approved by [role] for [duration].'])], expect=F)

    # ---- A.8.25 SDLC
    add('A.8.25', 'Secure Software Development Lifecycle Policy', 'SDLC rules covering requirements, review, scanning and release.', 'd', 'pdf',
        'Secure Software Development Lifecycle Policy', meta('POL-SDLC-01', 'Marcus Lee', 'Daniel Tan (CEO)', '2.0', '2026-02-16'),
        [('Lifecycle gates', ['1. Design: threat model for features touching authentication, vessel data or integrations (template TM-02).', '2. Build: GitHub pull request, 1 approving reviewer, branch protection on main, signed commits.', '3. Verify: CI runs CodeQL, Dependabot, Trivy image scan and automated QA suites; builds blocked on Critical/High.', '4. Release: change ticket, staging sign-off, deployment by pipeline only (no manual production push).']),
         ('Metrics 2026 YTD', ['412 pull requests merged, 100% reviewed; 0 production releases outside the pipeline.']),
         ('Approval', ['Approved: Daniel Tan, CEO, 2026-02-16. Review annually.'])])
    add('A.8.25', 'Fleet Platform Release Notes v4.12', 'Release notes document.', 'd', 'pdf',
        'MarineOps Release Notes - v4.12', meta('REL-4.12', 'Product Owner', 'CTO', '1.0', '2026-09-30'),
        [('New features', ['Voyage ETA recalculation with weather routing; new vessel dashboard widgets; CSV export of port-call history.']),
         ('Improvements', ['Faster map loading (35%); updated Italian and Greek translations.']),
         ('Known issues', ['Dark mode contrast on the fuel report; PDF export fonts on Safari 16.'])], expect=F)

    # ---- A.8.26 Application security requirements
    add('A.8.26', 'MarineOps Security Requirements Specification', 'Security requirements for the platform approved before build.', 'd', 'docx',
        'MarineOps Security Requirements Specification v3', meta('SRS-SEC-03', 'Aisha Rahman', 'Priya Nair (CISO)', '3.0', '2026-03-09'),
        [('Authentication and access', ['SR-01 SSO via SAML/OIDC; MFA enforced for admin roles. SR-02 Tenant isolation: every query scoped by org_id, verified by automated QA suites in CI.', 'SR-03 Sessions expire after 30 minutes idle.']),
         ('Data protection', ['SR-10 TLS 1.2+ in transit; SR-11 AES-256 at rest (KMS CMK); SR-12 crew personal data masked in logs.', 'SR-13 Audit trail of vessel configuration changes retained 24 months.']),
         ('Traceability', ['Each SR is linked to Jira epics (SEC-210..SEC-238); 29 of 29 requirements implemented in release 4.8.', 'Specification reviewed and approved by Priya Nair on 2026-03-09 before design start.'])])
    add('A.8.26', 'Application Security Requirements v1', 'Security requirements for the platform.', 'd', 'docx',
        'Application Security Requirements v1', meta('SRS-SEC-01', 'Aisha Rahman', 'Priya Nair (CISO)', '1.0', '2024-06-10'),
        [('Requirements', ['SR-01 Admin roles use MFA. SR-02 Passwords hashed with bcrypt. SR-03 TLS for all endpoints.']),
         ('Status', ['Approved 2024-06-10 for release 3.0. Not reviewed since.'])], expect=F)

    # ---- A.8.27 Secure architecture
    add('A.8.27', 'Secure Architecture Principles and Threat Model - MarineOps', 'Documented engineering principles with applied threat model.', 'd', 'pdf',
        'Secure System Architecture Principles - MarineOps', meta('ARCH-SEC-01', 'Aisha Rahman', 'Priya Nair (CISO)', '1.4', '2026-07-08'),
        [('Principles', ['P1 Least privilege: IAM roles per service, no wildcard actions (Access Analyzer verified).', 'P2 Defence in depth: WAF, private subnets, security groups, KMS, row-level tenant scoping.', 'P3 Zero trust: service-to-service mTLS (Istio), no implicit network trust.', 'P4 Secure defaults: new services come from the golden Terraform module ms-svc v2.']),
         ('Threat model 2026-06-30 (STRIDE)', ['14 threats identified across the vessel telemetry gateway; 12 mitigated, 2 accepted by the CISO (TM-9 and TM-13, residual Low).', 'Architecture review board attendees: A. Rahman, M. Lee, CTO.']),
         ('Approval', ['Approved: Priya Nair, CISO, 2026-07-08.'])])
    add('A.8.27', 'Engineering Principles Statement', 'Engineering principles.', 'd', 'docx',
        'Engineering Principles Statement', ['Maritime Services Pte. Ltd.'],
        [('Statement', ['We build systems with security in mind and follow industry best practice.', 'Architecture decisions consider risk and the needs of our customers.', 'Teams are encouraged to apply sound engineering principles and review designs regularly.', 'Security is everyone\'s responsibility.'])], expect=F)

    # ---- A.8.28 Secure coding
    add('A.8.28', 'GitHub Code Scanning - Repository Overview', 'CodeQL and dependency alerts across repositories.', 's', 'png',
        'GitHub', 'https://github.com/organizations/maritime-services/settings/security_analysis', '#24292f', ['Overview', 'Code scanning', 'Dependabot', 'Secret scanning'], 'Code security - maritime-services (12 repositories)',
        (['Repository', 'CodeQL', 'Open Critical/High', 'Secret scanning'], [300, 220, 260, 260]),
        [['fleet-api', 'Enabled', 0, 'Enabled'], ['marineops-web', 'Enabled', 0, 'Enabled'], ['telemetry-gateway', 'Enabled', 1, 'Enabled'], ['ms-infra', 'Enabled', 0, 'Enabled']],
        banner='Push protection on; 12 of 12 repos scanned on every pull request; 1 High in remediation (due 2026-11-27)', src='Integration')
    add('A.8.28', 'GitHub Code Scanning - Legacy Repositories', 'Code scanning alerts by repository.', 's', 'png',
        'GitHub', 'https://github.com/organizations/maritime-services/settings/security_analysis', '#24292f', ['Overview', 'Code scanning', 'Dependabot', 'Secret scanning'], 'Code security - legacy repositories',
        (['Repository', 'CodeQL', 'Open Critical/High', 'Secret scanning'], [300, 220, 260, 260]),
        [['legacy-reports', 'Disabled', 7, 'Disabled'], ['vessel-portal', 'Disabled', 5, 'Disabled'], ['crew-app', 'Disabled', 3, 'Disabled'], ['bastion-scripts', 'Disabled', 'Open', 'Disabled']], expect=F, src='Integration')

    # ---- A.8.29 Security testing
    add('A.8.29', 'External Penetration Assessment Report 2026 - MarineOps', 'Independent penetration assessment with re-verification closure.', 'd', 'pdf',
        'Penetration Assessment Report - MarineOps Platform', meta('PEN-2026-02', 'Priya Nair (CISO)', 'Daniel Tan (CEO)', '1.1', '2026-08-14'),
        [('Engagement', ['Assessor: Raffles CyberSec Pte Ltd (CREST accredited). Window 2026-07-06 to 2026-07-17. Scope: web app, public API, mobile API, AWS perimeter. Method: OWASP ASVS 4.0 L2.']),
         ('Findings', ['2 High, 4 Medium, 6 Low. H-1 IDOR on /api/v2/vessels/{id}/crew; H-2 JWT audience not validated on telemetry endpoint.']),
         ('Remediation and re-verification', ['H-1 fixed in release 4.9 (2026-07-28); H-2 fixed 2026-07-30; Mediums closed by 2026-08-07.', 'Re-verification on 2026-08-11 confirmed closure of all High and Medium findings; 5 Low accepted with owner sign-off.']),
         ('Approval', ['Report accepted by Priya Nair, CISO, 2026-08-14; presented to CEO in Management Review.'])])
    add('A.8.29', 'Penetration Assessment - Portal Findings Summary', 'Assessment findings with open items.', 'd', 'pdf',
        'Penetration Assessment - Vessel Portal Findings', meta('PEN-2026-03', 'Priya Nair (CISO)', 'Daniel Tan (CEO)', '1.0', '2026-10-09'),
        [('Engagement', ['Assessor: Raffles CyberSec Pte Ltd. Window 2026-09-21 to 2026-09-30. Scope: vessel portal only.']),
         ('Findings', ['1 Critical, 3 High, 5 Medium. C-1 SQL injection in /portal/search allows read of any tenant database. H-1 broken access control on invoice download.', 'Status on 2026-10-09: all findings Open. Re-verification not scheduled; no remediation owner assigned.']),
         ('Risk', ['Exploitation of C-1 demonstrated with extraction of 40 crew records.'])], expect=F)

    # ---- A.8.30 Outsourced development
    add('A.8.30', 'Outsourced Development Oversight - Kapal Digital 2026', 'Contract security terms and periodic review of outsourced developer.', 'd', 'docx',
        'Outsourced Development Oversight - Kapal Digital Pte Ltd', meta('SUP-DEV-KD', 'Marcus Lee', 'Priya Nair (CISO)', '1.2', '2026-09-28'),
        [('Contract', ['MSA and Security Addendum signed 2026-01-19 by Daniel Tan and Kapal Digital director: secure coding per POL-SDLC-01, right to audit, IP assignment, breach notice 24 h, NDA.']),
         ('Monitoring 2026', ['Contractors work only in the maritime-services GitHub organisation via Okta SSO; all 3 contractor accounts have MFA; repository access reviewed quarterly (last 2026-10-01).', 'Code review: 100% of 74 contractor pull requests approved by an internal engineer; CodeQL clean on release.', 'Quarterly review meetings held 2026-04-14, 2026-07-14, 2026-10-13; 2 minor findings closed.']),
         ('Approval', ['Approved: Priya Nair, CISO, 2026-09-28.'])])
    add('A.8.30', 'Statement of Work - Kapal Digital Mobile App', 'SOW for outsourced mobile app development.', 'd', 'pdf',
        'Statement of Work - Mobile App Development', ['Company: Maritime Services Pte. Ltd. / Kapal Digital Pte Ltd', 'Document ID: SOW-2026-07   Version: 1.0   Date: 2026-07-03', 'Owner: CTO   Approved by: (awaiting signature)'],
        [('Deliverables', ['iOS and Android crew app, 3 milestones, fixed fee SGD 96,000.']),
         ('Terms', ['Payment 30 days from invoice. Source code delivered at final milestone.', 'Security requirements: to be agreed. No audit rights or code review obligations specified.']),
         ('Signatures', ['Maritime Services: ____________   Kapal Digital: ____________'])], expect=F)

    # ---- A.8.31 Separation of environments
    add('A.8.31', 'AWS Organizations - Environment Account Separation', 'Separate AWS accounts and SCPs for dev, staging and production.', 's', 'png',
        'AWS Console | Organizations', 'https://console.aws.amazon.com/organizations/v2/home/accounts', '#232f3e', AWS, 'AWS accounts (4)',
        (['Account', 'Environment', 'Service control policy', 'Status'], [320, 220, 400, 200]),
        [['ms-prod (4412-xxxx-8801)', 'Production', 'scp-prod-guardrails', 'Active'], ['ms-stg (4412-xxxx-8802)', 'Staging', 'scp-nonprod-baseline', 'Active'], ['ms-dev (4412-xxxx-8803)', 'Development', 'scp-nonprod-baseline', 'Active'], ['ms-sec (4412-xxxx-8804)', 'Security tooling', 'scp-sec-readonly', 'Active']],
        banner='Cross-account production access only via role ms-prod-readonly with MFA; no developer IAM users in ms-prod', src='Integration')
    add('A.8.31', 'Security Group Review - Database Access', 'Security group review of database reachability.', 's', 'png',
        'AWS Console | EC2', 'https://console.aws.amazon.com/ec2/home#SecurityGroups', '#232f3e', AWS, 'Security group review: sg-db (shared account)',
        (['Source', 'Environment', 'Port', 'Result'], [340, 220, 200, 300]),
        [['sg-dev-app', 'Development', 5432, 'Non-compliant'], ['sg-stg-app', 'Staging', 5432, 'Non-compliant'], ['10.0.0.0/16', 'All environments', 5432, 'Non-compliant'], ['sg-prod-app', 'Production', 5432, 'Compliant']], expect=F, src='Integration')

    # ---- A.8.32 Change management
    add('A.8.32', 'Change Advisory Board Log 2026', 'Change records with risk rating, approval and rollback plan.', 'x', 'xlsx',
        ['Change ID', 'Date', 'Description', 'Risk', 'Rollback plan', 'Approved by', 'Result'],
        [['CHG-2201', '2026-03-17', 'RDS minor version upgrade 15.4 to 15.6', 'Medium', 'Snapshot + restore', 'Tom Wong / CAB', 'Successful'],
         ['CHG-2218', '2026-05-12', 'Okta MFA policy enforcement for contractors', 'Medium', 'Revert policy', 'Priya Nair / CAB', 'Successful'],
         ['CHG-2240', '2026-09-03', 'Umbrella policy category update', 'Low', 'Previous policy version', 'Tom Wong', 'Successful'],
         ['CHG-2265', '2026-09-30', 'Release 4.12 production deployment', 'Medium', 'Helm rollback to 4.11', 'CAB 2026-09-28', 'Successful'],
         ['CHG-2291', '2026-10-28', 'Add 2 EKS nodes (capacity)', 'Low', 'Scale down node group', 'Tom Wong', 'Successful'],
         ['CHG-2297', '2026-11-05', 'WAF rule set upgrade', 'Medium', 'Disable managed rule group', 'Priya Nair / CAB', 'Successful']])
    add('A.8.32', 'Production Change Register Export', 'Register of production changes.', 't', 'csv',
        ['Change ID', 'Date', 'Description', 'Type', 'Approver', 'Rollback plan', 'Result'],
        [['CHG-2230', '2026-07-21', 'Hotfix: payment export crash', 'Emergency', '', '', 'Deployed'], ['CHG-2233', '2026-07-29', 'Open port 8443 on ALB', 'Emergency', '', '', 'Deployed'],
         ['CHG-2250', '2026-09-11', 'Change DB parameter group', 'Standard', '', '', 'Deployed'], ['CHG-2258', '2026-09-19', 'Disable WAF rule 942100', 'Emergency', '', '', 'Deployed'],
         ['CHG-2271', '2026-10-09', 'Rotate S3 bucket policy', 'Standard', '', '', 'Deployed']], expect=F)

    # ---- A.8.33 Test information
    add('A.8.33', 'Non-Production Data Handling Standard', 'Rules for selection and protection of data used in pre-production environments.', 'd', 'pdf',
        'Non-Production Data Handling Standard', meta('STD-NPD-01', 'Aisha Rahman', 'Priya Nair (CISO)', '1.1', '2026-04-08'),
        [('Selection', ['Pre-production environments use synthetic datasets generated by data-gen v2 (fixtures repo ms-fixtures) as the default.', 'Production copies are allowed only with CISO approval, masked by mask-etl v1.7 (see STD-MASK-01), and expire after 14 days.']),
         ('Protection', ['Staging account ms-stg: same encryption (KMS) and RBAC as production; access via Okta group eng-staging; access logs reviewed monthly.', 'Refresh log: 2026-04-20, 2026-07-20, 2026-10-19, all masked and verified.']),
         ('Approval', ['Approved: Priya Nair, CISO, 2026-04-08.'])])
    add('A.8.33', 'Staging Environment Dataset Inventory', 'Inventory of datasets held in staging.', 't', 'csv',
        ['Dataset', 'Source', 'Records', 'Contains personal data', 'Masked', 'Access group'],
        [['crew_profiles', 'Production copy 2026-09-10', 1204, 'Yes (NRIC, passport)', 'No', 'eng-all'], ['support_tickets', 'Production copy 2026-09-10', 5810, 'Yes (email, phone)', 'No', 'eng-all'],
         ['vessel_positions', 'Production copy 2026-09-10', 2400000, 'No', 'n/a', 'eng-all'], ['invoices', 'Production copy 2026-09-10', 3122, 'Yes (company contacts)', 'No', 'contractors, eng-all'],
         ['port_calls', 'Synthetic', 9000, 'No', 'n/a', 'eng-all']], expect=F)

    # ---- A.8.34 Audit testing
    add('A.8.34', 'Audit Assessment Plan - Surveillance Preparation 2026', 'Planned operational-system assessments agreed with owners.', 'd', 'docx',
        'Audit Assessment Plan - Operational Systems 2026', meta('AUD-PLAN-2026', 'Marcus Lee (ISMS Manager)', 'Priya Nair (CISO)', '1.0', '2026-10-19'),
        [('Scope and window', ['Activities: read-only configuration review of AWS ms-prod, Okta tenant, and Jamf; log sampling from the SIEM. Window: 2026-11-02 to 2026-11-13, 09:00-17:00 SGT, outside month-end billing.']),
         ('Safeguards', ['Auditor accounts read-only, time-boxed, MFA; no vulnerability scanning of production; data exports encrypted and deleted after 30 days.', 'Rollback and contact: on-call SRE (+65 6000 0142); abort criteria: any production latency alert.']),
         ('Agreement', ['System owners confirmed in writing: Tom Wong (infrastructure) 2026-10-20, Aisha Rahman (AWS) 2026-10-20, HR Lead (Okta data) 2026-10-21.', 'Approved: Priya Nair, CISO, 2026-10-19.'])])
    add('A.8.34', 'Audit Assessment Plan 2025', 'Audit activity plan for operational systems.', 'd', 'docx',
        'Audit Assessment Plan - Operational Systems 2025', ['Company: Maritime Services Pte. Ltd.', 'Document ID: AUD-PLAN-2025   Version: 1.0   Date: 2025-05-30', 'Owner: Marcus Lee   Approved by: (no sign-off recorded)'],
        [('Scope and window', ['Configuration review of AWS and Okta during 2025-06-09 to 2025-06-20.']),
         ('Safeguards', ['Read-only access. Business hours only.']),
         ('Agreement', ['System owner confirmations not obtained. Plan not signed.'])], expect=F)
    # ---- A.8.24 Cryptography
    add('A.8.24', 'Cryptographic Controls and Key Management Record 2026', 'Cryptography rules and key lifecycle evidence.', 'd', 'pdf',
        'Cryptographic Controls and Key Management Record 2026', meta('POL-CRY-01R', 'Aisha Rahman', 'Priya Nair (CISO)', '1.2', '2026-05-09'),
        [('Rules', ['TLS 1.2+ only (ALB policy ELBSecurityPolicy-TLS13-1-2-2021-06); data at rest AES-256 via AWS KMS customer-managed keys; laptops FileVault 2; backups encrypted with key alias/ms-backup.', 'Prohibited: MD5, SHA-1 signatures, TLS 1.0/1.1, self-managed keys outside KMS.']),
         ('Key inventory and rotation', ['alias/ms-rds-prod - automatic annual rotation, last rotated 2026-03-14. alias/ms-s3-vessel - rotated 2026-04-02. alias/ms-backup - rotated 2026-05-21.', 'Key administrators limited to 2 named users; key policy changes logged in CloudTrail and reviewed quarterly (2026-10-05).', 'Certificates: 14 public certificates managed by ACM with auto-renewal; none expiring within 30 days at 2026-11-18.']),
         ('Approval', ['Approved: Priya Nair, CISO, 2026-05-09.'])])
    add('A.8.24', 'AWS KMS - Customer Managed Keys', 'KMS key list.', 's', 'png',
        'AWS Console | KMS', 'https://console.aws.amazon.com/kms/home#/kms/keys', '#232f3e', AWS, 'Customer managed keys (ms-dev account)',
        (['Alias', 'Key spec', 'Rotation', 'Last rotated'], [320, 260, 240, 260]),
        [['alias/ms-dev-data', 'SYMMETRIC_DEFAULT', 'Disabled', 'Never'], ['alias/ms-dev-logs', 'SYMMETRIC_DEFAULT', 'Disabled', 'Never'], ['alias/legacy-rsa', 'RSA_2048', 'Disabled', '2023-02-10'], ['alias/ms-dev-ci', 'SYMMETRIC_DEFAULT', 'Disabled', 'Never']], expect=F, src='Integration')

    return M


if __name__ == '__main__':
    out = sys.argv[1]
    m = build(out)
    json.dump(m, open(os.path.join(out, 'manifest.json'), 'w'), indent=1)
    print(len(m), 'items ->', out)
