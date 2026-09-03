from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(30), nullable=False, default='Viewer')
    is_active_user = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Role -> permission set.
    #   write            create/edit across compliance modules (risks, policies, vendors, assets,
    #                    people, evidence upload)
    #   delete           delete across all modules
    #   manage_users     create/invite users (Settings)
    #   audit_write      create/edit within the Audits module (Auditor's "manage audits")
    #   review_evidence  approve/reject evidence (Auditor's "review evidence")
    ROLE_PERMISSIONS = {
        'Admin':              {'write', 'delete', 'manage_users', 'audit_write', 'review_evidence'},
        'Compliance Manager': {'write', 'delete', 'audit_write', 'review_evidence'},
        'Auditor':            {'audit_write', 'review_evidence'},
        'Viewer':             set(),
    }

    def has_permission(self, perm):
        return perm in self.ROLE_PERMISSIONS.get(self.role, set())

    @property
    def can_write(self):
        return self.has_permission('write')

    @property
    def can_delete(self):
        return self.has_permission('delete')

    @property
    def can_manage_users(self):
        return self.has_permission('manage_users')

    @property
    def can_audit_write(self):
        return self.has_permission('audit_write')

    @property
    def can_review_evidence(self):
        return self.has_permission('review_evidence')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.is_active_user


class Framework(db.Model):
    __tablename__ = 'frameworks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    icon = db.Column(db.String(50), default='globe')
    status = db.Column(db.String(30), default='In Progress')
    owner = db.Column(db.String(100))
    target_date = db.Column(db.Date)
    controls_detail = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    controls = db.relationship('Control', backref='framework', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def total_controls(self):
        return self.controls.count()

    @property
    def passing(self):
        return self.controls.filter_by(status='Passing').count()

    @property
    def failing(self):
        return self.controls.filter_by(status='Failing').count()

    @property
    def not_applicable(self):
        return self.controls.filter_by(status='Not Applicable').count()

    @property
    def not_assessed(self):
        return self.controls.filter_by(status='Not Assessed').count()

    @property
    def compliance_score(self):
        """Passing / (Total - N/A) × 100"""
        applicable = self.total_controls - self.not_applicable
        if applicable == 0:
            return 0.0
        return round((self.passing / applicable) * 100, 1)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'icon': self.icon,
            'total_controls': self.total_controls,
            'controls_detail': self.controls_detail,
            'passing': self.passing,
            'failing': self.failing,
            'not_applicable': self.not_applicable,
            'not_assessed': self.not_assessed,
            'compliance_score': self.compliance_score,
            'status': self.status,
        }


class Control(db.Model):
    __tablename__ = 'controls'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    framework_id = db.Column(db.Integer, db.ForeignKey('frameworks.id'), nullable=False)
    status = db.Column(db.String(30), default='Not Assessed')
    owner = db.Column(db.String(100))
    test_criteria = db.Column(db.Text)
    evidence_requirement = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    evidence_mappings = db.relationship('EvidenceMapping', backref='control', lazy='dynamic', cascade='all, delete-orphan')


class Evidence(db.Model):
    __tablename__ = 'evidence'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500))
    file_name = db.Column(db.String(200))
    file_type = db.Column(db.String(50))
    file_size = db.Column(db.Integer)
    source_type = db.Column(db.String(50))
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=True)
    audit_period_start = db.Column(db.Date)
    audit_period_end = db.Column(db.Date)
    status = db.Column(db.String(30), default='Pending Review')
    review_notes = db.Column(db.Text)
    reviewed_by = db.Column(db.String(100))
    reviewed_at = db.Column(db.DateTime)
    ai_suggested_status = db.Column(db.String(30))
    ai_confidence = db.Column(db.Float)
    ai_rationale = db.Column(db.Text)
    ai_reviewed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    uploaded_by = db.relationship('User', backref='evidence_uploads')
    evidence_mappings = db.relationship('EvidenceMapping', backref='evidence', lazy='dynamic', cascade='all, delete-orphan')


class EvidenceMapping(db.Model):
    __tablename__ = 'evidence_mappings'
    id = db.Column(db.Integer, primary_key=True)
    evidence_id = db.Column(db.Integer, db.ForeignKey('evidence.id'), nullable=False)
    control_id = db.Column(db.Integer, db.ForeignKey('controls.id'), nullable=False)
    status = db.Column(db.String(30), default='Mapped')
    mapped_at = db.Column(db.DateTime, default=datetime.utcnow)
    validated_at = db.Column(db.DateTime)


risk_controls = db.Table(
    'risk_controls',
    db.Column('risk_id', db.Integer, db.ForeignKey('risks.id'), primary_key=True),
    db.Column('control_id', db.Integer, db.ForeignKey('controls.id'), primary_key=True),
)


class Risk(db.Model):
    __tablename__ = 'risks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    likelihood = db.Column(db.String(20))
    impact = db.Column(db.String(20))
    score = db.Column(db.Integer)
    owner = db.Column(db.String(100))
    status = db.Column(db.String(30), default='Open')
    treatment = db.Column(db.String(30))
    treatment_plan = db.Column(db.Text)
    linked_control_id = db.Column(db.Integer, db.ForeignKey('controls.id'), nullable=True)
    residual_likelihood = db.Column(db.String(20), nullable=True)
    residual_impact = db.Column(db.String(20), nullable=True)
    residual_score = db.Column(db.Integer, nullable=True)
    created = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    linked_control = db.relationship('Control', foreign_keys=[linked_control_id], backref='risks')
    mitigating_controls = db.relationship('Control', secondary=risk_controls, backref='mitigated_risks')
    treatments = db.relationship('RiskTreatment', backref='risk', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'category': self.category,
            'likelihood': self.likelihood,
            'impact': self.impact,
            'score': self.score,
            'owner': self.owner,
            'status': self.status,
            'treatment': self.treatment,
            'created': self.created,
            'residual_likelihood': self.residual_likelihood,
            'residual_impact': self.residual_impact,
            'residual_score': self.residual_score,
        }


class RiskTreatment(db.Model):
    __tablename__ = 'risk_treatments'
    id = db.Column(db.Integer, primary_key=True)
    risk_id = db.Column(db.Integer, db.ForeignKey('risks.id'), nullable=False)
    action = db.Column(db.Text, nullable=False)
    owner = db.Column(db.String(100))
    department = db.Column(db.String(100))
    deadline = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Planned')  # Planned, In Progress, Pending Approval, Needs Revision, Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    milestones = db.relationship('TreatmentMilestone', backref='treatment', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def milestone_progress(self):
        total = self.milestones.count()
        if not total:
            return 0
        return round((self.milestones.filter_by(completed=True).count() / total) * 100)


class TreatmentMilestone(db.Model):
    __tablename__ = 'treatment_milestones'
    id = db.Column(db.Integer, primary_key=True)
    treatment_id = db.Column(db.Integer, db.ForeignKey('risk_treatments.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.String(20))
    completed = db.Column(db.Boolean, default=False)


policy_assignees = db.Table(
    'policy_assignees',
    db.Column('policy_id', db.Integer, db.ForeignKey('policies.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
)

policy_approvers = db.Table(
    'policy_approvers',
    db.Column('policy_id', db.Integer, db.ForeignKey('policies.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
)

policy_controls = db.Table(
    'policy_controls',
    db.Column('policy_id', db.Integer, db.ForeignKey('policies.id'), primary_key=True),
    db.Column('control_id', db.Integer, db.ForeignKey('controls.id'), primary_key=True),
)


class Policy(db.Model):
    __tablename__ = 'policies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    version = db.Column(db.String(20), default='1.0')
    owner = db.Column(db.String(100))
    status = db.Column(db.String(30), default='Not Uploaded')
    framework = db.Column(db.String(50))
    last_reviewed = db.Column(db.String(20))
    next_review = db.Column(db.String(20))
    review_cycle_days = db.Column(db.Integer, default=180)
    file_path = db.Column(db.String(500))
    file_name = db.Column(db.String(200))
    external_url = db.Column(db.String(500))
    requirement_text = db.Column(db.Text)
    entities = db.Column(db.String(200), default='Organization Wide')
    effort_estimate = db.Column(db.String(10), default='Medium')
    recurrence = db.Column(db.String(20), default='Annually')
    department = db.Column(db.String(50))
    assigned_reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    acks = db.relationship('PolicyAcknowledgement', backref='policy', lazy='dynamic', cascade='all, delete-orphan')
    versions = db.relationship('PolicyVersion', backref='policy', lazy='dynamic', cascade='all, delete-orphan', order_by='PolicyVersion.created_at.desc()')
    reviews = db.relationship('PolicyReview', backref='policy', lazy='dynamic', cascade='all, delete-orphan', order_by='PolicyReview.reviewed_at.desc()')
    comments = db.relationship('PolicyComment', backref='policy', lazy='dynamic', cascade='all, delete-orphan', order_by='PolicyComment.created_at.desc()')
    approvals = db.relationship('PolicyApproval', backref='policy', lazy='dynamic', cascade='all, delete-orphan')
    assigned_reviewer = db.relationship('User', foreign_keys=[assigned_reviewer_id])
    assignees = db.relationship('User', secondary=policy_assignees, backref='assigned_policies')
    approvers = db.relationship('User', secondary=policy_approvers, backref='approver_policies')
    controls = db.relationship('Control', secondary=policy_controls, backref='policies')

    STATUS_FLOW = ['Not Uploaded', 'Draft', 'Needs Review', 'Pending Approval', 'Approved', 'Published', 'Retired']

    @property
    def acknowledgements(self):
        return self.acks.count()

    @property
    def total_employees(self):
        return Employee.query.count()

    @property
    def next_status(self):
        try:
            idx = self.STATUS_FLOW.index(self.status)
        except ValueError:
            return None
        return self.STATUS_FLOW[idx + 1] if idx + 1 < len(self.STATUS_FLOW) else None

    @property
    def content_state(self):
        if self.file_path:
            return 'file'
        if self.external_url:
            return 'external'
        if self.status == 'Not Uploaded':
            return 'blank'
        return 'content'

    @property
    def approval_progress(self):
        rows = self.approvals.all()
        if not rows:
            return (0, 0)
        return (len([r for r in rows if r.status == 'Approved']), len(rows))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'content': self.content,
            'version': self.version,
            'owner': self.owner,
            'status': self.status,
            'framework': self.framework,
            'review_cycle_days': self.review_cycle_days,
            'department': self.department,
            'effort_estimate': self.effort_estimate,
            'recurrence': self.recurrence,
            'entities': self.entities,
        }


class PolicyAcknowledgement(db.Model):
    __tablename__ = 'policy_acknowledgements'
    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('policies.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    acknowledged_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship('Employee')


class PolicyVersion(db.Model):
    __tablename__ = 'policy_versions'
    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('policies.id'), nullable=False)
    version = db.Column(db.String(20))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100))


class PolicyReview(db.Model):
    __tablename__ = 'policy_reviews'
    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('policies.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(20), default='Pending')  # Pending, Approved, Rejected
    comments = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviewer = db.relationship('User')


class PolicyComment(db.Model):
    __tablename__ = 'policy_comments'
    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('policies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')


class PolicyApproval(db.Model):
    __tablename__ = 'policy_approvals'
    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('policies.id'), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, Approved, Rejected
    comments = db.Column(db.Text)
    decided_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    approver = db.relationship('User')


class Audit(db.Model):
    __tablename__ = 'audits'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    framework = db.Column(db.String(100))
    auditor = db.Column(db.String(100))
    status = db.Column(db.String(30), default='Scheduled')
    start_date = db.Column(db.String(20))
    end_date = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    evidence_items = db.relationship('AuditEvidence', backref='audit', lazy='dynamic', cascade='all, delete-orphan')
    finding_items = db.relationship('AuditFinding', backref='audit', lazy='dynamic', cascade='all, delete-orphan')

    STATUS_FLOW = ['Scheduled', 'In Progress', 'Under Review', 'Completed']

    @property
    def evidence_total(self):
        return self.evidence_items.count()

    @property
    def evidence_collected(self):
        return self.evidence_items.filter_by(status='Collected').count()

    @property
    def findings(self):
        return self.finding_items.count()

    @property
    def open_findings(self):
        return self.finding_items.filter_by(status='Open').count()

    @property
    def next_status(self):
        try:
            idx = self.STATUS_FLOW.index(self.status)
        except ValueError:
            return None
        return self.STATUS_FLOW[idx + 1] if idx + 1 < len(self.STATUS_FLOW) else None

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'framework': self.framework,
            'auditor': self.auditor,
            'status': self.status,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'findings': self.findings,
            'evidence_collected': self.evidence_collected,
            'evidence_total': self.evidence_total,
        }


class AuditEvidence(db.Model):
    """One row per control in an audit's scope; doubles as the scope list and the evidence checklist."""
    __tablename__ = 'audit_evidence'
    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(db.Integer, db.ForeignKey('audits.id'), nullable=False)
    control_id = db.Column(db.Integer, db.ForeignKey('controls.id'), nullable=False)
    evidence_id = db.Column(db.Integer, db.ForeignKey('evidence.id'), nullable=True)
    status = db.Column(db.String(30), default='Missing')
    collected_at = db.Column(db.DateTime)

    control = db.relationship('Control')
    evidence = db.relationship('Evidence')


class AuditFinding(db.Model):
    __tablename__ = 'audit_findings'
    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(db.Integer, db.ForeignKey('audits.id'), nullable=False)
    control_id = db.Column(db.Integer, db.ForeignKey('controls.id'), nullable=True)
    type = db.Column(db.String(30), default='Observation')  # Observation, Non-Conformity, Recommendation
    severity = db.Column(db.String(20), default='Medium')   # Low, Medium, High, Critical
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='Open')       # Open, Remediated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    control = db.relationship('Control')
    remediation = db.relationship('Remediation', backref='finding', uselist=False, cascade='all, delete-orphan')


class Remediation(db.Model):
    __tablename__ = 'remediations'
    id = db.Column(db.Integer, primary_key=True)
    finding_id = db.Column(db.Integer, db.ForeignKey('audit_findings.id'), nullable=False, unique=True)
    owner = db.Column(db.String(100))
    deadline = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Planned')  # Planned, In Progress, Completed
    notes = db.Column(db.Text)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


VENDOR_REASSESSMENT_DAYS = 180


class Vendor(db.Model):
    __tablename__ = 'vendors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    status = db.Column(db.String(30), default='Under Review')
    website = db.Column(db.String(300))
    contact_name = db.Column(db.String(100))
    contact_email = db.Column(db.String(120))
    last_assessment = db.Column(db.String(20))
    next_assessment = db.Column(db.String(20))
    compliance = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assessments = db.relationship('VendorAssessment', backref='vendor', lazy='dynamic', cascade='all, delete-orphan')
    documents = db.relationship('Evidence', backref='vendor', lazy='dynamic', foreign_keys='Evidence.vendor_id')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'status': self.status,
            'website': self.website,
            'contact_name': self.contact_name,
            'contact_email': self.contact_email,
            'compliance': self.compliance or [],
        }


class QuestionnaireTemplate(db.Model):
    __tablename__ = 'questionnaire_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship('QuestionnaireQuestion', backref='template', lazy='dynamic', cascade='all, delete-orphan', order_by='QuestionnaireQuestion.order')


class QuestionnaireQuestion(db.Model):
    __tablename__ = 'questionnaire_questions'
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('questionnaire_templates.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, default=0)


class VendorAssessment(db.Model):
    __tablename__ = 'vendor_assessments'
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('questionnaire_templates.id'), nullable=False)
    status = db.Column(db.String(20), default='Sent')  # Sent, In Progress, Completed
    verdict = db.Column(db.String(20), nullable=True)  # Pass, Fail, Needs Follow-up
    reviewer_notes = db.Column(db.Text)
    sent_date = db.Column(db.String(20))
    completed_date = db.Column(db.String(20))

    template = db.relationship('QuestionnaireTemplate')
    responses = db.relationship('VendorAssessmentResponse', backref='assessment', lazy='dynamic', cascade='all, delete-orphan')


class VendorAssessmentResponse(db.Model):
    __tablename__ = 'vendor_assessment_responses'
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('vendor_assessments.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questionnaire_questions.id'), nullable=False)
    answer_text = db.Column(db.Text)

    question = db.relationship('QuestionnaireQuestion')


class Asset(db.Model):
    __tablename__ = 'assets'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50))
    resource_id = db.Column(db.String(300))
    region = db.Column(db.String(50))
    risk_associated = db.Column(db.String(50))
    environment = db.Column(db.String(50))
    owner = db.Column(db.String(100))
    classification = db.Column(db.String(30))
    status = db.Column(db.String(30), default='Active')
    cloud_provider = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'resource_id': self.resource_id,
            'region': self.region,
            'risk_associated': self.risk_associated,
            'environment': self.environment,
            'owner': self.owner,
            'classification': self.classification,
            'status': self.status,
            'cloud_provider': self.cloud_provider,
        }


class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    department = db.Column(db.String(50))
    source = db.Column(db.String(50), default='Manual')
    status = db.Column(db.String(30), default='Active')
    monitoring_agent_installed = db.Column(db.Boolean, default=False)
    device_security_compliant = db.Column(db.Boolean, default=False)
    policy_acknowledged = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    offboarded_at = db.Column(db.DateTime)

    enrollments = db.relationship('TrainingCampaignEnrollment', backref='employee', lazy='dynamic', cascade='all, delete-orphan')
    access_grants = db.relationship('EmployeeAccess', backref='employee', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def has_pending_tasks(self):
        if not self.policy_acknowledged:
            return True
        return self.enrollments.filter_by(completed=False).count() > 0

    @property
    def campaign_names(self):
        return [e.campaign.name for e in self.enrollments]

    @property
    def campaign_ids(self):
        return [e.campaign_id for e in self.enrollments]

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'department': self.department,
            'source': self.source,
            'status': self.status,
            'monitoring_agent_installed': self.monitoring_agent_installed,
            'device_security_compliant': self.device_security_compliant,
            'policy_acknowledged': self.policy_acknowledged,
            'campaign_names': self.campaign_names,
        }


campaign_materials = db.Table(
    'campaign_materials',
    db.Column('campaign_id', db.Integer, db.ForeignKey('training_campaigns.id'), primary_key=True),
    db.Column('material_id', db.Integer, db.ForeignKey('training_materials.id'), primary_key=True),
)


class TrainingMaterial(db.Model):
    __tablename__ = 'training_materials'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20), default='Document')  # Document, Link, Video
    file_path = db.Column(db.String(500))
    file_name = db.Column(db.String(200))
    url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ICON_BY_TYPE = {'Document': 'fa-file-pdf', 'Link': 'fa-link', 'Video': 'fa-circle-play'}

    @property
    def icon(self):
        return self.ICON_BY_TYPE.get(self.type, 'fa-file')


class TrainingCampaign(db.Model):
    __tablename__ = 'training_campaigns'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500))
    status = db.Column(db.String(30), default='Draft')
    launch_date = db.Column(db.String(20))
    end_date = db.Column(db.String(20))
    timezone = db.Column(db.String(50), default='(GMT+05:30) Asia/Calcutta')
    no_end_date = db.Column(db.Boolean, default=False)
    sla_days = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    enrollments = db.relationship('TrainingCampaignEnrollment', backref='campaign', lazy='dynamic', cascade='all, delete-orphan')
    materials = db.relationship('TrainingMaterial', secondary=campaign_materials, backref='campaigns')

    @property
    def total_enrolled(self):
        return self.enrollments.count()

    @property
    def completed_count(self):
        return self.enrollments.filter_by(completed=True).count()

    @property
    def completion_rate(self):
        total = self.total_enrolled
        return round((self.completed_count / total) * 100) if total else 0


class TrainingCampaignEnrollment(db.Model):
    __tablename__ = 'training_campaign_enrollments'
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('training_campaigns.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)


class EmployeeAccess(db.Model):
    __tablename__ = 'employee_access'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    access_level = db.Column(db.String(30), default='Standard')
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)

    vendor = db.relationship('Vendor', backref='employee_access')


access_review_applications = db.Table(
    'access_review_applications',
    db.Column('access_review_id', db.Integer, db.ForeignKey('access_reviews.id'), primary_key=True),
    db.Column('vendor_id', db.Integer, db.ForeignKey('vendors.id'), primary_key=True),
)


class AccessReview(db.Model):
    __tablename__ = 'access_reviews'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    owner = db.Column(db.String(100))
    status = db.Column(db.String(30), default='Created')
    review_period_start = db.Column(db.String(20))
    review_period_end = db.Column(db.String(20))
    recurrence = db.Column(db.String(20), default='Once')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    applications = db.relationship('Vendor', secondary=access_review_applications, backref='access_reviews')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'owner': self.owner,
            'status': self.status,
            'review_period_start': self.review_period_start,
            'review_period_end': self.review_period_end,
            'recurrence': self.recurrence,
            'applications': [v.name for v in self.applications],
        }


class ComplianceSnapshot(db.Model):
    __tablename__ = 'compliance_snapshots'
    id = db.Column(db.Integer, primary_key=True)
    framework_id = db.Column(db.Integer, db.ForeignKey('frameworks.id'), nullable=False)
    score = db.Column(db.Float, default=0.0)
    passing = db.Column(db.Integer, default=0)
    failing = db.Column(db.Integer, default=0)
    not_assessed = db.Column(db.Integer, default=0)
    not_applicable = db.Column(db.Integer, default=0)
    total_controls = db.Column(db.Integer, default=0)
    snapshot_date = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    framework = db.relationship('Framework', backref='snapshots')


class DashboardSnapshot(db.Model):
    __tablename__ = 'dashboard_snapshots'
    id = db.Column(db.Integer, primary_key=True)
    snapshot_date = db.Column(db.Date, default=date.today, unique=True)
    open_risks = db.Column(db.Integer, default=0)
    active_policies = db.Column(db.Integer, default=0)
    pending_evidence = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ActivityLog(db.Model):
    __tablename__ = 'activity_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(30), nullable=False)
    entity_type = db.Column(db.String(30), nullable=False)
    entity_name = db.Column(db.String(200))
    description = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')


class NDAAcceptance(db.Model):
    """A Trust Center visitor's NDA acceptance — unlocks gated document downloads for their session."""
    __tablename__ = 'nda_acceptances'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    name = db.Column(db.String(100))
    company = db.Column(db.String(150))
    ip_address = db.Column(db.String(45))
    accepted_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(30), nullable=False)
    # deadline_approaching, evidence_rejected, risk_escalated, policy_review_due, finding_assigned
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.String(400))
    link = db.Column(db.String(300))
    is_read = db.Column(db.Boolean, default=False)
    dedupe_key = db.Column(db.String(200), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')
