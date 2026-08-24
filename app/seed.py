"""
Seed database with:
- Default admin user
- ISO 27001:2022 framework: 30 main-clause requirements (4-10) + 93 Annex A controls (all set to 'Not Assessed')

All other modules (risks, policies, audits, vendors, assets, training, access reviews)
start empty - data should be added by the user through the application.

Run: python -m app.seed
"""
import sys
import random
from datetime import date, datetime, timedelta
from app import create_app
from app.models import (
    db, User, Framework, Control, Vendor, Employee, TrainingCampaign,
    TrainingCampaignEnrollment, EmployeeAccess, AccessReview,
    ComplianceSnapshot, DashboardSnapshot, ActivityLog, Asset,
)


def seed_database():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        # ---- DEFAULT USER ----
        admin = User(email='harsha@migrc.com', name='Harsha S', role='Admin')
        admin.set_password('admin123')
        db.session.add(admin)

        # ---- ISO 27001:2022 FRAMEWORK ----
        iso27001 = Framework(
            name='ISO 27001:2022',
            description='International standard for Information Security Management Systems (ISMS) - 30 main-clause requirements (Clauses 4-10) and 93 Annex A controls',
            category='Security',
            icon='globe',
            status='Not Started',
            owner='Harsha P',
            controls_detail='Clauses 4-10 (30) + Annex A: Organizational (37) + People (8) + Physical (14) + Technological (34)',
        )
        db.session.add(iso27001)
        db.session.flush()

        # ---- ISO 27001:2022 MAIN CLAUSES (30 total) ----
        # ISMS management-system requirements, Clauses 4-10. Not audited as pass/fail
        # "controls" in the Annex A sense, but tracked the same way for evidence/status.
        iso_clauses = [
            # Clause 4 Context of the organization (4)
            ("4.1", "Understanding the organization and its context", "Context of the organization"),
            ("4.2", "Understanding the needs and expectations of interested parties", "Context of the organization"),
            ("4.3", "Determining the scope of the information security management system", "Context of the organization"),
            ("4.4", "Information security management system", "Context of the organization"),
            # Clause 5 Leadership (3)
            ("5.1", "Leadership and commitment", "Leadership"),
            ("5.2", "Policy", "Leadership"),
            ("5.3", "Organizational roles, responsibilities and authorities", "Leadership"),
            # Clause 6 Planning (5)
            ("6.1.1", "Actions to address risks and opportunities - General", "Planning"),
            ("6.1.2", "Information security risk assessment", "Planning"),
            ("6.1.3", "Information security risk treatment", "Planning"),
            ("6.2", "Information security objectives and planning to achieve them", "Planning"),
            ("6.3", "Planning of changes", "Planning"),
            # Clause 7 Support (7)
            ("7.1", "Resources", "Support"),
            ("7.2", "Competence", "Support"),
            ("7.3", "Awareness", "Support"),
            ("7.4", "Communication", "Support"),
            ("7.5.1", "Documented information - General", "Support"),
            ("7.5.2", "Creating and updating documented information", "Support"),
            ("7.5.3", "Control of documented information", "Support"),
            # Clause 8 Operation (3)
            ("8.1", "Operational planning and control", "Operation"),
            ("8.2", "Information security risk assessment", "Operation"),
            ("8.3", "Information security risk treatment", "Operation"),
            # Clause 9 Performance evaluation (6)
            ("9.1", "Monitoring, measurement, analysis and evaluation", "Performance evaluation"),
            ("9.2.1", "Internal audit - General", "Performance evaluation"),
            ("9.2.2", "Internal audit programme", "Performance evaluation"),
            ("9.3.1", "Management review - General", "Performance evaluation"),
            ("9.3.2", "Management review inputs", "Performance evaluation"),
            ("9.3.3", "Management review results", "Performance evaluation"),
            # Clause 10 Improvement (2)
            ("10.1", "Continual improvement", "Improvement"),
            ("10.2", "Nonconformity and corrective action", "Improvement"),
        ]

        for code, title, category in iso_clauses:
            db.session.add(Control(
                code=code, title=title, category=category,
                status='Not Assessed', framework_id=iso27001.id
            ))

        # ---- ISO 27001:2022 ANNEX A CONTROLS (93 total) ----
        # All controls start as 'Not Assessed' - status changes when evidence is uploaded
        iso_controls = [
            # A.5 Organizational Controls (37)
            ("A.5.1", "Policies for information security", "Organizational"),
            ("A.5.2", "Information security roles and responsibilities", "Organizational"),
            ("A.5.3", "Segregation of duties", "Organizational"),
            ("A.5.4", "Management responsibilities", "Organizational"),
            ("A.5.5", "Contact with authorities", "Organizational"),
            ("A.5.6", "Contact with special interest groups", "Organizational"),
            ("A.5.7", "Threat intelligence", "Organizational"),
            ("A.5.8", "Information security in project management", "Organizational"),
            ("A.5.9", "Inventory of information and other associated assets", "Organizational"),
            ("A.5.10", "Acceptable use of information and other associated assets", "Organizational"),
            ("A.5.11", "Return of assets", "Organizational"),
            ("A.5.12", "Classification of information", "Organizational"),
            ("A.5.13", "Labelling of information", "Organizational"),
            ("A.5.14", "Information transfer", "Organizational"),
            ("A.5.15", "Access control", "Organizational"),
            ("A.5.16", "Identity management", "Organizational"),
            ("A.5.17", "Authentication information", "Organizational"),
            ("A.5.18", "Access rights", "Organizational"),
            ("A.5.19", "Information security in supplier relationships", "Organizational"),
            ("A.5.20", "Addressing information security within supplier agreements", "Organizational"),
            ("A.5.21", "Managing information security in the ICT supply chain", "Organizational"),
            ("A.5.22", "Monitoring, review and change management of supplier services", "Organizational"),
            ("A.5.23", "Information security for use of cloud services", "Organizational"),
            ("A.5.24", "Information security incident management planning and preparation", "Organizational"),
            ("A.5.25", "Assessment and decision on information security events", "Organizational"),
            ("A.5.26", "Response to information security incidents", "Organizational"),
            ("A.5.27", "Learning from information security incidents", "Organizational"),
            ("A.5.28", "Collection of evidence", "Organizational"),
            ("A.5.29", "Information security during disruption", "Organizational"),
            ("A.5.30", "ICT readiness for business continuity", "Organizational"),
            ("A.5.31", "Legal, statutory, regulatory and contractual requirements", "Organizational"),
            ("A.5.32", "Intellectual property rights", "Organizational"),
            ("A.5.33", "Protection of records", "Organizational"),
            ("A.5.34", "Privacy and protection of PII", "Organizational"),
            ("A.5.35", "Independent review of information security", "Organizational"),
            ("A.5.36", "Compliance with policies, rules and standards for information security", "Organizational"),
            ("A.5.37", "Documented operating procedures", "Organizational"),
            # A.6 People Controls (8)
            ("A.6.1", "Screening", "People"),
            ("A.6.2", "Terms and conditions of employment", "People"),
            ("A.6.3", "Information security awareness, education and training", "People"),
            ("A.6.4", "Disciplinary process", "People"),
            ("A.6.5", "Responsibilities after termination or change of employment", "People"),
            ("A.6.6", "Confidentiality or non-disclosure agreements", "People"),
            ("A.6.7", "Remote working", "People"),
            ("A.6.8", "Information security event reporting", "People"),
            # A.7 Physical Controls (14)
            ("A.7.1", "Physical security perimeters", "Physical"),
            ("A.7.2", "Physical entry", "Physical"),
            ("A.7.3", "Securing offices, rooms and facilities", "Physical"),
            ("A.7.4", "Physical security monitoring", "Physical"),
            ("A.7.5", "Protecting against physical and environmental threats", "Physical"),
            ("A.7.6", "Working in secure areas", "Physical"),
            ("A.7.7", "Clear desk and clear screen", "Physical"),
            ("A.7.8", "Equipment siting and protection", "Physical"),
            ("A.7.9", "Security of assets off-premises", "Physical"),
            ("A.7.10", "Storage media", "Physical"),
            ("A.7.11", "Supporting utilities", "Physical"),
            ("A.7.12", "Cabling security", "Physical"),
            ("A.7.13", "Equipment maintenance", "Physical"),
            ("A.7.14", "Secure disposal or re-use of equipment", "Physical"),
            # A.8 Technological Controls (34)
            ("A.8.1", "User endpoint devices", "Technological"),
            ("A.8.2", "Privileged access rights", "Technological"),
            ("A.8.3", "Information access restriction", "Technological"),
            ("A.8.4", "Access to source code", "Technological"),
            ("A.8.5", "Secure authentication", "Technological"),
            ("A.8.6", "Capacity management", "Technological"),
            ("A.8.7", "Protection against malware", "Technological"),
            ("A.8.8", "Management of technical vulnerabilities", "Technological"),
            ("A.8.9", "Configuration management", "Technological"),
            ("A.8.10", "Information deletion", "Technological"),
            ("A.8.11", "Data masking", "Technological"),
            ("A.8.12", "Data leakage prevention", "Technological"),
            ("A.8.13", "Information backup", "Technological"),
            ("A.8.14", "Redundancy of information processing facilities", "Technological"),
            ("A.8.15", "Logging", "Technological"),
            ("A.8.16", "Monitoring activities", "Technological"),
            ("A.8.17", "Clock synchronization", "Technological"),
            ("A.8.18", "Use of privileged utility programs", "Technological"),
            ("A.8.19", "Installation of software on operational systems", "Technological"),
            ("A.8.20", "Networks security", "Technological"),
            ("A.8.21", "Security of network services", "Technological"),
            ("A.8.22", "Segregation of networks", "Technological"),
            ("A.8.23", "Web filtering", "Technological"),
            ("A.8.24", "Use of cryptography", "Technological"),
            ("A.8.25", "Secure development life cycle", "Technological"),
            ("A.8.26", "Application security requirements", "Technological"),
            ("A.8.27", "Secure system architecture and engineering principles", "Technological"),
            ("A.8.28", "Secure coding", "Technological"),
            ("A.8.29", "Security testing in development and acceptance", "Technological"),
            ("A.8.30", "Outsourced development", "Technological"),
            ("A.8.31", "Separation of development, test and production environments", "Technological"),
            ("A.8.32", "Change management", "Technological"),
            ("A.8.33", "Test information", "Technological"),
            ("A.8.34", "Protection of information systems during audit testing", "Technological"),
        ]

        for code, title, category in iso_controls:
            db.session.add(Control(
                code=code, title=title, category=category,
                status='Not Assessed', framework_id=iso27001.id
            ))

        # ---- SOC 2 TRUST SERVICE CRITERIA FRAMEWORK ----
        soc2 = Framework(
            name='SOC 2',
            description='AICPA Trust Service Criteria for Security, Availability, Processing Integrity, Confidentiality, and Privacy',
            category='Security',
            icon='shield-halved',
            status='Not Started',
            owner='Harsha P',
            controls_detail='Common Criteria (CC1-CC9) - Security Trust Service Category',
        )
        db.session.add(soc2)
        db.session.flush()

        soc2_controls = [
            ("CC1.1", "Board oversight of internal control", "Control Environment"),
            ("CC1.2", "Management philosophy and operating style", "Control Environment"),
            ("CC1.3", "Organizational structure and reporting lines", "Control Environment"),
            ("CC1.4", "Commitment to competence", "Control Environment"),
            ("CC2.1", "Internal communication of information security objectives", "Communication and Information"),
            ("CC2.2", "Communication with external parties", "Communication and Information"),
            ("CC2.3", "Quality of information used for control decisions", "Communication and Information"),
            ("CC3.1", "Risk identification and assessment process", "Risk Assessment"),
            ("CC3.2", "Fraud risk consideration", "Risk Assessment"),
            ("CC3.3", "Assessment of significant change impact", "Risk Assessment"),
            ("CC4.1", "Ongoing monitoring of control effectiveness", "Monitoring Activities"),
            ("CC4.2", "Evaluation and communication of control deficiencies", "Monitoring Activities"),
            ("CC5.1", "Selection and development of control activities", "Control Activities"),
            ("CC5.2", "Technology general controls", "Control Activities"),
            ("CC5.3", "Policies and procedures deployment", "Control Activities"),
            ("CC6.1", "Logical access security controls", "Logical and Physical Access"),
            ("CC6.2", "Registration and authorization of new users", "Logical and Physical Access"),
            ("CC6.3", "Access removal on termination or role change", "Logical and Physical Access"),
            ("CC6.6", "Protection against external threats", "Logical and Physical Access"),
            ("CC6.7", "Restriction of data transmission and movement", "Logical and Physical Access"),
            ("CC6.8", "Prevention and detection of unauthorized software", "Logical and Physical Access"),
            ("CC7.1", "Detection of security events and vulnerabilities", "System Operations"),
            ("CC7.2", "Monitoring of system components for anomalies", "System Operations"),
            ("CC7.3", "Evaluation of security incidents", "System Operations"),
            ("CC7.4", "Incident response and recovery procedures", "System Operations"),
            ("CC8.1", "Change management process for infrastructure and software", "Change Management"),
            ("CC9.1", "Risk mitigation for business disruptions", "Risk Mitigation"),
            ("CC9.2", "Vendor and business partner risk management", "Risk Mitigation"),
        ]

        for code, title, category in soc2_controls:
            db.session.add(Control(
                code=code, title=title, category=category,
                status='Not Assessed', framework_id=soc2.id
            ))

        db.session.commit()

        # ---- INTEGRATED PLATFORMS (VENDORS) ----
        vendors_data = [
            dict(name='AWS', category='Cloud Infrastructure', risk_tier='Critical', risk_score=82,
                 status='Approved', contact_name='AWS Support', contact_email='security@aws.com',
                 last_assessment='2026-06-15', next_assessment='2026-12-15',
                 compliance=['SOC 2', 'ISO 27001', 'HIPAA']),
            dict(name='Google Workspace', category='Communication', risk_tier='High', risk_score=74,
                 status='Approved', contact_name='Google Workspace Admin', contact_email='security@google.com',
                 last_assessment='2026-05-20', next_assessment='2026-11-20',
                 compliance=['SOC 2', 'ISO 27001']),
            dict(name='GitHub', category='Development', risk_tier='Critical', risk_score=78,
                 status='Approved', contact_name='GitHub Support', contact_email='security@github.com',
                 last_assessment='2026-04-10', next_assessment='2026-10-10',
                 compliance=['SOC 2', 'ISO 27001']),
            dict(name='Slack', category='Communication', risk_tier='Medium', risk_score=60,
                 status='Approved', contact_name='Slack Support', contact_email='security@slack.com',
                 last_assessment='2026-03-15', next_assessment='2026-09-15',
                 compliance=['SOC 2']),
        ]
        vendors = {}
        for data in vendors_data:
            vendor = Vendor(**data)
            db.session.add(vendor)
            vendors[data['name']] = vendor
        db.session.flush()

        # ---- EMPLOYEES ----
        employees_data = [
            ('Aditi Rao', 'aditi.rao@midevops.io', 'Engineering', True, True, True),
            ('Karan Mehta', 'karan.mehta@midevops.io', 'Engineering', True, True, True),
            ('Neha Verma', 'neha.verma@midevops.io', 'IT', True, True, True),
            ('Rohan Iyer', 'rohan.iyer@midevops.io', 'Security', True, True, True),
            ('Sanya Kapoor', 'sanya.kapoor@midevops.io', 'Finance', True, True, True),
            ('Farhan Ali', 'farhan.ali@midevops.io', 'Engineering', True, True, True),
            ('Divya Nair', 'divya.nair@midevops.io', 'HR', True, True, True),
            ('Arjun Malhotra', 'arjun.malhotra@midevops.io', 'IT', True, True, True),
            ('Meera Pillai', 'meera.pillai@midevops.io', 'Finance', True, True, False),
            ('Vikram Chawla', 'vikram.chawla@midevops.io', 'Security', True, True, False),
        ]
        employees = {}
        for name, email, department, monitoring, device_compliant, policy_ack in employees_data:
            employee = Employee(
                name=name, email=email, department=department, source='Manual', status='Active',
                monitoring_agent_installed=monitoring, device_security_compliant=device_compliant,
                policy_acknowledged=policy_ack,
            )
            db.session.add(employee)
            employees[name] = employee
        db.session.flush()

        # ---- TRAINING CAMPAIGNS ----
        isms_training = TrainingCampaign(name='ISMS Training', status='Completed',
            launch_date='10 Jul 2024', end_date='31 Jan 2025')
        isms_campaign = TrainingCampaign(name='ISMS Training Campaign', status='Completed',
            launch_date='19 Jun 2024', end_date='30 Sept 2024')
        db.session.add_all([isms_training, isms_campaign])
        db.session.flush()

        incomplete_pairs = {('Vikram Chawla', isms_training.id), ('Meera Pillai', isms_campaign.id)}
        for campaign in (isms_training, isms_campaign):
            for name, employee in employees.items():
                completed = (name, campaign.id) not in incomplete_pairs
                db.session.add(TrainingCampaignEnrollment(
                    campaign_id=campaign.id, employee_id=employee.id, completed=completed,
                ))

        # ---- EMPLOYEE ACCESS (per integrated platform) ----
        access_grants = [
            ('Aditi Rao', 'AWS', 'Admin'), ('Aditi Rao', 'GitHub', 'Standard'),
            ('Karan Mehta', 'GitHub', 'Admin'), ('Karan Mehta', 'AWS', 'Standard'),
            ('Neha Verma', 'Google Workspace', 'Admin'),
            ('Rohan Iyer', 'AWS', 'Admin'), ('Rohan Iyer', 'Slack', 'Standard'),
            ('Sanya Kapoor', 'Google Workspace', 'Standard'),
            ('Farhan Ali', 'GitHub', 'Standard'), ('Farhan Ali', 'Slack', 'Standard'),
            ('Divya Nair', 'Google Workspace', 'Standard'), ('Divya Nair', 'Slack', 'Standard'),
            ('Arjun Malhotra', 'AWS', 'Standard'), ('Arjun Malhotra', 'Google Workspace', 'Standard'),
            ('Meera Pillai', 'Google Workspace', 'Standard'),
            ('Vikram Chawla', 'AWS', 'Read-only'),
        ]
        for employee_name, vendor_name, access_level in access_grants:
            db.session.add(EmployeeAccess(
                employee_id=employees[employee_name].id, vendor_id=vendors[vendor_name].id,
                access_level=access_level,
            ))

        # ---- ACCESS REVIEW ----
        access_review = AccessReview(
            name='Q3 2026 Access Review', owner='Compliance Team', status='Overdue',
            review_period_start='2026-05-01', review_period_end='2026-07-31', recurrence='Once',
        )
        access_review.applications = [vendors['AWS'], vendors['GitHub']]
        db.session.add(access_review)

        db.session.commit()

        # ---- HISTORICAL SNAPSHOTS (last 14 days, for the dashboard trend/deltas) ----
        # Today's real snapshot is captured lazily on first dashboard load, so this
        # backfill only covers days -14..-1, ending just before the real (currently
        # all-zero, freshly-seeded) state.
        rng = random.Random(42)
        iso_total = len(iso_clauses) + len(iso_controls)
        for days_ago in range(14, 0, -1):
            snap_date = date.today() - timedelta(days=days_ago)
            score = min(38, 18 + (14 - days_ago) * 1.5 + rng.uniform(-2, 2))
            passing = round(iso_total * score / 100)
            db.session.add(ComplianceSnapshot(
                framework_id=iso27001.id,
                score=round(score, 1),
                passing=passing,
                failing=rng.randint(2, 6),
                not_assessed=iso_total - passing - rng.randint(2, 6),
                not_applicable=0,
                total_controls=iso_total,
                snapshot_date=snap_date,
            ))
            db.session.add(DashboardSnapshot(
                snapshot_date=snap_date,
                open_risks=rng.randint(3, 8),
                active_policies=rng.randint(1, 4),
                pending_evidence=rng.randint(0, 3),
            ))

        # ---- RECENT ACTIVITY (for the dashboard feed) ----
        activity_events = [
            ('created', 'Framework', 'ISO 27001:2022', 'Harsha S created the ISO 27001:2022 framework', 13),
            ('created', 'Vendor', 'AWS', 'Harsha S added vendor "AWS"', 12),
            ('created', 'Vendor', 'GitHub', 'Harsha S added vendor "GitHub"', 12),
            ('created', 'Employee', 'Aditi Rao', 'Harsha S added employee "Aditi Rao"', 10),
            ('created', 'TrainingCampaign', 'ISMS Training', 'Harsha S created campaign "ISMS Training"', 9),
            ('created', 'AccessReview', 'Q3 2026 Access Review', 'Harsha S created access review "Q3 2026 Access Review"', 5),
            ('updated', 'Vendor', 'AWS', 'Harsha S updated vendor "AWS"', 3),
            ('acknowledged', 'Policy', 'ISMS Training', 'Harsha S recorded 8 acknowledgement(s) for policy "ISMS Training"', 2),
            ('created', 'Employee', 'Vikram Chawla', 'Harsha S added employee "Vikram Chawla"', 1),
        ]
        for action, entity_type, entity_name, description, days_ago in activity_events:
            db.session.add(ActivityLog(
                user_id=admin.id, action=action, entity_type=entity_type,
                entity_name=entity_name, description=description,
                created_at=datetime.utcnow() - timedelta(days=days_ago, hours=rng.randint(0, 20)),
            ))

        db.session.commit()

        print("Database seeded successfully!")
        print(f"  Users: {User.query.count()}")
        print(f"  Frameworks: {Framework.query.count()}")
        print(f"  Controls: {Control.query.count()} (ISO 27001: {iso_total} + SOC 2: {len(soc2_controls)})")
        print(f"  Risks: 0 (add your own)")
        print(f"  Policies: 0 (add your own)")
        print(f"  Audits: 0 (add your own)")
        print(f"  Vendors: {Vendor.query.count()}")
        print(f"  Assets: 0 (add your own)")
        print(f"  Employees: {Employee.query.count()}")
        print(f"  Training Campaigns: {TrainingCampaign.query.count()}")
        print(f"  Access Reviews: {AccessReview.query.count()}")
        print(f"  Compliance Snapshots: {ComplianceSnapshot.query.count()} (14-day backfill)")
        print(f"  Dashboard Snapshots: {DashboardSnapshot.query.count()} (14-day backfill)")
        print(f"  Activity Log: {ActivityLog.query.count()} (seeded history)")


def seed_demo_assets():
    """
    Add a handful of demo assets across every Asset Management category.
    Additive only (checks Asset.query.count() first) - safe to run against a
    database that already has real data, unlike seed_database() which wipes everything.

    Run: python -m app.seed assets
    """
    app = create_app()
    with app.app_context():
        if Asset.query.count() > 0:
            print(f"Assets table already has {Asset.query.count()} row(s) - skipping demo seed.")
            return

        demo_assets = [
            # (name, type, resource_id, cloud_provider, region, environment, classification, owner)
            ("web-app-prod-01", "Compute Instances", "arn:aws:ec2:us-east-1:111122223333:instance/i-0abcd1234ef567890", "AWS", "us-east-1", "Production", "Confidential", "Neha Verma"),
            ("api-gateway-prod-02", "Compute Instances", "arn:aws:ec2:ap-south-1:111122223333:instance/i-0fedcba9876543210", "AWS", "ap-south-1", "Production", "Confidential", "Neha Verma"),
            ("eks-prod-cluster", "Container Platforms", "arn:aws:eks:us-east-1:111122223333:cluster/eks-prod-cluster", "AWS", "us-east-1", "Production", "Confidential", "Rohan Iyer"),
            ("ecs-app-cluster", "Container Platforms", "arn:aws:ecs:us-east-1:111122223333:cluster/ecs-app-cluster", "AWS", "us-east-1", "Staging", "Internal", "Rohan Iyer"),
            ("app-data-bucket-prod", "Storage & Databases", "arn:aws:s3:::app-data-bucket-prod", "AWS", "us-east-1", "Production", "Restricted", "Arjun Malhotra"),
            ("prod-postgres-db", "Storage & Databases", "arn:aws:rds:us-east-1:111122223333:db:prod-postgres-db", "AWS", "us-east-1", "Production", "Restricted", "Arjun Malhotra"),
            ("prod-vpc-main", "Virtual Network (VPCs)", "arn:aws:ec2:us-east-1:111122223333:vpc/vpc-0a1b2c3d4e5f60789", "AWS", "us-east-1", "Production", "Internal", "Neha Verma"),
            ("staging-vpc", "Virtual Network (VPCs)", "arn:aws:ec2:ap-south-1:111122223333:vpc/vpc-0f9e8d7c6b5a41230", "AWS", "ap-south-1", "Staging", "Internal", "Neha Verma"),
            ("evidence-processor-fn", "Serverless Functions", "arn:aws:lambda:us-east-1:111122223333:function:evidence-processor-fn", "AWS", "us-east-1", "Production", "Internal", "Farhan Ali"),
            ("webhook-handler-fn", "Serverless Functions", "arn:aws:lambda:us-east-1:111122223333:function:webhook-handler-fn", "AWS", "us-east-1", "Production", "Internal", "Farhan Ali"),
            ("cloudtrail-org-logs", "Monitoring & Logging", "arn:aws:cloudtrail:us-east-1:111122223333:trail/org-logs", "AWS", "us-east-1", "Production", "Internal", "Rohan Iyer"),
            ("app-log-group", "Monitoring & Logging", "arn:aws:logs:us-east-1:111122223333:log-group:/app/prod", "AWS", "us-east-1", "Production", "Internal", "Rohan Iyer"),
            ("prod-data-encryption-key", "Key Management", "arn:aws:kms:us-east-1:111122223333:key/1a2b3c4d-5e6f-7890-abcd-ef1234567890", "AWS", "us-east-1", "Production", "Restricted", "Rohan Iyer"),
            ("backup-encryption-key", "Key Management", "arn:aws:kms:us-east-1:111122223333:key/2b3c4d5e-6f78-9012-bcde-f12345678901", "AWS", "us-east-1", "Production", "Restricted", "Rohan Iyer"),
            ("iPhone-13-Aditi-Rao", "Mobile Devices", "MDM-DEV-00291", "N/A", "", "Corporate", "Confidential", "Aditi Rao"),
            ("MacBook-Pro-Karan-Mehta", "Mobile Devices", "MDM-DEV-00417", "N/A", "", "Corporate", "Confidential", "Karan Mehta"),
            ("aditi.rao@midevops.io", "Identity Users", "arn:aws:iam::111122223333:user/aditi.rao", "AWS", "", "Production", "Internal", "Neha Verma"),
            ("svc-ci-deploy", "Identity Users", "arn:aws:iam::111122223333:user/svc-ci-deploy", "AWS", "", "Production", "Internal", "Karan Mehta"),
            ("ReadOnlyAuditorRole", "Identity Roles", "arn:aws:iam::111122223333:role/ReadOnlyAuditorRole", "AWS", "", "Production", "Internal", "Rohan Iyer"),
            ("EKSNodeInstanceRole", "Identity Roles", "arn:aws:iam::111122223333:role/EKSNodeInstanceRole", "AWS", "", "Production", "Internal", "Rohan Iyer"),
            ("Engineering-Admins", "Identity Groups", "arn:aws:iam::111122223333:group/Engineering-Admins", "AWS", "", "Production", "Internal", "Neha Verma"),
            ("Security-ReadOnly", "Identity Groups", "arn:aws:iam::111122223333:group/Security-ReadOnly", "AWS", "", "Production", "Internal", "Rohan Iyer"),
            ("migrc-platform", "Code Repo", "github.com/midevops/migrc-platform", "GitHub", "", "Production", "Internal", "Karan Mehta"),
            ("infra-terraform", "Code Repo", "github.com/midevops/infra-terraform", "GitHub", "", "Production", "Internal", "Farhan Ali"),
        ]

        for name, atype, resource_id, cloud_provider, region, environment, classification, owner in demo_assets:
            db.session.add(Asset(
                name=name, type=atype, resource_id=resource_id, cloud_provider=cloud_provider,
                region=region, environment=environment, classification=classification,
                owner=owner, status='Active',
            ))
        db.session.commit()
        print(f"Seeded {len(demo_assets)} demo assets across {len(set(a[1] for a in demo_assets))} categories.")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'assets':
        seed_demo_assets()
    else:
        seed_database()
