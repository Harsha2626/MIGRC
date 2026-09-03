import os
from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_wtf import CSRFProtect
from flask_mail import Mail
from app.models import db, User
from app.utils import timesince

migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()


def create_app():
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
                static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))

    app.config.from_object('config.Config')
    app.jinja_env.filters['timesince'] = timesince

    # Ensure upload folder exists
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_notifications():
        if not current_user.is_authenticated:
            return {}
        from app.models import Notification
        unread = Notification.query.filter_by(user_id=current_user.id, is_read=False)
        return {
            'unread_notification_count': unread.count(),
            'recent_notifications': unread.order_by(Notification.created_at.desc()).limit(8).all(),
        }

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.compliance import compliance_bp
    from app.routes.risks import risks_bp
    from app.routes.policies import policies_bp
    from app.routes.audits import audits_bp
    from app.routes.vendors import vendors_bp
    from app.routes.assets import assets_bp
    from app.routes.people import people_bp
    from app.routes.notifications import notifications_bp
    from app.routes.reports import reports_bp
    from app.routes.integrations import integrations_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(compliance_bp)
    app.register_blueprint(risks_bp)
    app.register_blueprint(policies_bp)
    app.register_blueprint(audits_bp)
    app.register_blueprint(vendors_bp)
    app.register_blueprint(assets_bp)
    app.register_blueprint(people_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(integrations_bp)

    return app
