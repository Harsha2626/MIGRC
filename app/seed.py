"""
Seed database with:
- Default admin user
- ISO 27001:2022 framework: 30 main-clause requirements (4-10) + 93 Annex A controls (all set to 'Not Assessed')

All other modules (risks, policies, audits, vendors, assets, training, access reviews)
start empty - data should be added by the user through the application.

Run: python -m app.seed
"""
import os
import sys
import random
from datetime import date, datetime, timedelta
from app import create_app
from app.models import (
    db, User, Framework, Control, Vendor, Employee, TrainingCampaign,
    TrainingCampaignEnrollment, EmployeeAccess, AccessReview,
    ComplianceSnapshot, DashboardSnapshot, ActivityLog, Asset,
    Policy,
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
            ("4.1", "Understanding the organization and its context", "Context of the organization",
             "The organization must determine external and internal issues relevant to its purpose that affect its ability to achieve the intended outcomes of its information security management system."),
            ("4.2", "Understanding the needs and expectations of interested parties", "Context of the organization",
             "The organization must identify interested parties relevant to the ISMS and determine their requirements, including legal, regulatory, and contractual obligations."),
            ("4.3", "Determining the scope of the information security management system", "Context of the organization",
             "The organization must determine the boundaries and applicability of the ISMS, considering internal and external issues, interested party requirements, and interfaces with other organizations."),
            ("4.4", "Information security management system", "Context of the organization",
             "The organization must establish, implement, maintain, and continually improve an ISMS, including the processes needed and their interactions."),
            # Clause 5 Leadership (3)
            ("5.1", "Leadership and commitment", "Leadership",
             "Top management must demonstrate leadership and commitment to the ISMS by ensuring policies and objectives are established, resources are available, and the importance of information security is communicated."),
            ("5.2", "Policy", "Leadership",
             "Top management must establish an information security policy appropriate to the organization's purpose, including commitments to satisfy requirements and continually improve the ISMS."),
            ("5.3", "Organizational roles, responsibilities and authorities", "Leadership",
             "Top management must assign and communicate responsibilities and authorities for roles relevant to information security."),
            # Clause 6 Planning (5)
            ("6.1.1", "Actions to address risks and opportunities - General", "Planning",
             "When planning the ISMS, the organization must determine risks and opportunities that need to be addressed to ensure the ISMS achieves its intended outcomes and prevents undesired effects."),
            ("6.1.2", "Information security risk assessment", "Planning",
             "The organization must define and apply an information security risk assessment process that establishes and maintains risk criteria, identifies risks, and analyzes and evaluates them."),
            ("6.1.3", "Information security risk treatment", "Planning",
             "The organization must define and apply a risk treatment process to select appropriate treatment options, determine necessary controls, and produce a Statement of Applicability."),
            ("6.2", "Information security objectives and planning to achieve them", "Planning",
             "The organization must establish measurable information security objectives at relevant functions and levels, along with plans to achieve them."),
            ("6.3", "Planning of changes", "Planning",
             "When the organization determines the need for changes to the ISMS, the changes must be carried out in a planned manner."),
            # Clause 7 Support (7)
            ("7.1", "Resources", "Support",
             "The organization must determine and provide the resources needed for the establishment, implementation, maintenance, and continual improvement of the ISMS."),
            ("7.2", "Competence", "Support",
             "The organization must determine and ensure the necessary competence of persons doing work under its control that affects information security performance."),
            ("7.3", "Awareness", "Support",
             "Persons doing work under the organization's control must be aware of the information security policy, their contribution to the ISMS, and the implications of not conforming."),
            ("7.4", "Communication", "Support",
             "The organization must determine the need for internal and external communications relevant to the ISMS, including what, when, with whom, and how to communicate."),
            ("7.5.1", "Documented information - General", "Support",
             "The ISMS must include documented information required by the standard and any documented information the organization determines is necessary for its effectiveness."),
            ("7.5.2", "Creating and updating documented information", "Support",
             "When creating and updating documented information, the organization must ensure appropriate identification, format, and review/approval for suitability and adequacy."),
            ("7.5.3", "Control of documented information", "Support",
             "Documented information required by the ISMS must be controlled to ensure it is available and suitably protected, and properly distributed, stored, and retained."),
            # Clause 8 Operation (3)
            ("8.1", "Operational planning and control", "Operation",
             "The organization must plan, implement, and control the processes needed to meet information security requirements and to implement the actions determined in the planning clause."),
            ("8.2", "Information security risk assessment", "Operation",
             "The organization must perform information security risk assessments at planned intervals, or when significant changes are proposed or occur."),
            ("8.3", "Information security risk treatment", "Operation",
             "The organization must implement the information security risk treatment plan and retain documented information on the results of the risk treatment."),
            # Clause 9 Performance evaluation (6)
            ("9.1", "Monitoring, measurement, analysis and evaluation", "Performance evaluation",
             "The organization must evaluate the information security performance and the effectiveness of the ISMS through monitoring, measurement, analysis, and evaluation."),
            ("9.2.1", "Internal audit - General", "Performance evaluation",
             "The organization must conduct internal audits at planned intervals to provide information on whether the ISMS conforms to its own requirements and to the standard."),
            ("9.2.2", "Internal audit programme", "Performance evaluation",
             "The organization must plan, establish, implement, and maintain an audit programme, including the frequency, methods, responsibilities, and reporting of audits."),
            ("9.3.1", "Management review - General", "Performance evaluation",
             "Top management must review the organization's ISMS at planned intervals to ensure its continuing suitability, adequacy, and effectiveness."),
            ("9.3.2", "Management review inputs", "Performance evaluation",
             "Management reviews must consider the status of actions from previous reviews, changes in relevant issues, feedback on performance, and opportunities for continual improvement."),
            ("9.3.3", "Management review results", "Performance evaluation",
             "The results of management reviews must include decisions related to continual improvement opportunities and any need for changes to the ISMS."),
            # Clause 10 Improvement (2)
            ("10.1", "Continual improvement", "Improvement",
             "The organization must continually improve the suitability, adequacy, and effectiveness of the ISMS."),
            ("10.2", "Nonconformity and corrective action", "Improvement",
             "When a nonconformity occurs, the organization must react to it, evaluate the need for action to eliminate the causes, and review the effectiveness of any corrective action taken."),
        ]

        for code, title, category, description in iso_clauses:
            db.session.add(Control(
                code=code, title=title, category=category, description=description,
                status='Not Assessed', framework_id=iso27001.id
            ))

        # ---- ISO 27001:2022 ANNEX A CONTROLS (93 total) ----
        # All controls start as 'Not Assessed' - status changes when evidence is uploaded
        iso_controls = [
            # A.5 Organizational Controls (37)
            ("A.5.1", "Policies for information security", "Organizational",
             "Information security policy and topic-specific policies must be defined, approved by management, published, and communicated to relevant personnel and interested parties, and reviewed at planned intervals."),
            ("A.5.2", "Information security roles and responsibilities", "Organizational",
             "Information security roles and responsibilities must be defined and allocated according to the organization's needs."),
            ("A.5.3", "Segregation of duties", "Organizational",
             "Conflicting duties and areas of responsibility must be segregated to reduce opportunities for unauthorized or unintentional modification or misuse of the organization's assets."),
            ("A.5.4", "Management responsibilities", "Organizational",
             "Management must require all personnel to apply information security in accordance with the established policy and topic-specific policies."),
            ("A.5.5", "Contact with authorities", "Organizational",
             "The organization must establish and maintain contact with relevant authorities, such as law enforcement, regulatory bodies, and supervisory authorities."),
            ("A.5.6", "Contact with special interest groups", "Organizational",
             "The organization must establish and maintain contact with special interest groups, security forums, and professional associations relevant to information security."),
            ("A.5.7", "Threat intelligence", "Organizational",
             "Information relating to information security threats must be collected and analyzed to produce actionable threat intelligence."),
            ("A.5.8", "Information security in project management", "Organizational",
             "Information security must be integrated into project management, regardless of the type of project."),
            ("A.5.9", "Inventory of information and other associated assets", "Organizational",
             "An inventory of information and other associated assets, including owners, must be developed and maintained."),
            ("A.5.10", "Acceptable use of information and other associated assets", "Organizational",
             "Rules for the acceptable use and handling procedures of information and other associated assets must be identified, documented, and implemented."),
            ("A.5.11", "Return of assets", "Organizational",
             "Personnel and other interested parties must return all organizational assets in their possession upon change or termination of employment, contract, or agreement."),
            ("A.5.12", "Classification of information", "Organizational",
             "Information must be classified according to the confidentiality, integrity, availability, and relevant interested party requirements of the organization."),
            ("A.5.13", "Labelling of information", "Organizational",
             "An appropriate set of procedures for information labelling must be developed and implemented in accordance with the information classification scheme adopted by the organization."),
            ("A.5.14", "Information transfer", "Organizational",
             "Rules, procedures, and agreements for information transfer must be in place for all types of transfer facilities within the organization and between the organization and other parties."),
            ("A.5.15", "Access control", "Organizational",
             "Rules to control physical and logical access to information and other associated assets must be established and implemented based on business and information security requirements."),
            ("A.5.16", "Identity management", "Organizational",
             "The full lifecycle of identities must be managed to enable the unique identification of individuals and systems accessing the organization's information and other associated assets."),
            ("A.5.17", "Authentication information", "Organizational",
             "Allocation and management of authentication information must be controlled by a management process, including advising personnel on the appropriate handling of authentication information."),
            ("A.5.18", "Access rights", "Organizational",
             "Access rights to information and other associated assets must be provisioned, reviewed, modified, and removed in accordance with the organization's access control policy."),
            ("A.5.19", "Information security in supplier relationships", "Organizational",
             "Processes and procedures must be defined and implemented to manage the information security risks associated with the use of supplier's products or services."),
            ("A.5.20", "Addressing information security within supplier agreements", "Organizational",
             "Relevant information security requirements must be established and agreed with each supplier based on the type of supplier relationship."),
            ("A.5.21", "Managing information security in the ICT supply chain", "Organizational",
             "Processes must be defined and implemented to manage the information security risks associated with the ICT products and services supply chain."),
            ("A.5.22", "Monitoring, review and change management of supplier services", "Organizational",
             "The organization must regularly monitor, review, evaluate, and manage change in supplier information security practices and service delivery."),
            ("A.5.23", "Information security for use of cloud services", "Organizational",
             "Processes for acquisition, use, management, and exit from cloud services must be established in accordance with the organization's information security requirements."),
            ("A.5.24", "Information security incident management planning and preparation", "Organizational",
             "The organization must plan and prepare for managing information security incidents by defining, establishing, and communicating incident management processes, roles, and responsibilities."),
            ("A.5.25", "Assessment and decision on information security events", "Organizational",
             "The organization must assess information security events and decide if they are to be categorized as information security incidents."),
            ("A.5.26", "Response to information security incidents", "Organizational",
             "Information security incidents must be responded to in accordance with documented procedures."),
            ("A.5.27", "Learning from information security incidents", "Organizational",
             "Knowledge gained from analyzing and resolving information security incidents must be used to reduce the likelihood or impact of future incidents."),
            ("A.5.28", "Collection of evidence", "Organizational",
             "The organization must establish and implement procedures for the identification, collection, acquisition, and preservation of evidence related to information security events."),
            ("A.5.29", "Information security during disruption", "Organizational",
             "The organization must plan how to maintain information security at an appropriate level during disruption."),
            ("A.5.30", "ICT readiness for business continuity", "Organizational",
             "ICT readiness must be planned, implemented, maintained, and tested based on business continuity objectives and ICT continuity requirements."),
            ("A.5.31", "Legal, statutory, regulatory and contractual requirements", "Organizational",
             "Legal, statutory, regulatory, and contractual requirements relevant to information security and the organization's approach to meet them must be identified, documented, and kept up to date."),
            ("A.5.32", "Intellectual property rights", "Organizational",
             "The organization must implement appropriate procedures to protect intellectual property rights."),
            ("A.5.33", "Protection of records", "Organizational",
             "Records must be protected from loss, destruction, falsification, unauthorized access, and unauthorized release."),
            ("A.5.34", "Privacy and protection of PII", "Organizational",
             "The organization must identify and meet the requirements regarding the preservation of privacy and protection of personally identifiable information (PII) according to applicable laws and regulations."),
            ("A.5.35", "Independent review of information security", "Organizational",
             "The organization's approach to managing information security and its implementation must be independently reviewed at planned intervals or when significant changes occur."),
            ("A.5.36", "Compliance with policies, rules and standards for information security", "Organizational",
             "Compliance with the organization's information security policy, topic-specific policies, rules, and standards must be regularly reviewed."),
            ("A.5.37", "Documented operating procedures", "Organizational",
             "Operating procedures for information processing facilities must be documented and made available to personnel who need them."),
            # A.6 People Controls (8)
            ("A.6.1", "Screening", "People",
             "Background verification checks on all candidates must be carried out prior to joining the organization, and on an ongoing basis, in accordance with laws, regulations, and ethics, and proportional to business requirements and risk."),
            ("A.6.2", "Terms and conditions of employment", "People",
             "Employment contractual agreements must state personnel's and the organization's responsibilities for information security."),
            ("A.6.3", "Information security awareness, education and training", "People",
             "Personnel of the organization and relevant interested parties must receive appropriate information security awareness, education, and training, and regular updates on policies and procedures."),
            ("A.6.4", "Disciplinary process", "People",
             "A disciplinary process must be formalized and communicated to take action against personnel and other relevant parties who have committed an information security policy violation."),
            ("A.6.5", "Responsibilities after termination or change of employment", "People",
             "Information security responsibilities and duties that remain valid after termination or change of employment must be defined, enforced, and communicated to relevant personnel."),
            ("A.6.6", "Confidentiality or non-disclosure agreements", "People",
             "Confidentiality or non-disclosure agreements reflecting the organization's needs for the protection of information must be identified, documented, regularly reviewed, and signed by personnel and other relevant parties."),
            ("A.6.7", "Remote working", "People",
             "Security measures must be implemented when personnel work remotely to protect information accessed, processed, or stored outside the organization's premises."),
            ("A.6.8", "Information security event reporting", "People",
             "The organization must provide a mechanism for personnel to report observed or suspected information security events through appropriate channels in a timely manner."),
            # A.7 Physical Controls (14)
            ("A.7.1", "Physical security perimeters", "Physical",
             "Security perimeters must be defined and used to protect areas that contain information and other associated assets."),
            ("A.7.2", "Physical entry", "Physical",
             "Secure areas must be protected by appropriate entry controls and access points."),
            ("A.7.3", "Securing offices, rooms and facilities", "Physical",
             "Physical security for offices, rooms, and facilities must be designed and implemented."),
            ("A.7.4", "Physical security monitoring", "Physical",
             "Premises must be continuously monitored for unauthorized physical access."),
            ("A.7.5", "Protecting against physical and environmental threats", "Physical",
             "Protection against physical and environmental threats, such as natural disasters and other intentional or unintentional threats to infrastructure, must be designed and implemented."),
            ("A.7.6", "Working in secure areas", "Physical",
             "Security measures for working in secure areas must be designed and implemented."),
            ("A.7.7", "Clear desk and clear screen", "Physical",
             "Clear desk rules for papers and removable storage media, and clear screen rules for information processing facilities, must be defined and appropriately enforced."),
            ("A.7.8", "Equipment siting and protection", "Physical",
             "Equipment must be sited securely and protected to reduce the risks from environmental threats and hazards, and opportunities for unauthorized access."),
            ("A.7.9", "Security of assets off-premises", "Physical",
             "Off-site assets must be protected, taking into account the different risks of working outside the organization's premises."),
            ("A.7.10", "Storage media", "Physical",
             "Storage media must be managed through their life cycle of acquisition, use, transportation, and disposal in accordance with the organization's classification scheme and handling requirements."),
            ("A.7.11", "Supporting utilities", "Physical",
             "Information processing facilities must be protected from power failures and other disruptions caused by failures in supporting utilities."),
            ("A.7.12", "Cabling security", "Physical",
             "Cables carrying power, data, or supporting information services must be protected from interception, interference, or damage."),
            ("A.7.13", "Equipment maintenance", "Physical",
             "Equipment must be maintained correctly to ensure the availability, integrity, and confidentiality of information."),
            ("A.7.14", "Secure disposal or re-use of equipment", "Physical",
             "Items of equipment containing storage media must be verified to ensure that any sensitive data and licensed software have been removed or securely overwritten prior to disposal or re-use."),
            # A.8 Technological Controls (34)
            ("A.8.1", "User endpoint devices", "Technological",
             "Information stored on, processed by, or accessible via user endpoint devices must be protected."),
            ("A.8.2", "Privileged access rights", "Technological",
             "The allocation and use of privileged access rights must be restricted and managed."),
            ("A.8.3", "Information access restriction", "Technological",
             "Access to information and other associated assets must be restricted in accordance with the established access control policy."),
            ("A.8.4", "Access to source code", "Technological",
             "Read and write access to source code, development tools, and software libraries must be appropriately managed."),
            ("A.8.5", "Secure authentication", "Technological",
             "Secure authentication technologies and procedures must be implemented based on information access restrictions and the access control policy."),
            ("A.8.6", "Capacity management", "Technological",
             "The use of resources must be monitored and adjusted in line with current and expected capacity requirements."),
            ("A.8.7", "Protection against malware", "Technological",
             "Protection against malware must be implemented and supported by appropriate user awareness."),
            ("A.8.8", "Management of technical vulnerabilities", "Technological",
             "Information about technical vulnerabilities of information systems in use must be obtained, the organization's exposure to such vulnerabilities evaluated, and appropriate measures taken."),
            ("A.8.9", "Configuration management", "Technological",
             "Configurations, including security configurations, of hardware, software, services, and networks must be established, documented, implemented, monitored, and reviewed."),
            ("A.8.10", "Information deletion", "Technological",
             "Information stored in information systems, devices, or on any other storage media must be deleted when no longer required."),
            ("A.8.11", "Data masking", "Technological",
             "Data masking must be used in accordance with the organization's access control policy and other related topic-specific policies, and business requirements, taking applicable legislation into consideration."),
            ("A.8.12", "Data leakage prevention", "Technological",
             "Data leakage prevention measures must be applied to systems, networks, and other devices that process, store, or transmit sensitive information."),
            ("A.8.13", "Information backup", "Technological",
             "Backup copies of information, software, and systems must be maintained and regularly tested in accordance with an agreed backup policy."),
            ("A.8.14", "Redundancy of information processing facilities", "Technological",
             "Information processing facilities must be implemented with sufficient redundancy to meet availability requirements."),
            ("A.8.15", "Logging", "Technological",
             "Logs that record activities, exceptions, faults, and other relevant events must be produced, stored, protected, and analyzed."),
            ("A.8.16", "Monitoring activities", "Technological",
             "Networks, systems, and applications must be monitored for anomalous behavior, and appropriate actions taken to evaluate potential information security incidents."),
            ("A.8.17", "Clock synchronization", "Technological",
             "The clocks of information processing systems used by the organization must be synchronized to approved time sources."),
            ("A.8.18", "Use of privileged utility programs", "Technological",
             "The use of utility programs that can override system and application controls must be restricted and tightly controlled."),
            ("A.8.19", "Installation of software on operational systems", "Technological",
             "Procedures and measures must be implemented to securely manage software installation on operational systems."),
            ("A.8.20", "Networks security", "Technological",
             "Networks and network devices must be secured, managed, and controlled to protect information in systems and applications."),
            ("A.8.21", "Security of network services", "Technological",
             "Security mechanisms, service levels, and requirements of network services must be identified, implemented, and monitored."),
            ("A.8.22", "Segregation of networks", "Technological",
             "Groups of information services, users, and information systems must be segregated in the organization's networks."),
            ("A.8.23", "Web filtering", "Technological",
             "Access to external websites must be managed to reduce exposure to malicious content."),
            ("A.8.24", "Use of cryptography", "Technological",
             "Rules for the effective use of cryptography, including cryptographic key management, must be defined and implemented."),
            ("A.8.25", "Secure development life cycle", "Technological",
             "Rules for the secure development of software and systems must be established and applied."),
            ("A.8.26", "Application security requirements", "Technological",
             "Information security requirements must be identified, specified, and approved when developing or acquiring applications."),
            ("A.8.27", "Secure system architecture and engineering principles", "Technological",
             "Principles for engineering secure systems must be established, documented, maintained, and applied to information system development activities."),
            ("A.8.28", "Secure coding", "Technological",
             "Secure coding principles must be applied to software development."),
            ("A.8.29", "Security testing in development and acceptance", "Technological",
             "Security testing processes must be defined and implemented in the development life cycle."),
            ("A.8.30", "Outsourced development", "Technological",
             "The organization must direct, monitor, and review the activities related to outsourced system development."),
            ("A.8.31", "Separation of development, test and production environments", "Technological",
             "Development, testing, and production environments must be separated and secured."),
            ("A.8.32", "Change management", "Technological",
             "Changes to information processing facilities and information systems must be subject to change management procedures."),
            ("A.8.33", "Test information", "Technological",
             "Test information must be appropriately selected, protected, and managed."),
            ("A.8.34", "Protection of information systems during audit testing", "Technological",
             "Audit tests and other assurance activities involving assessment of operational systems must be planned and agreed between the tester and appropriate management."),
        ]

        for code, title, category, description in iso_controls:
            db.session.add(Control(
                code=code, title=title, category=category, description=description,
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
            ("CC1.1", "Board oversight of internal control", "Control Environment",
             "The entity demonstrates a commitment to integrity and ethical values, with the board of directors exercising oversight responsibility for the development and performance of internal control."),
            ("CC1.2", "Management philosophy and operating style", "Control Environment",
             "Management establishes structures, reporting lines, and appropriate authorities and responsibilities in pursuit of objectives, reflecting a consistent philosophy and operating style toward internal control."),
            ("CC1.3", "Organizational structure and reporting lines", "Control Environment",
             "The entity establishes organizational structures, reporting lines, and appropriate authorities and responsibilities to support the achievement of objectives."),
            ("CC1.4", "Commitment to competence", "Control Environment",
             "The entity demonstrates a commitment to attract, develop, and retain competent individuals in alignment with objectives."),
            ("CC2.1", "Internal communication of information security objectives", "Communication and Information",
             "The entity obtains or generates and uses relevant, quality information to support the functioning of internal control, and communicates security objectives and responsibilities internally."),
            ("CC2.2", "Communication with external parties", "Communication and Information",
             "The entity communicates with external parties regarding matters affecting the functioning of internal control."),
            ("CC2.3", "Quality of information used for control decisions", "Communication and Information",
             "The entity ensures information used to support the functioning of internal control is relevant, timely, and of adequate quality."),
            ("CC3.1", "Risk identification and assessment process", "Risk Assessment",
             "The entity specifies objectives with sufficient clarity to enable the identification and assessment of risks relating to those objectives."),
            ("CC3.2", "Fraud risk consideration", "Risk Assessment",
             "The entity considers the potential for fraud in assessing risks to the achievement of objectives."),
            ("CC3.3", "Assessment of significant change impact", "Risk Assessment",
             "The entity identifies and assesses changes that could significantly impact the system of internal control."),
            ("CC4.1", "Ongoing monitoring of control effectiveness", "Monitoring Activities",
             "The entity selects, develops, and performs ongoing and/or separate evaluations to ascertain whether the components of internal control are present and functioning."),
            ("CC4.2", "Evaluation and communication of control deficiencies", "Monitoring Activities",
             "The entity evaluates and communicates internal control deficiencies in a timely manner to the parties responsible for taking corrective action."),
            ("CC5.1", "Selection and development of control activities", "Control Activities",
             "The entity selects and develops control activities that contribute to the mitigation of risks to the achievement of objectives to acceptable levels."),
            ("CC5.2", "Technology general controls", "Control Activities",
             "The entity selects and develops general control activities over technology to support the achievement of objectives."),
            ("CC5.3", "Policies and procedures deployment", "Control Activities",
             "The entity deploys control activities through policies that establish what is expected and procedures that put policies into action."),
            ("CC6.1", "Logical access security controls", "Logical and Physical Access",
             "The entity implements logical access security software, infrastructure, and architectures over protected information assets to protect them from security events."),
            ("CC6.2", "Registration and authorization of new users", "Logical and Physical Access",
             "Prior to issuing system credentials and granting system access, the entity registers and authorizes new internal and external users."),
            ("CC6.3", "Access removal on termination or role change", "Logical and Physical Access",
             "The entity authorizes, modifies, or removes access to data, software, functions, and other protected assets based on roles and responsibilities, and changes access in a timely manner upon termination or role change."),
            ("CC6.6", "Protection against external threats", "Logical and Physical Access",
             "The entity implements logical access security measures to protect against threats from sources outside its system boundaries."),
            ("CC6.7", "Restriction of data transmission and movement", "Logical and Physical Access",
             "The entity restricts the transmission, movement, and removal of information to authorized internal and external users and processes, and protects it during transmission, movement, or removal."),
            ("CC6.8", "Prevention and detection of unauthorized software", "Logical and Physical Access",
             "The entity implements controls to prevent or detect and act upon the introduction of unauthorized or malicious software."),
            ("CC7.1", "Detection of security events and vulnerabilities", "System Operations",
             "The entity uses detection and monitoring procedures to identify changes to configurations that introduce vulnerabilities and susceptibilities to security events."),
            ("CC7.2", "Monitoring of system components for anomalies", "System Operations",
             "The entity monitors system components and the operation of controls for anomalies indicative of malicious acts, natural disasters, or errors affecting security objectives."),
            ("CC7.3", "Evaluation of security incidents", "System Operations",
             "The entity evaluates security events to determine whether they could or have resulted in a failure to meet objectives, and if so, takes action to prevent or address such failures."),
            ("CC7.4", "Incident response and recovery procedures", "System Operations",
             "The entity responds to identified security incidents by executing a defined incident response program to understand, contain, remediate, and communicate about incidents."),
            ("CC8.1", "Change management process for infrastructure and software", "Change Management",
             "The entity authorizes, designs, develops, configures, documents, tests, approves, and implements changes to infrastructure, data, software, and procedures to meet objectives."),
            ("CC9.1", "Risk mitigation for business disruptions", "Risk Mitigation",
             "The entity identifies, selects, and develops risk mitigation activities for risks arising from potential business disruptions."),
            ("CC9.2", "Vendor and business partner risk management", "Risk Mitigation",
             "The entity assesses and manages risks associated with vendors and business partners."),
        ]

        for code, title, category, description in soc2_controls:
            db.session.add(Control(
                code=code, title=title, category=category, description=description,
                status='Not Assessed', framework_id=soc2.id
            ))

        db.session.commit()

        # ---- INTEGRATED PLATFORMS (VENDORS) ----
        vendors_data = [
            dict(name='AWS', category='Cloud Infrastructure',
                 status='Approved', contact_name='AWS Support', contact_email='security@aws.com',
                 last_assessment='2026-06-15', next_assessment='2026-12-15',
                 compliance=['SOC 2', 'ISO 27001', 'HIPAA']),
            dict(name='Google Workspace', category='Communication',
                 status='Approved', contact_name='Google Workspace Admin', contact_email='security@google.com',
                 last_assessment='2026-05-20', next_assessment='2026-11-20',
                 compliance=['SOC 2', 'ISO 27001']),
            dict(name='GitHub', category='Development',
                 status='Approved', contact_name='GitHub Support', contact_email='security@github.com',
                 last_assessment='2026-04-10', next_assessment='2026-10-10',
                 compliance=['SOC 2', 'ISO 27001']),
            dict(name='Slack', category='Communication',
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


def seed_demo_policies():
    """
    Add a handful of demo policies spanning every status and content-state
    Adds exactly one policy (Information Security Policy, linked to ISO 27001:2022)
    so the Policies module isn't empty, without cluttering the app with a large
    dummy dataset.

    Additive only (checks Policy.query.count() first) - safe to run against a
    database that already has real data, unlike seed_database() which wipes everything.

    Run: python -m app.seed policies
    """
    app = create_app()
    with app.app_context():
        if Policy.query.count() > 0:
            print(f"Policies table already has {Policy.query.count()} row(s) - skipping demo seed.")
            return

        admin = User.query.filter_by(email='harsha@migrc.com').first() or User.query.first()
        today = date.today()

        policy = Policy(
            name='Information Security Policy', version='1.0',
            owner=admin.name if admin else 'Compliance Team',
            status='Published', framework='ISO 27001:2022', department='Security',
            effort_estimate='High', recurrence='Annually', entities='Organization Wide',
            review_cycle_days=365,
            last_reviewed=(today - timedelta(days=345)).strftime('%Y-%m-%d'),
            next_review=(today + timedelta(days=20)).strftime('%Y-%m-%d'),
            requirement_text='Describes information security policy requirements and how they are enforced across the organization.',
            content='# Information Security Policy\n\nThis is placeholder policy content for demo purposes.\n\n## Purpose\n\nTo define information security policy for ISO 27001:2022.',
        )
        if admin:
            policy.assignees = [admin]
        db.session.add(policy)
        db.session.commit()
        print("Seeded 1 demo policy (Information Security Policy, ISO 27001:2022).")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'assets':
        seed_demo_assets()
    elif len(sys.argv) > 1 and sys.argv[1] == 'policies':
        seed_demo_policies()
    else:
        seed_database()
