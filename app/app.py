from flask import Flask, render_template, redirect, url_for, flash, request, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import requests
import json
import pandas as pd
import statsmodels.api as sm
from io import BytesIO
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import re
import sys
import traceback
from apscheduler.schedulers.background import BackgroundScheduler
from models.models import EconometricModels
from models.report_generator import create_econometric_report
import tempfile
import chardet
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import psutil

# ==================== FONCTIONS DE LECTURE DE FICHIERS ====================

def detect_separator(file_path):
    """DÃ©tecter automatiquement le sÃ©parateur d'un fichier CSV"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline()
    except:
        with open(file_path, 'r', encoding='latin-1', errors='ignore') as f:
            first_line = f.readline()
    
    # SÃ©parateurs possibles
    separators = [',', ';', '\t', '|', ' ']
    best_sep = ','
    max_count = 0
    
    for sep in separators:
        count = first_line.count(sep)
        if count > max_count:
            max_count = count
            best_sep = sep
    
    return best_sep

def detect_encoding(file_path):
    """DÃ©tecter l'encodage d'un fichier"""
    try:
        import chardet
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)
            result = chardet.detect(raw_data)
            return result['encoding'] or 'utf-8'
    except:
        return 'utf-8'

def read_data_file(file_path):
    """Lire un fichier de donnÃ©es avec dÃ©tection automatique du sÃ©parateur et de l'encodage"""
    if file_path.endswith('.csv'):
        try:
            # DÃ©tecter l'encodage
            encoding = detect_encoding(file_path)
            # DÃ©tecter le sÃ©parateur
            sep = detect_separator(file_path)
            
            # PremiÃ¨re tentative de lecture
            df = pd.read_csv(file_path, sep=sep, encoding=encoding)
            
            # VÃ©rifier si toutes les donnÃ©es sont dans une seule colonne
            if len(df.columns) == 1:
                # Essayer avec un autre sÃ©parateur
                for alt_sep in [';', ',', '\t', '|']:
                    if alt_sep != sep:
                        try:
                            df_test = pd.read_csv(file_path, sep=alt_sep, encoding=encoding)
                            if len(df_test.columns) > 1:
                                df = df_test
                                break
                        except:
                            continue
            
            # Nettoyer les noms de colonnes (supprimer les espaces)
            df.columns = df.columns.str.strip()
            
            return df
            
        except Exception as e:
            print(f"âš ï¸ Erreur lecture CSV: {e}", flush=True)
            # Dernier essai avec sÃ©parateur automatique
            try:
                return pd.read_csv(file_path, sep=None, engine='python', encoding='utf-8')
            except:
                return pd.read_csv(file_path, sep=';', encoding='utf-8')
    
    elif file_path.endswith(('.xlsx', '.xls')):
        return pd.read_excel(file_path)
    
    elif file_path.endswith('.dta'):
        return pd.read_stata(file_path)
    
    else:
        raise ValueError(f"Format de fichier non supportÃ©: {file_path}")

# ==================== CONFIGURATION ====================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://dataecon:dataecon123@db:5432/dataecon')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = '/app/data'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max
app.config['SERVER_NAME'] = os.environ.get('SERVER_NAME')  # None en production, pas de restriction de domaine
# ==================== FILTRE MARKDOWN ====================
import mistune
from markupsafe import Markup
from mistune import create_markdown

@app.template_filter('markdown')
def markdown_filter(text):
    """Convertir le markdown en HTML"""
    if not text:
        return ''
    markdown = create_markdown()
    return Markup(markdown(text))

# ==================== CONFIGURATION EMAIL ====================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'dataeconci@gmail.com'
app.config['MAIL_PASSWORD'] = 'mptl yrfx pnvh fsqj'
app.config['MAIL_DEFAULT_SENDER'] = 'dataeconci@gmail.com'

# SÃ©rializer pour les tokens
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'dta'}
# ==================== CONFIGURATION CLOUDFLARE R2 ====================
R2_ENDPOINT = os.environ.get('R2_ENDPOINT')
R2_ACCESS_KEY = os.environ.get('R2_ACCESS_KEY')
R2_SECRET_KEY = os.environ.get('R2_SECRET_KEY')
R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME', 'dataecon-pdfs')

def get_r2_client():
    """CrÃ©er un client S3 compatible Cloudflare R2"""
    if not R2_ENDPOINT or not R2_ACCESS_KEY or not R2_SECRET_KEY:
        return None
    
    return boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        config=Config(signature_version='s3v4')
    )

def get_pdf_url(file_name):
    """GÃ©nÃ©rer une URL prÃ©signÃ©e pour un PDF depuis R2"""
    client = get_r2_client()
    if not client:
        return None
    
    try:
        url = client.generate_presigned_url(
            'get_object',
            Params={'Bucket': R2_BUCKET_NAME, 'Key': file_name},
            ExpiresIn=3600
        )
        return url
    except Exception as e:
        print(f"âŒ Erreur R2: {e}", flush=True)
        return None

# ==================== CONFIGURATION WAVE PAYMENT ====================
WAVE_API_URL = "https://pay.wave.com/api/v1"
WAVE_RETURN_URL = "http://localhost:5000/payment_callback"
WAVE_CANCEL_URL = "http://localhost:5000/payment_cancel"

SUBSCRIPTION_PLANS = {
    'free': {
        'name': 'Gratuit',
        'price': 0,
        'currency': 'XOF',
        'features': ['Cours DÃ©butant']
    },
    'premium': {
        'name': 'Premium',
        'price': 2000,
        'currency': 'XOF',
        'features': ['Cours DÃ©butant', 'Cours IntermÃ©diaire', 'Cours AvancÃ©'],
        'wave_link': 'https://pay.wave.com/m/M_ci_BBSbYjlQgoxi/c/ci'
    },
    'premium_pro': {
        'name': 'Premium Pro',
        'price': 5000,
        'currency': 'XOF',
        'features': ['Cours DÃ©butant', 'Cours IntermÃ©diaire', 'Cours AvancÃ©', 'DonnÃ©es', 'ModÃ¨les'],
        'wave_link': 'https://pay.wave.com/m/M_ci_BBSbYjlQgoxi/c/ci'
    }
}

# ==================== INITIALISATION ====================
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accÃ©der Ã  cette page.'
mail = Mail(app)

# ==================== MODÃˆLES ====================
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    email_confirmed = db.Column(db.Boolean, default=False)
    email_confirmed_at = db.Column(db.DateTime)
    last_password_reset = db.Column(db.DateTime)
    
    subscription_level = db.Column(db.String(20), default='free')
    subscription_expires_at = db.Column(db.DateTime)
    wave_payment_id = db.Column(db.String(100))
    is_subscription_active = db.Column(db.Boolean, default=False)
    reminder_sent = db.Column(db.Boolean, default=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_access(self, course_level):
        if self.is_admin:
            return True
        if course_level == 'DÃ©butant':
            return True
        if self.subscription_level in ['premium', 'premium_pro']:
            return True
        return False
    
    def can_download_pdf(self):
        if self.is_admin:
            return True
        if self.subscription_level in ['premium', 'premium_pro']:
            return True
        return False
    
    def can_download_data(self):
        if self.is_admin:
            return True
        if self.subscription_level == 'premium_pro':
            return True
        return False
    
    def can_upload_course(self):
        return self.is_admin
    
    def can_upload_data(self):
        return self.is_admin
    
    def can_access_data(self):
        if self.is_admin:
            return True
        return self.subscription_level == 'premium_pro'
    
    def can_access_models(self):
        if self.is_admin:
            return True
        return self.subscription_level == 'premium_pro'
    
    def get_subscription_name(self):
        return SUBSCRIPTION_PLANS.get(self.subscription_level, {}).get('name', 'Gratuit')

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    level = db.Column(db.String(50))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.String(200))
    file_name = db.Column(db.String(100))

class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(200))
    file_name = db.Column(db.String(100))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    completed = db.Column(db.Boolean, default=False)
    progress_percent = db.Column(db.Integer, default=0)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== FONCTIONS ====================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_email(to, subject, template, **kwargs):
    print(f"ðŸ“§ TENTATIVE D'ENVOI EMAIL: {to}", flush=True)
    print(f"ðŸ“§ Sujet: {subject}", flush=True)
    
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            html=render_template(template, **kwargs),
            sender=app.config['MAIL_DEFAULT_SENDER']
        )
        print(f"ðŸ“§ Message crÃ©Ã©, envoi en cours...", flush=True)
        mail.send(msg)
        print(f"âœ… EMAIL ENVOYÃ‰ AVEC SUCCÃˆS Ã  {to}", flush=True)
        return True
    except Exception as e:
        print(f"âŒ ERREUR ENVOI EMAIL: {str(e)}", flush=True)
        traceback.print_exc()
        return False

def send_confirmation_email(user):
    try:
        token = serializer.dumps(user.email, salt='email-confirm')
        confirm_url = url_for('confirm_email', token=token, _external=True)
        print(f"ðŸ”— URL de confirmation: {confirm_url}", flush=True)
        
        return send_email(
            to=user.email,
            subject='Confirmez votre email - DataEcon.Ci',
            template='emails/confirm_email.html',
            user=user,
            confirm_url=confirm_url
        )
    except Exception as e:
        print(f"âŒ Erreur dans send_confirmation_email: {str(e)}", flush=True)
        traceback.print_exc()
        return False

def send_reset_email(user):
    try:
        token = serializer.dumps(user.email, salt='password-reset')
        reset_url = url_for('reset_password', token=token, _external=True)
        print(f"ðŸ”— URL de rÃ©initialisation: {reset_url}", flush=True)
        
        return send_email(
            to=user.email,
            subject='RÃ©initialisation du mot de passe - DataEcon.Ci',
            template='emails/reset_password.html',
            user=user,
            reset_url=reset_url
        )
    except Exception as e:
        print(f"âŒ Erreur dans send_reset_email: {str(e)}", flush=True)
        traceback.print_exc()
        return False

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ==================== TÃ‚CHES AUTOMATISÃ‰ES ====================
def check_subscription_reminders():
    """Envoyer un rappel 3 jours avant l'expiration"""
    with app.app_context():
        print("ðŸ”” VÃ©rification des rappels d'abonnement...", flush=True)
        seuil = datetime.utcnow() + timedelta(days=3)
        users_to_remind = User.query.filter(
            User.subscription_level.in_(['premium', 'premium_pro']),
            User.is_subscription_active == True,
            User.subscription_expires_at <= seuil,
            User.subscription_expires_at > datetime.utcnow(),
            User.reminder_sent == False
        ).all()

        for user in users_to_remind:
            try:
                jours_restants = (user.subscription_expires_at - datetime.utcnow()).days
                msg = Message(
                    subject="Votre abonnement DataEcon.Ci expire bientÃ´t",
                    recipients=[user.email],
                    html=render_template(
                        'emails/subscription_reminder.html',
                        user=user,
                        jours_restants=jours_restants,
                        expire_date=user.subscription_expires_at.strftime('%d/%m/%Y'),
                        subscription_url=url_for('subscription', _external=True)
                    ),
                    sender=app.config['MAIL_DEFAULT_SENDER']
                )
                mail.send(msg)
                user.reminder_sent = True
                db.session.commit()
                print(f"âœ… Rappel envoyÃ© Ã  {user.email}", flush=True)
            except Exception as e:
                print(f"âŒ Erreur envoi rappel Ã  {user.email}: {e}", flush=True)

def downgrade_expired_subscriptions():
    """Repasser en Gratuit les abonnements expirÃ©s"""
    with app.app_context():
        print("â³ VÃ©rification des abonnements expirÃ©s...", flush=True)
        expired_users = User.query.filter(
            User.subscription_level.in_(['premium', 'premium_pro']),
            User.is_subscription_active == True,
            User.subscription_expires_at <= datetime.utcnow()
        ).all()

        for user in expired_users:
            user.subscription_level = 'free'
            user.is_subscription_active = False
            user.subscription_expires_at = None
            user.reminder_sent = False
            db.session.commit()
            print(f"â¬‡ï¸ {user.username} repassÃ© en Gratuit (abonnement expirÃ©)", flush=True)

            try:
                msg = Message(
                    subject="Votre abonnement DataEcon.Ci a expirÃ©",
                    recipients=[user.email],
                    html=render_template(
                        'emails/subscription_expired.html',
                        user=user,
                        subscription_url=url_for('subscription', _external=True)
                    ),
                    sender=app.config['MAIL_DEFAULT_SENDER']
                )
                mail.send(msg)
            except Exception as e:
                print(f"âŒ Erreur envoi email expiration Ã  {user.email}: {e}", flush=True)

# ==================== ROUTES ====================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')

        print(f"ðŸ“ NOUVEL UTILISATEUR: {username} - {email}", flush=True)

        if not is_valid_email(email):
            flash('Veuillez entrer un email valide.', 'danger')
            return render_template('register.html')

        user_exists = User.query.filter_by(username=username).first()
        email_exists = User.query.filter_by(email=email).first()

        if user_exists:
            flash('Ce nom d\'utilisateur est dÃ©jÃ  pris.', 'danger')
            return render_template('register.html')

        if email_exists:
            flash('Cet email est dÃ©jÃ  utilisÃ©.', 'danger')
            return render_template('register.html')

        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            email_confirmed=False,
            subscription_level='free',
            is_subscription_active=False
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"âœ… Utilisateur {username} crÃ©Ã© en base de donnÃ©es", flush=True)

        email_sent = send_confirmation_email(user)
        if email_sent:
            flash('Inscription rÃ©ussie ! Un email de confirmation vous a Ã©tÃ© envoyÃ©.', 'success')
        else:
            flash('Inscription rÃ©ussie ! Mais l\'email de confirmation n\'a pas pu Ãªtre envoyÃ©.', 'warning')

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=86400)
    except SignatureExpired:
        flash('Le lien de confirmation a expirÃ©. Veuillez vous rÃ©inscrire.', 'danger')
        return redirect(url_for('register'))
    except BadSignature:
        flash('Lien de confirmation invalide.', 'danger')
        return redirect(url_for('register'))

    user = User.query.filter_by(email=email).first()
    if user:
        if user.email_confirmed:
            flash('Votre email est dÃ©jÃ  confirmÃ©. Vous pouvez vous connecter.', 'info')
        else:
            user.email_confirmed = True
            user.email_confirmed_at = datetime.utcnow()
            db.session.commit()
            flash('Votre email a Ã©tÃ© confirmÃ© avec succÃ¨s ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('login'))
    else:
        flash('Utilisateur non trouvÃ©.', 'danger')
        return redirect(url_for('register'))

@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()

        if user:
            if send_reset_email(user):
                flash('Un email de rÃ©initialisation a Ã©tÃ© envoyÃ© Ã  votre adresse.', 'success')
            else:
                flash('Erreur lors de l\'envoi de l\'email. Veuillez rÃ©essayer.', 'danger')
        else:
            flash('Si votre email est enregistrÃ©, vous recevrez un lien de rÃ©initialisation.', 'info')

        return redirect(url_for('login'))

    return render_template('reset_password_request.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset', max_age=3600)
    except SignatureExpired:
        flash('Le lien de rÃ©initialisation a expirÃ©. Veuillez refaire une demande.', 'danger')
        return redirect(url_for('reset_password_request'))
    except BadSignature:
        flash('Lien de rÃ©initialisation invalide.', 'danger')
        return redirect(url_for('reset_password_request'))

    if request.method == 'POST':
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')

        if password != password_confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return render_template('reset_password.html')

        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(password)
            user.last_password_reset = datetime.utcnow()
            db.session.commit()
            flash('Votre mot de passe a Ã©tÃ© rÃ©initialisÃ© avec succÃ¨s !', 'success')
            return redirect(url_for('login'))
        else:
            flash('Utilisateur non trouvÃ©.', 'danger')
            return redirect(url_for('login'))

    return render_template('reset_password.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.email_confirmed:
                flash('Veuillez confirmer votre email avant de vous connecter.', 'warning')
                return render_template('login.html')
            login_user(user)
            flash(f'Bienvenue {user.first_name} !', 'success')
            return redirect(url_for('dashboard'))

        flash('Identifiants incorrects.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous Ãªtes dÃ©connectÃ©.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    courses = Course.query.all()
    datasets = Dataset.query.all()
    progress = Progress.query.filter_by(user_id=current_user.id).all()

    completed_count = sum(1 for p in progress if p.completed)
    total_courses = len(courses)

    return render_template('dashboard.html',
                         courses=courses,
                         datasets=datasets,
                         progress=progress,
                         completed_count=completed_count,
                         total_courses=total_courses)

@app.route('/courses')
@login_required
def courses():
    all_courses = Course.query.all()
    accessible_courses = []
    for course in all_courses:
        if current_user.has_access(course.level):
            accessible_courses.append(course)
    return render_template('courses.html', courses=accessible_courses)

@app.route('/course/<int:course_id>')
@login_required
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    
    if not current_user.has_access(course.level):
        flash('Vous devez avoir un abonnement Premium pour accÃ©der Ã  ce cours.', 'warning')
        return redirect(url_for('subscription'))
    
    progress = Progress.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if not progress:
        progress = Progress(user_id=current_user.id, course_id=course_id)
        db.session.add(progress)
    
    progress.last_accessed = datetime.utcnow()
    db.session.commit()
    
    return render_template('course_detail.html', 
                         course=course, 
                         progress=[progress],
                         can_download_pdf=current_user.can_download_pdf())

@app.route('/datasets')
@login_required
def datasets():
    if not current_user.can_access_data():
        flash('Vous devez avoir un abonnement Premium Pro pour accÃ©der aux donnÃ©es.', 'warning')
        return redirect(url_for('subscription'))
    
    datasets = Dataset.query.all()
    return render_template('datasets.html', datasets=datasets)

@app.route('/upload_dataset', methods=['POST'])
@login_required
def upload_dataset():
    if not current_user.can_upload_data():
        flash('Seul l\'administrateur peut ajouter des donnÃ©es.', 'danger')
        return redirect(url_for('datasets'))
    
    if 'file' not in request.files:
        flash('Aucun fichier sÃ©lectionnÃ©.', 'danger')
        return redirect(url_for('datasets'))

    file = request.files['file']
    name = request.form.get('name')
    description = request.form.get('description')

    if file.filename == '':
        flash('Aucun fichier sÃ©lectionnÃ©.', 'danger')
        return redirect(url_for('datasets'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        file.save(file_path)
        
        # VÃ‰RIFIER ET RÃ‰PARER LE FICHIER AVEC LE BON SÃ‰PARATEUR
        try:
            # Tester la lecture
            df = read_data_file(file_path)
            print(f"âœ… Fichier importÃ©: {filename}")
            print(f"ðŸ“Š Colonnes dÃ©tectÃ©es: {list(df.columns)}")
            print(f"ðŸ“Š Nombre de lignes: {len(df)}")
            
            # Si tout est bon, sauvegarder avec le sÃ©parateur standard (,) pour la compatibilitÃ©
            if len(df.columns) > 1:
                # Sauvegarder avec le sÃ©parateur standard
                df.to_csv(file_path, sep=',', index=False, encoding='utf-8')
                print("âœ… Fichier normalisÃ© avec sÃ©parateur ,")
            
        except Exception as e:
            flash(f'âš ï¸ Erreur lors de la lecture du fichier: {str(e)}', 'danger')
            os.remove(file_path)
            return redirect(url_for('datasets'))

        dataset = Dataset(
            name=name or filename,
            description=description,
            file_path=file_path,
            file_name=filename,
            uploaded_by=current_user.id
        )
        db.session.add(dataset)
        db.session.commit()

        flash('Fichier de donnÃ©es uploadÃ© avec succÃ¨s !', 'success')
    else:
        flash('Format de fichier non supportÃ©. Utilisez CSV, Excel ou Stata.', 'danger')

    return redirect(url_for('datasets'))

@app.route('/view_dataset/<int:dataset_id>')
@login_required
def view_dataset(dataset_id):
    if not current_user.can_access_data():
        flash('Vous devez avoir un abonnement Premium Pro pour accÃ©der aux donnÃ©es.', 'warning')
        return redirect(url_for('subscription'))
    
    dataset = Dataset.query.get_or_404(dataset_id)

    try:
        # Utiliser la fonction de lecture automatique
        df = read_data_file(dataset.file_path)

        table_html = df.head(20).to_html(classes='table table-striped')
        columns = list(df.columns)
        shape = df.shape
        stats = df.describe().to_html(classes='table table-striped')

        plt.figure(figsize=(12, 6))
        df_numeric = df.select_dtypes(include=['float64', 'int64'])
        if len(df_numeric.columns) >= 2:
            sns.heatmap(df_numeric.corr(), annot=True, cmap='coolwarm', center=0)
            plt.title('Matrice de corrÃ©lation')
            plot_path = '/tmp/plot.png'
            plt.savefig(plot_path, bbox_inches='tight')
            plt.close()

            with open(plot_path, 'rb') as f:
                plot_data = base64.b64encode(f.read()).decode('utf-8')
            plot_url = f'data:image/png;base64,{plot_data}'
        else:
            plot_url = None

        return render_template('view_dataset.html',
                             dataset=dataset,
                             table=table_html,
                             columns=columns,
                             rows=shape[0],
                             cols=shape[1],
                             stats=stats,
                             plot_url=plot_url)

    except Exception as e:
        flash(f'Erreur lors de la lecture du fichier: {str(e)}', 'danger')
        return redirect(url_for('datasets'))

@app.route('/analytics')
@login_required
def analytics():
    if not current_user.can_access_data():
        flash('Vous devez avoir un abonnement Premium Pro pour accÃ©der aux analyses.', 'warning')
        return redirect(url_for('subscription'))
    
    datasets = Dataset.query.all()
    dataset_stats = []

    for ds in datasets:
        try:
            df = read_data_file(ds.file_path)
            dataset_stats.append({
                'name': ds.name,
                'rows': len(df),
                'columns': len(df.columns),
                'numeric_cols': len(df.select_dtypes(include=['float64', 'int64']).columns)
            })
        except:
            pass

    return render_template('analytics.html', dataset_stats=dataset_stats)

@app.route('/econometric_model', methods=['GET', 'POST'])
@login_required
def econometric_model():
    if not current_user.can_access_models():
        flash('Vous devez avoir un abonnement Premium Pro pour utiliser les modÃ¨les.', 'warning')
        return redirect(url_for('subscription'))
    
    result_html = None
    model_info = None

    if request.method == 'POST':
        dataset_id = request.form.get('dataset_id')
        dependent = request.form.get('dependent')
        independent = request.form.get('independent')

        dataset = Dataset.query.get(int(dataset_id))
        if dataset:
            try:
                df = read_data_file(dataset.file_path)

                indep_vars = [v.strip() for v in independent.split(',')]
                X = df[indep_vars]
                X = sm.add_constant(X)
                y = df[dependent]

                model = sm.OLS(y, X).fit()

                model_info = {
                    'dependent': dependent,
                    'independent': indep_vars,
                    'r_squared': round(model.rsquared, 4),
                    'adj_r_squared': round(model.rsquared_adj, 4),
                    'f_stat': round(model.fvalue, 2),
                    'f_pvalue': round(model.f_pvalue, 4),
                    'nobs': int(model.nobs)
                }

                coef_html = model.summary().tables[1].as_html()
                result_html = coef_html

            except Exception as e:
                flash(f'Erreur: {str(e)}', 'danger')

    datasets = Dataset.query.all()
    return render_template('econometric_model.html',
                         datasets=datasets,
                         result_html=result_html,
                         model_info=model_info)

@app.route('/download_dataset/<int:dataset_id>')
@login_required
def download_dataset(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    
    if not current_user.can_download_data():
        flash('Vous devez avoir un abonnement Premium Pro pour tÃ©lÃ©charger les donnÃ©es.', 'warning')
        return redirect(url_for('subscription'))
    
    return send_file(dataset.file_path, as_attachment=True)

# ==================== ROUTES PDF ====================
@app.route('/view_pdf/<int:course_id>')
@login_required
def view_pdf(course_id):
    """Visualiser un PDF en ligne"""
    course = Course.query.get_or_404(course_id)
    
    if not current_user.has_access(course.level):
        flash('Vous n\'avez pas accÃ¨s Ã  ce cours.', 'danger')
        return redirect(url_for('courses'))
    
    # Essayer R2
    if R2_ENDPOINT:
        url = get_pdf_url(course.file_name)
        if url:
            return redirect(url)
    
    # Local
    if not course.file_path or not os.path.exists(course.file_path):
        flash('Fichier non trouvÃ©.', 'danger')
        return redirect(url_for('course_detail', course_id=course.id))
    
    return send_file(course.file_path, mimetype='application/pdf')

@app.route('/download_course_pdf/<int:course_id>')
@login_required
def download_course_pdf(course_id):
    """TÃ©lÃ©charger un PDF"""
    course = Course.query.get_or_404(course_id)
    
    if not current_user.can_download_pdf():
        flash('Vous devez avoir un abonnement Premium pour tÃ©lÃ©charger les PDF.', 'warning')
        return redirect(url_for('subscription'))
    
    if not current_user.has_access(course.level):
        flash('Vous n\'avez pas accÃ¨s Ã  ce cours.', 'danger')
        return redirect(url_for('courses'))
    
    # Essayer R2
    if R2_ENDPOINT:
        client = get_r2_client()
        if client:
            try:
                response = client.get_object(Bucket=R2_BUCKET_NAME, Key=course.file_name)
                return send_file(
                    BytesIO(response['Body'].read()),
                    as_attachment=True,
                    download_name=course.file_name or 'cours.pdf',
                    mimetype='application/pdf'
                )
            except ClientError as e:
                print(f"âŒ Erreur R2: {e}", flush=True)
    
    # Local
    if not course.file_path or not os.path.exists(course.file_path):
        flash('Fichier non trouvÃ©.', 'danger')
        return redirect(url_for('course_detail', course_id=course.id))
    
    return send_file(course.file_path, as_attachment=True, download_name=course.file_name or 'cours.pdf')# ==================== ROUTES DE PAIEMENT ====================
@app.route('/subscription')
@login_required
def subscription():
    plans = SUBSCRIPTION_PLANS
    return render_template('subscription.html', plans=plans, current_user=current_user)

@app.route('/payment_callback')
@login_required
def payment_callback():
    plan = request.args.get('plan', 'premium')
    
    if plan in SUBSCRIPTION_PLANS and plan != 'free':
        current_user.subscription_level = plan
        current_user.is_subscription_active = True
        current_user.subscription_expires_at = datetime.utcnow() + timedelta(days=30)
        current_user.reminder_sent = False
        db.session.commit()
        
        flash(f'Paiement rÃ©ussi ! Bienvenue sur le plan {SUBSCRIPTION_PLANS[plan]["name"]} ðŸŽ‰', 'success')
    else:
        flash('Erreur lors du traitement du paiement.', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/payment_cancel')
@login_required
def payment_cancel():
    flash('Paiement annulÃ©. Vous pouvez rÃ©essayer quand vous voulez.', 'warning')
    return redirect(url_for('subscription'))

@app.route('/cancel_subscription', methods=['POST'])
@login_required
def cancel_subscription():
    current_user.subscription_level = 'free'
    current_user.is_subscription_active = False
    current_user.subscription_expires_at = None
    current_user.reminder_sent = False
    db.session.commit()
    
    flash('Votre abonnement a Ã©tÃ© annulÃ©.', 'info')
    return redirect(url_for('dashboard'))

# ==================== ROUTES ADMIN ====================
@app.route('/admin/courses')
@login_required
def admin_courses():
    if not current_user.is_admin:
        flash('AccÃ¨s rÃ©servÃ© aux administrateurs.', 'danger')
        return redirect(url_for('dashboard'))
    
    courses = Course.query.all()
    return render_template('admin_courses.html', courses=courses)

@app.route('/admin/add_course', methods=['POST'])
@login_required
def add_course():
    if not current_user.can_upload_course():
        flash('Seul l\'administrateur peut ajouter des cours.', 'danger')
        return redirect(url_for('dashboard'))
    
    title = request.form.get('title')
    description = request.form.get('description')
    level = request.form.get('level')
    content = request.form.get('content')
    
    file = request.files.get('pdf_file')
    file_name = None
    file_path = None
    
    if file and file.filename:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_filename = f"{timestamp}_{filename}"
        
        pdf_dir = '/app/data/pdfs'
        os.makedirs(pdf_dir, exist_ok=True)
        
        file_path = os.path.join(pdf_dir, new_filename)
        file.save(file_path)
        file_name = filename
    
    course = Course(
        title=title,
        description=description,
        level=level,
        content=content,
        file_name=file_name,
        file_path=file_path
    )
    db.session.add(course)
    db.session.commit()
    
    flash('Cours ajoutÃ© avec succÃ¨s !', 'success')
    return redirect(url_for('admin_courses'))

@app.route('/admin/delete_course/<int:course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    if not current_user.is_admin:
        flash('AccÃ¨s rÃ©servÃ© aux administrateurs.', 'danger')
        return redirect(url_for('dashboard'))
    
    course = Course.query.get_or_404(course_id)
    
    if course.file_path and os.path.exists(course.file_path):
        os.remove(course.file_path)
    
    db.session.delete(course)
    db.session.commit()
    
    flash('Cours supprimÃ© avec succÃ¨s.', 'success')
    return redirect(url_for('admin_courses'))

# ==================== ROUTES ADMIN UTILISATEURS ====================
@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('AccÃ¨s rÃ©servÃ© aux administrateurs.', 'danger')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/update_subscription/<int:user_id>', methods=['POST'])
@login_required
def update_subscription(user_id):
    if not current_user.is_admin:
        flash('AccÃ¨s rÃ©servÃ© aux administrateurs.', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    new_level = request.form.get('subscription_level')
    
    if new_level in ['free', 'premium', 'premium_pro']:
        user.subscription_level = new_level
        if new_level != 'free':
            user.is_subscription_active = True
            user.subscription_expires_at = datetime.utcnow() + timedelta(days=30)
            user.reminder_sent = False
        else:
            user.is_subscription_active = False
            user.subscription_expires_at = None
            user.reminder_sent = False
        db.session.commit()
        flash(f'Abonnement de {user.username} mis Ã  jour vers {SUBSCRIPTION_PLANS[new_level]["name"]}.', 'success')
    else:
        flash('Niveau d\'abonnement invalide.', 'danger')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/toggle_admin/<int:user_id>', methods=['POST'])
@login_required
def toggle_admin(user_id):
    if not current_user.is_admin:
        flash('AccÃ¨s rÃ©servÃ© aux administrateurs.', 'danger')
        return redirect(url_for('dashboard'))
    
    if user_id == current_user.id:
        flash('Vous ne pouvez pas modifier vos propres droits admin.', 'warning')
        return redirect(url_for('admin_users'))
    
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    
    status = 'donnÃ©' if user.is_admin else 'retirÃ©'
    flash(f'Droits admin {status} Ã  {user.username}.', 'success')
    return redirect(url_for('admin_users'))

# ==================== ROUTES MODÃˆLES ====================

@app.route('/models')
@login_required
def models_list():
    """Page de sÃ©lection des modÃ¨les"""
    if not current_user.can_access_models():
        flash('Vous devez avoir un abonnement Premium Pro pour accÃ©der aux modÃ¨les.', 'warning')
        return redirect(url_for('subscription'))
    
    datasets = Dataset.query.all()
    return render_template('models_list.html', datasets=datasets)

@app.route('/models/analyze', methods=['POST'])
@login_required
def models_analyze():
    """ExÃ©cuter l'analyse choisie"""
    if not current_user.can_access_models():
        flash('Vous devez avoir un abonnement Premium Pro pour accÃ©der aux modÃ¨les.', 'warning')
        return redirect(url_for('subscription'))
    
    dataset_id = request.form.get('dataset_id')
    model_type = request.form.get('model_type')
    target_col = request.form.get('target_col')
    feature_cols = request.form.get('feature_cols', '')
    forecast_steps = int(request.form.get('forecast_steps', 12))
    
    dataset = Dataset.query.get_or_404(dataset_id)
    
    try:
        # Utiliser la fonction de lecture automatique
        df = read_data_file(dataset.file_path)
        
        print(f"ðŸ“Š Colonnes disponibles: {list(df.columns)}", flush=True)
        
        # Initialiser les modÃ¨les
        models = EconometricModels(df)
        
        # ExÃ©cuter le modÃ¨le choisi
        features = [f.strip() for f in feature_cols.split(',') if f.strip()] if feature_cols else []
        
        if model_type == 'time_series':
            results = models.time_series_analysis(target_col, forecast_steps=forecast_steps)
        elif model_type == 'regression':
            if not features:
                flash('Veuillez entrer au moins une variable explicative.', 'danger')
                return redirect(url_for('models_list'))
            results = models.regression_analysis(target_col, features)
        elif model_type == 'machine_learning':
            if not features:
                flash('Veuillez entrer au moins une variable explicative.', 'danger')
                return redirect(url_for('models_list'))
            results = models.machine_learning_analysis(target_col, features)
        elif model_type == 'deep_learning':
            if not features:
                flash('Veuillez entrer au moins une variable explicative.', 'danger')
                return redirect(url_for('models_list'))
            results = models.deep_learning_analysis(target_col, features)
        elif model_type == 'financial_series':
            results = models.financial_series_analysis(target_col)
        else:
            flash('Type de modÃ¨le non reconnu.', 'danger')
            return redirect(url_for('models_list'))
        
        # VÃ©rifier les erreurs
        if results.get('errors'):
            for error in results['errors']:
                flash(f'âš ï¸ {error}', 'danger')
            return render_template('models_results.html', 
                                 results=results, 
                                 model_type=model_type,
                                 dataset=dataset,
                                 report_data=None,
                                 report_name=None)
        
        # GÃ©nÃ©rer le rapport Word
        report = create_econometric_report(
            data=df,
            model_results=results,
            model_type=model_type,
            variable_names=[target_col] + features
        )
        
        # Sauvegarder le rapport
        temp_dir = tempfile.mkdtemp()
        report_path = os.path.join(temp_dir, f'rapport_{model_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.docx')
        report.save(report_path)
        
        # Lire le fichier pour l'envoi
        with open(report_path, 'rb') as f:
            report_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Nettoyer
        os.remove(report_path)
        os.rmdir(temp_dir)
        
        return render_template('models_results.html', 
                             results=results, 
                             model_type=model_type,
                             dataset=dataset,
                             report_data=report_data,
                             report_name=os.path.basename(report_path))
    
    except Exception as e:
        flash(f'Erreur lors de l\'analyse : {str(e)}', 'danger')
        return redirect(url_for('models_list'))

@app.route('/models/download_report/<path:report_data>')
@login_required
def download_report(report_data):
    """TÃ©lÃ©charger le rapport Word"""
    if not current_user.can_access_models():
        flash('Vous devez avoir un abonnement Premium Pro pour tÃ©lÃ©charger les rapports.', 'warning')
        return redirect(url_for('subscription'))
    
    try:
        report_binary = base64.b64decode(report_data)
        return send_file(
            BytesIO(report_binary),
            as_attachment=True,
            download_name='rapport_analyse.docx',
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        flash(f'Erreur lors du tÃ©lÃ©chargement : {str(e)}', 'danger')
        return redirect(url_for('models_list'))
@app.route('/generate_chart/<int:dataset_id>/<chart_type>')
@login_required
def generate_chart(dataset_id, chart_type):
    """GÃ©nÃ©rer un graphique pour un dataset"""
    if not current_user.can_access_data():
        flash('Vous devez avoir un abonnement Premium Pro pour accÃ©der aux donnÃ©es.', 'warning')
        return redirect(url_for('subscription'))
    
    dataset = Dataset.query.get_or_404(dataset_id)
    
    try:
        df = read_data_file(dataset.file_path)
        
        # SÃ©lectionner les colonnes numÃ©riques
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        
        if not numeric_cols:
            flash('Aucune colonne numÃ©rique disponible pour les graphiques.', 'warning')
            return redirect(url_for('analytics'))
        
        plt.figure(figsize=(12, 8))
        
        if chart_type == 'histogram':
            # Histogramme de la premiÃ¨re colonne numÃ©rique
            col = numeric_cols[0]
            plt.hist(df[col].dropna(), bins=30, edgecolor='black', alpha=0.7)
            plt.title(f'Histogramme de {col}')
            plt.xlabel(col)
            plt.ylabel('FrÃ©quence')
            
        elif chart_type == 'boxplot':
            # BoÃ®te Ã  moustaches
            df[numeric_cols[:5]].boxplot()
            plt.title('BoÃ®tes Ã  moustaches')
            plt.xticks(rotation=45)
            
        elif chart_type == 'scatter':
            # Nuage de points (2 premiÃ¨res colonnes)
            if len(numeric_cols) >= 2:
                plt.scatter(df[numeric_cols[0]], df[numeric_cols[1]], alpha=0.5)
                plt.xlabel(numeric_cols[0])
                plt.ylabel(numeric_cols[1])
                plt.title(f'Nuage de points : {numeric_cols[0]} vs {numeric_cols[1]}')
            else:
                flash('Besoin d\'au moins 2 colonnes numÃ©riques pour un nuage de points.', 'warning')
                return redirect(url_for('analytics'))
                
        elif chart_type == 'correlation':
            # Matrice de corrÃ©lation
            if len(numeric_cols) >= 2:
                sns.heatmap(df[numeric_cols].corr(), annot=True, cmap='coolwarm', center=0)
                plt.title('Matrice de corrÃ©lation')
            else:
                flash('Besoin d\'au moins 2 colonnes numÃ©riques pour la corrÃ©lation.', 'warning')
                return redirect(url_for('analytics'))
        
        # Sauvegarder le graphique
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        img_buffer.seek(0)
        
        plot_data = base64.b64encode(img_buffer.read()).decode('utf-8')
        plot_url = f'data:image/png;base64,{plot_data}'
        
        return render_template('chart_view.html', plot_url=plot_url, chart_type=chart_type, dataset=dataset)
        
    except Exception as e:
        flash(f'Erreur lors de la gÃ©nÃ©ration du graphique : {str(e)}', 'danger')
        return redirect(url_for('analytics'))

# ==================== INITIALISATION ====================
def init_db():
    with app.app_context():
        db.create_all()

        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@dataecon.ci',
                first_name='Admin',
                last_name='DataEcon',
                is_admin=True,
                email_confirmed=True,
                email_confirmed_at=datetime.utcnow(),
                subscription_level='free',
                is_subscription_active=False
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("âœ… Admin crÃ©Ã© avec succÃ¨s !")

        existing_courses = db.session.execute(db.select(Course)).scalars().all()
        
        if len(existing_courses) == 0:
            print("ðŸ“š Ajout des cours par dÃ©faut...")
            courses_data = [
                {
                    'title': "Introduction Ã  l'Ã‰conomÃ©trie",
                    'description': "Les fondements de l'Ã©conomÃ©trie : rÃ©gression linÃ©aire, hypothÃ¨ses, interprÃ©tation.",
                    'level': 'DÃ©butant',
                    'content': '<h2>Introduction Ã  l\'Ã‰conomÃ©trie</h2><p>Les fondamentaux de l\'Ã©conomÃ©trie.</p>'
                },
                {
                    'title': 'RÃ©gression LinÃ©aire AvancÃ©e',
                    'description': "ModÃ¨les avec plusieurs variables, tests d'hypothÃ¨ses.",
                    'level': 'IntermÃ©diaire',
                    'content': '<h2>RÃ©gression LinÃ©aire AvancÃ©e</h2><p>ModÃ¨les multi-variables.</p>'
                },
                {
                    'title': 'SÃ©ries Temporelles',
                    'description': 'ARIMA, stationnaritÃ©, prÃ©visions.',
                    'level': 'AvancÃ©',
                    'content': '<h2>SÃ©ries Temporelles</h2><p>ARIMA et prÃ©visions.</p>'
                }
            ]

            for c in courses_data:
                course = Course(**c)
                db.session.add(course)
            
            db.session.commit()
            print("âœ… Cours ajoutÃ©s avec succÃ¨s !")
        else:
            print(f"â„¹ï¸ {len(existing_courses)} cours existent dÃ©jÃ .")

# ==================== PLANIFICATEUR DE TÃ‚CHES ====================
# ==================== PLANIFICATEUR DE TÃ‚CHES ====================
try:
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=check_subscription_reminders, trigger="interval", hours=24, id='reminder_job')
    scheduler.add_job(func=downgrade_expired_subscriptions, trigger="interval", hours=24, id='downgrade_job')
    scheduler.start()
    print("âœ… Scheduler dÃ©marrÃ©", flush=True)
except Exception as e:
    print(f"âš ï¸ Erreur scheduler: {e}", flush=True)
# Afficher le port que Render a attribuÃ©
print(f"ðŸ”Œ PORT = {os.environ.get('PORT', 'non dÃ©fini')}", flush=True)

# ==================== INITIALISATION AU CHARGEMENT (pour Gunicorn) ====================
print("ðŸš€ DÃ©marrage de l'application...", flush=True)
try:
    with app.app_context():
        print("ðŸ“¡ Connexion Ã  la base de donnÃ©es...", flush=True)
        init_db()
        print("âœ… Base de donnÃ©es initialisÃ©e avec succÃ¨s !", flush=True)
except Exception as e:
    import traceback
    print(f"âŒ ERREUR INITIALISATION BD: {e}", flush=True)
    traceback.print_exc()
# ==================== FORCER L'ENREGISTREMENT DES ROUTES ====================
# S'assurer que toutes les routes sont bien enregistrÃ©es
print(f"ðŸ“‹ Routes enregistrÃ©es: {len(list(app.url_map.iter_rules()))} routes", flush=True)
for rule in app.url_map.iter_rules():
    print(f"   - {rule.rule}", flush=True)

# ==================== POINT D'ENTRÃ‰E GUNICORN ====================
# Gunicorn appellera cette fonction automatiquement au dÃ©marrage
def create_app():
    """Point d'entrÃ©e pour Gunicorn"""
    return app

# Alias pour Gunicorn (wsgi:application)
application = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
