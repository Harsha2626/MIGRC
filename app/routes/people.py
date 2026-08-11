from flask import Blueprint, render_template
from flask_login import login_required
from app.models import AccessReview, TrainingModule

people_bp = Blueprint('people', __name__)


@people_bp.route('/access-reviews')
@login_required
def access_reviews():
    reviews = AccessReview.query.all()
    return render_template('access_reviews.html', page='access_reviews', reviews=reviews)


@people_bp.route('/training')
@login_required
def training():
    modules = TrainingModule.query.all()
    return render_template('training.html', page='training', modules=modules)
