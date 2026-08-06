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
    acknowledgements = db.Column(db.Integer, default=0)
    total_employees = db.Column(db.Integer, default=50)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
    evidence_collected = db.Column(db.Integer, default=0)
    evidence_total = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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


class TrainingModule(db.Model):
    __tablename__ = 'training_modules'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    duration = db.Column(db.String(30))
    assigned = db.Column(db.Integer, default=0)
    completed = db.Column(db.Integer, default=0)
    overdue = db.Column(db.Integer, default=0)
    status = db.Column(db.String(30), default='Active')
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AccessReview(db.Model):
    __tablename__ = 'access_reviews'
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50))
    systems = db.Column(db.JSON, default=list)
    last_review = db.Column(db.String(20))
    next_review = db.Column(db.String(20))
    status = db.Column(db.String(30), default='Active')
    risk = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
