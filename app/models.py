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
    audit_period_start = db.Column(db.Date)
    audit_period_end = db.Column(db.Date)
    status = db.Column(db.String(30), default='Pending Review')
    review_notes = db.Column(db.Text)
    reviewed_by = db.Column(db.String(100))
    reviewed_at = db.Column(db.DateTime)
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
    created = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    linked_control = db.relationship('Control', backref='risks')

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
        }


class Policy(db.Model):
    __tablename__ = 'policies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    version = db.Column(db.String(20), default='1.0')
    owner = db.Column(db.String(100))
    status = db.Column(db.String(30), default='Draft')
    framework = db.Column(db.String(50))
    last_reviewed = db.Column(db.String(20))
    next_review = db.Column(db.String(20))
    review_cycle_days = db.Column(db.Integer, default=180)
    file_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    acks = db.relationship('PolicyAcknowledgement', backref='policy', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def acknowledgements(self):
        return self.acks.count()

    @property
    def total_employees(self):
        return Employee.query.count()

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
        }


class PolicyAcknowledgement(db.Model):
    __tablename__ = 'policy_acknowledgements'
    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('policies.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    acknowledged_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship('Employee')


class Audit(db.Model):
    __tablename__ = 'audits'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    framework = db.Column(db.String(100))
    auditor = db.Column(db.String(100))
    status = db.Column(db.String(30), default='Scheduled')
    start_date = db.Column(db.String(20))
    end_date = db.Column(db.String(20))
    findings = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    evidence_items = db.relationship('AuditEvidence', backref='audit', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def evidence_total(self):
        return self.evidence_items.count()

    @property
    def evidence_collected(self):
        return self.evidence_items.filter_by(status='Collected').count()

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
    __tablename__ = 'audit_evidence'
    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(db.Integer, db.ForeignKey('audits.id'), nullable=False)
    control_id = db.Column(db.Integer, db.ForeignKey('controls.id'), nullable=False)
    status = db.Column(db.String(30), default='Missing')
    collected_at = db.Column(db.DateTime)

    control = db.relationship('Control')


class Vendor(db.Model):
    __tablename__ = 'vendors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    risk_tier = db.Column(db.String(20))
    risk_score = db.Column(db.Integer)
    status = db.Column(db.String(30), default='Under Review')
    contact_name = db.Column(db.String(100))
    contact_email = db.Column(db.String(120))
    last_assessment = db.Column(db.String(20))
    next_assessment = db.Column(db.String(20))
    compliance = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'risk_tier': self.risk_tier,
            'risk_score': self.risk_score,
            'status': self.status,
            'contact_name': self.contact_name,
            'contact_email': self.contact_email,
            'compliance': self.compliance or [],
        }


class Asset(db.Model):
    __tablename__ = 'assets'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50))
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


class TrainingCampaign(db.Model):
    __tablename__ = 'training_campaigns'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(30), default='Draft')
    launch_date = db.Column(db.String(20))
    end_date = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    enrollments = db.relationship('TrainingCampaignEnrollment', backref='campaign', lazy='dynamic', cascade='all, delete-orphan')

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
