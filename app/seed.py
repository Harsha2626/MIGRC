"""
Seed database with:
- Default admin user
- ISO 27001:2022 framework + 93 Annex A controls (all set to 'Not Assessed')

All other modules (risks, policies, audits, vendors, assets, training, access reviews)
start empty - data should be added by the user through the application.

Run: python -m app.seed
"""
from app import create_app
from app.models import db, User, Framework, Control


def seed_database():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        # ---- DEFAULT USER ----
        admin = User(email='harsha@migrc.com', name='Harsha P', role='Admin')
        admin.set_password('admin123')
        db.session.add(admin)

        # ---- ISO 27001:2022 FRAMEWORK ----
        iso27001 = Framework(
            name='ISO 27001:2022',
            description='International standard for Information Security Management Systems (ISMS) with 93 Annex A controls',
            category='Security',
            icon='globe',
            status='Not Started',
            owner='Harsha P',
            controls_detail='Organizational (37) + People (8) + Physical (14) + Technological (34)',
        )
        db.session.add(iso27001)
        db.session.flush()

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

        db.session.commit()

        print("Database seeded successfully!")
        print(f"  Users: {User.query.count()}")
        print(f"  Frameworks: {Framework.query.count()}")
        print(f"  Controls: {Control.query.count()} (ISO 27001 Annex A)")
        print(f"  Risks: 0 (add your own)")
        print(f"  Policies: 0 (add your own)")
        print(f"  Audits: 0 (add your own)")
        print(f"  Vendors: 0 (add your own)")
        print(f"  Assets: 0 (add your own)")


if __name__ == '__main__':
    seed_database()
