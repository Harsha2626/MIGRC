import os
from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager
from app.models import db, User

migrate = Migrate()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
                static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))

    app.config.from_object('config.Config')

    # Ensure upload folder exists
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.compliance import compliance_bp
    from app.routes.risks import risks_bp
    from app.routes.policies import policies_bp
    from app.routes.audits import audits_bp
    from app.routes.vendors import vendors_bp
    from app.routes.assets import assets_bp
    from app.routes.people import people_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(compliance_bp)
    app.register_blueprint(risks_bp)
    app.register_blueprint(policies_bp)
    app.register_blueprint(audits_bp)
    app.register_blueprint(vendors_bp)
    app.register_blueprint(assets_bp)
    app.register_blueprint(people_bp)

    return app
