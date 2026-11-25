# -*- coding: utf-8 -*-
"""
Espace Entreprise DataEcon.Ci (TPE / PME)

- inscription « Entreprise » : organisation, équipe (code d'invitation), rôles
- formulaires collaboratifs (réponses directes + lien public), jeux de données
- tableaux de bord interactifs (indicateurs, graphiques, filtres)
- salle de formation (assignation, suivi, sessions en direct)
- messagerie : canal « Support DataEcon » et canal « Équipe »
- demandes de services (formation, analyse de données, consulting)
- tâches (kanban), documents partagés, annonces
- administration côté plateforme

Les données d'une entreprise ne sont visibles que par ses membres (et par l'administrateur DataEcon.Ci).
"""
import os
import io
import csv
import json
import secrets
import uuid
from datetime import datetime, date, timedelta
from functools import wraps

from flask import (Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort,
                   send_file, Response, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

SECTEURS = ['Agriculture et agro-industrie', 'Commerce et distribution', 'Banque, assurance et microfinance',
            'Industrie et BTP', 'Transport et logistique', 'Santé et pharmacie', 'Éducation et formation',
            'Technologies et télécommunications', 'Hôtellerie, restauration et tourisme',
            'ONG et projets de développement', 'Administration et collectivités', 'Énergie et mines',
            'Services aux entreprises', 'Autre']
TAILLES = [('tpe', 'TPE (moins de 10 salariés)'), ('pme', 'PME (10 à 250 salariés)'),
           ('autre', 'Autre structure (association, ONG, administration)')]
OBJECTIFS = {'formation': "Formation de l'équipe", 'analyse': 'Analyse de données',
             'consulting': "Consultation d'expert (consulting)"}
TYPES_CHAMPS = {'text': 'Texte court', 'textarea': 'Texte long', 'number': 'Nombre', 'date': 'Date',
                'choice': 'Choix unique', 'multi': 'Choix multiples', 'rating': 'Note de 1 à 5', 'yesno': 'Oui / Non'}
KINDS_DEMANDE = {'formation': 'Formation', 'analyse': 'Analyse de données', 'consulting': 'Consulting / expertise'}
STATUTS_DEMANDE = {'nouvelle': 'Nouvelle', 'en_cours': 'En cours', 'terminee': 'Terminée', 'annulee': 'Annulée'}
STATUTS_TACHE = [('a_faire', 'À faire'), ('en_cours', 'En cours'), ('termine', 'Terminé')]
ROLES = {'owner': 'Responsable', 'admin': 'Administrateur', 'member': 'Membre'}
OUTILS_PRATIQUE = {'python': 'Python', 'r': 'R', 'sql': 'SQL', 'tableau': 'Tableau', 'smartpls': 'SmartPLS',
                   'powerbi': 'Power BI'}
NIVEAUX = {'debutant': 'Débutant', 'intermediaire': 'Intermédiaire', 'avance': 'Avancé'}
EXT_DOCS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'ppt', 'pptx', 'txt', 'png', 'jpg', 'jpeg', 'zip'}
MAX_DOC = 25 * 1024 * 1024
MAX_LIGNES = 20000


def _now():
    return datetime.utcnow()


def _j(s, default):
    try:
        return json.loads(s) if s else default
    except Exception:
        return default


def init_enterprise(app, db, User, Course=None, notify=None):
    bp = Blueprint('ent', __name__, url_prefix='/entreprise')

    # ------------------------------------------------------------------ modèles
    class Organization(db.Model):
        __tablename__ = 'org_organization'
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(160), nullable=False)
        sector = db.Column(db.String(120))
        size = db.Column(db.String(10))
        purposes = db.Column(db.String(120))
        country = db.Column(db.String(80))
        city = db.Column(db.String(80))
        invite_code = db.Column(db.String(16), unique=True, index=True)
        owner_id = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=_now)

        def objectifs(self):
            return [OBJECTIFS[p] for p in (self.purposes or '').split(',') if p in OBJECTIFS]

    class Form(db.Model):
        __tablename__ = 'org_form'
        id = db.Column(db.Integer, primary_key=True)
        org_id = db.Column(db.Integer, index=True, nullable=False)
        title = db.Column(db.String(200), nullable=False)
        description = db.Column(db.Text)
        fields = db.Column(db.Text, default='[]')
        is_open = db.Column(db.Boolean, default=True)
        public_token = db.Column(db.String(32), unique=True, index=True)
        created_by = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=_now)

        def champs(self):
            return _j(self.fields, [])

    class FormResponse(db.Model):
        __tablename__ = 'org_form_response'
        id = db.Column(db.Integer, primary_key=True)
        form_id = db.Column(db.Integer, index=True, nullable=False)
        user_id = db.Column(db.Integer)
        respondent = db.Column(db.String(120))
        data = db.Column(db.Text, default='{}')
        created_at = db.Column(db.DateTime, default=_now)

    class OrgDataset(db.Model):
        __tablename__ = 'org_dataset'
        id = db.Column(db.Integer, primary_key=True)
        org_id = db.Column(db.Integer, index=True, nullable=False)
        name = db.Column(db.String(200), nullable=False)
        columns = db.Column(db.Text, default='[]')
        rows = db.Column(db.Text, default='[]')
        n_rows = db.Column(db.Integer, default=0)
        created_by = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=_now)

    class Dashboard(db.Model):
        __tablename__ = 'org_dashboard'
        id = db.Column(db.Integer, primary_key=True)
        org_id = db.Column(db.Integer, index=True, nullable=False)
        title = db.Column(db.String(200), nullable=False)
        source_kind = db.Column(db.String(10))       # form | dataset
        source_id = db.Column(db.Integer)
        config = db.Column(db.Text, default='{}')     # {widgets: [...], filters: [...]}
        created_by = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=_now)
        updated_at = db.Column(db.DateTime, default=_now)

    class Training(db.Model):
        __tablename__ = 'org_training'
        id = db.Column(db.Integer, primary_key=True)
        org_id = db.Column(db.Integer, index=True, nullable=False)
        kind = db.Column(db.String(10))               # course | pratique
        ref = db.Column(db.String(60))
        title = db.Column(db.String(200))
        due_date = db.Column(db.Date)
        assigned_to = db.Column(db.Integer)           # null = toute l'équipe
        created_by = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=_now)

    class TrainingDone(db.Model):
        __tablename__ = 'org_training_done'
        id = db.Column(db.Integer, primary_key=True)
        training_id = db.Column(db.Integer, index=True)
        user_id = db.Column(db.Integer, index=True)
        done_at = db.Column(db.DateTime, default=_now)

    class LiveSession(db.Model):
        __tablename__ = 'org_session'
        id = db.Column(db.Integer, primary_key=True)
        org_id = db.Column(db.Integer, index=True)    # null = ouverte à toutes les entreprises
        title = db.Column(db.String(200), nullable=False)
        description = db.Column(db.Text)
        starts_at = db.Column(db.DateTime)
        link = db.Column(db.String(400))
        created_by = db.Column(db.Integer)

    class Message(db.Model):
        __tablename__ = 'org_message'
        id = db.Column(db.Integer, primary_key=True)
        org_id = db.Column(db.Integer, index=True, nullable=False)
        channel = db.Column(db.String(10), index=True)   # support | team
        user_id = db.Column(db.Integer)
        author = db.Column(db.String(120))
        from_staff = db.Column(db.Boolean, default=False)
        body = db.Column(db.Text)
        created_at = db.Column(db.DateTime, default=_now)

    class ReadMark(db.Model):
        __tablename__ = 'org_read'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, index=True)
        key = db.Column(db.String(30))
        last_id = db.Column(db.Integer, default=0)

    class ServiceRequest(db.Model):
        __tablename__ = 'org_request'
        id = db.Column(db.Integer, primary_key=True)
        org_id = db.Column(db.Integer, index=True, nullable=False)
        user_id = db.Column(db.Integer)
        kind = db.Column(db.String(12))
        title = db.Column(db.String(200))
        description = db.Column(db.Text)
        status = db.Column(db.String(12), default='nouvelle')
        admin_note = db.Column(db.Text)
        created_at = db.Column(db.DateTime, default=_now)
        updated_at = db.Column(db.DateTime, default=_now)

    class Task(db.Model):
        __tablename__ = 'org_task'
        id = db.Column(db.Integer, primary_key=True)
        org_id = db.Column(db.Integer, index=True, nullable=False)
        title = db.Column(db.String(200), nullable=False)
        description = db.Column(db.Text)
        status = db.Column(db.String(10), default='a_faire')
        assignee_id = db.Column(db.Integer)
        due_date = db.Column(db.Date)
        created_by = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=_now)

    class Document(db.Model):
        __tablename__ = 'org_document'
        id = db.Column(db.Integer, primary_key=True)
        org_id = db.Column(db.Integer, index=True, nullable=False)
        name = db.Column(db.String(200))
        stored = db.Column(db.String(300))
        size = db.Column(db.Integer)
        uploaded_by = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=_now)

    class Announcement(db.Model):
        __tablename__ = 'org_announcement'
        id = db.Column(db.Integer, primary_key=True)
        org_id = db.Column(db.Integer, index=True, nullable=False)
        title = db.Column(db.String(200))
        body = db.Column(db.Text)
        author = db.Column(db.String(120))
        created_at = db.Column(db.DateTime, default=_now)

    # ------------------------------------------------------------------ utilitaires
    def staff_notify(subject, html):
        to = os.environ.get('ADMIN_NOTIFY_EMAIL')
        if notify and to:
            try:
                notify(to, 'DataEcon.Ci', subject, html)
            except Exception:
                pass

    def new_invite_code():
        while True:
            c = secrets.token_hex(4).upper()
            if not Organization.query.filter_by(invite_code=c).first():
                return c

    def create_organization(user, name, sector, size, purposes, country, city):
        org = Organization(name=name[:160], sector=sector, size=size, purposes=','.join(p for p in purposes if p in OBJECTIFS),
                           country=country, city=city, invite_code=new_invite_code(), owner_id=user.id)
        db.session.add(org)
        db.session.flush()
        user.account_type = 'entreprise'
        user.org_id = org.id
        user.org_role = 'owner'
        db.session.add(Announcement(org_id=org.id, title='Bienvenue dans votre espace entreprise',
                                    body="Invitez votre équipe avec le code d'invitation (page Équipe), créez vos premiers formulaires et tableaux de bord, "
                                         "et contactez-nous depuis la messagerie pour une formation, une analyse de données ou une mission de consulting.",
                                    author='DataEcon.Ci'))
        return org

    def join_organization(user, code):
        org = Organization.query.filter_by(invite_code=(code or '').strip().upper()).first()
        if not org:
            return None
        user.account_type = 'entreprise'
        user.org_id = org.id
        user.org_role = 'member'
        return org

    app.config['ent_create_org'] = create_organization
    app.config['ent_join_org'] = join_organization

    def org_required(f):
        @wraps(f)
        @login_required
        def w(*a, **k):
            if getattr(current_user, 'account_type', None) != 'entreprise' or not current_user.org_id:
                flash("Cet espace est réservé aux comptes entreprise.", 'warning')
                return redirect(url_for('dashboard'))
            return f(*a, **k)
        return w

    def org_admin_required(f):
        @wraps(f)
        @org_required
        def w(*a, **k):
            if current_user.org_role not in ('owner', 'admin'):
                flash("Action réservée aux administrateurs de l'entreprise.", 'warning')
                return redirect(url_for('ent.home'))
            return f(*a, **k)
        return w

    def staff_required(f):
        @wraps(f)
        @login_required
        def w(*a, **k):
            if not current_user.is_admin:
                abort(403)
            return f(*a, **k)
        return w

    def my_org():
        return Organization.query.get(current_user.org_id)

    def members(org_id):
        return User.query.filter_by(org_id=org_id).order_by(User.first_name).all()

    def name_of(u):
        return ((u.first_name or '') + ' ' + (u.last_name or '')).strip() or u.username

    def unread(key, org_id, channel, user_id):
        mk = ReadMark.query.filter_by(user_id=user_id, key=key).first()
        last = mk.last_id if mk else 0
        q = Message.query.filter(Message.org_id == org_id, Message.channel == channel, Message.id > last)
        if channel == 'team':
            q = q.filter(Message.user_id != user_id)
        elif key.startswith('support:'):                       # côté plateforme : messages de l'entreprise
            q = q.filter(Message.from_staff.is_(False))
        else:                                                  # côté entreprise : messages du support
            q = q.filter(Message.from_staff.is_(True))
        return q.count()

    def mark_read(key, user_id, last_id):
        mk = ReadMark.query.filter_by(user_id=user_id, key=key).first()
        if not mk:
            mk = ReadMark(user_id=user_id, key=key, last_id=0)
            db.session.add(mk)
        if last_id > (mk.last_id or 0):
            mk.last_id = last_id
        db.session.commit()

    @app.context_processor
    def ent_context():
        try:
            if current_user.is_authenticated and getattr(current_user, 'account_type', None) == 'entreprise' and current_user.org_id:
                return {'org_name': (Organization.query.get(current_user.org_id) or Organization(name='Mon entreprise')).name,
                        'ent_unread_support': unread('support', current_user.org_id, 'support', current_user.id),
                        'ent_unread_team': unread('team', current_user.org_id, 'team', current_user.id),
                        'ent_is_admin': current_user.org_role in ('owner', 'admin')}
        except Exception:
            pass
        return {'org_name': '', 'ent_unread_support': 0, 'ent_unread_team': 0, 'ent_is_admin': False}

    # ------------------------------------------------------------------ accueil
    @bp.route('/')
    @org_required
    def home():
        org = my_org()
        oid = org.id
        mem = members(oid)
        forms = Form.query.filter_by(org_id=oid).all()
        fids = [f.id for f in forms]
        since = _now() - timedelta(days=13)
        resp = FormResponse.query.filter(FormResponse.form_id.in_(fids or [0]), FormResponse.created_at >= since).all()
        days = [(date.today() - timedelta(days=i)) for i in range(13, -1, -1)]
        series = [sum(1 for r in resp if r.created_at.date() == d) for d in days]
        total_resp = FormResponse.query.filter(FormResponse.form_id.in_(fids or [0])).count()
        tasks = Task.query.filter_by(org_id=oid).all()
        trainings = Training.query.filter_by(org_id=oid).all()
        done = {(d.training_id, d.user_id) for d in TrainingDone.query.filter(TrainingDone.training_id.in_([t.id for t in trainings] or [0])).all()}
        expected = sum(len(mem) if t.assigned_to is None else 1 for t in trainings)
        pct = round(100 * len(done) / expected) if expected else None
        reqs = ServiceRequest.query.filter_by(org_id=oid).order_by(ServiceRequest.created_at.desc()).limit(5).all()
        ann = Announcement.query.filter_by(org_id=oid).order_by(Announcement.created_at.desc()).limit(4).all()
        sessions = LiveSession.query.filter(((LiveSession.org_id == oid) | (LiveSession.org_id.is_(None))),
                                            LiveSession.starts_at >= _now()).order_by(LiveSession.starts_at).limit(3).all()
        mine = [t for t in tasks if t.assignee_id == current_user.id and t.status != 'termine']
        return render_template('ent_home.html', org=org, n_members=len(mem), forms=forms, total_resp=total_resp,
                               days=[d.strftime('%d/%m') for d in days], series=series, tasks=tasks, mine=mine, pct=pct,
                               reqs=reqs, ann=ann, sessions=sessions, STATUTS=STATUTS_DEMANDE, KINDS=KINDS_DEMANDE)

    @bp.route('/annonces', methods=['POST'])
    @org_admin_required
    def announce():
        t, b = (request.form.get('title') or '').strip(), (request.form.get('body') or '').strip()
        if t and b:
            db.session.add(Announcement(org_id=current_user.org_id, title=t[:200], body=b[:4000], author=name_of(current_user)))
            db.session.commit()
            flash('Annonce publiée.', 'success')
        return redirect(url_for('ent.home'))

    @bp.route('/annonces/<int:aid>/supprimer', methods=['POST'])
    @org_admin_required
    def announce_delete(aid):
        a = Announcement.query.filter_by(id=aid, org_id=current_user.org_id).first_or_404()
        db.session.delete(a)
        db.session.commit()
        return redirect(url_for('ent.home'))

    # ------------------------------------------------------------------ équipe
    @bp.route('/equipe')
    @org_required
    def team():
        org = my_org()
        return render_template('ent_team.html', org=org, mem=members(org.id), ROLES=ROLES, SECTEURS=SECTEURS, TAILLES=TAILLES, OBJECTIFS=OBJECTIFS)

    @bp.route('/equipe/profil', methods=['POST'])
    @org_admin_required
    def team_profile():
        org = my_org()
        org.name = (request.form.get('name') or org.name).strip()[:160]
        org.sector = request.form.get('sector') or org.sector
        org.size = request.form.get('size') or org.size
        org.city = (request.form.get('city') or '').strip()[:80]
        org.country = (request.form.get('country') or '').strip()[:80]
        org.purposes = ','.join(p for p in request.form.getlist('purposes') if p in OBJECTIFS)
        db.session.commit()
        flash("Informations de l'entreprise mises à jour.", 'success')
        return redirect(url_for('ent.team'))

    @bp.route('/equipe/code', methods=['POST'])
    @org_admin_required
    def team_code():
        org = my_org()
        org.invite_code = new_invite_code()
        db.session.commit()
        flash("Nouveau code d'invitation généré : l'ancien code ne fonctionne plus.", 'success')
        return redirect(url_for('ent.team'))

    @bp.route('/equipe/<int:uid>/role', methods=['POST'])
    @org_admin_required
    def team_role(uid):
        u = User.query.filter_by(id=uid, org_id=current_user.org_id).first_or_404()
        role = request.form.get('role')
        if u.org_role == 'owner' or role not in ('admin', 'member') or (current_user.org_role != 'owner' and role == 'admin'):
            flash('Modification de rôle non autorisée.', 'warning')
        else:
            u.org_role = role
            db.session.commit()
            flash('Rôle mis à jour.', 'success')
        return redirect(url_for('ent.team'))

    @bp.route('/equipe/<int:uid>/retirer', methods=['POST'])
    @org_admin_required
    def team_remove(uid):
        u = User.query.filter_by(id=uid, org_id=current_user.org_id).first_or_404()
        if u.org_role == 'owner' or u.id == current_user.id:
            flash('Ce membre ne peut pas être retiré.', 'warning')
        else:
            u.org_id = None
            u.org_role = None
            u.account_type = 'particulier'
            db.session.commit()
            flash('Membre retiré de l\'entreprise.', 'success')
        return redirect(url_for('ent.team'))

    # ------------------------------------------------------------------ formulaires
    def clean_fields(raw):
        out = []
        for i, f in enumerate(raw or []):
            t = f.get('type')
            label = (f.get('label') or '').strip()
            if t not in TYPES_CHAMPS or not label:
                continue
            opts = [str(o).strip()[:100] for o in (f.get('options') or []) if str(o).strip()]
            if t in ('choice', 'multi') and len(opts) < 2:
                continue
            out.append({'id': 'q%d' % (len(out) + 1), 'label': label[:200], 'type': t, 'required': bool(f.get('required')),
                        'options': opts[:30] if t in ('choice', 'multi') else []})
        return out[:60]

    def get_form(fid):
        return Form.query.filter_by(id=fid, org_id=current_user.org_id).first_or_404()

    @bp.route('/formulaires')
    @org_required
    def forms_list():
        fs = Form.query.filter_by(org_id=current_user.org_id).order_by(Form.created_at.desc()).all()
        counts = {f.id: FormResponse.query.filter_by(form_id=f.id).count() for f in fs}
        return render_template('ent_forms.html', forms=fs, counts=counts)

    @bp.route('/formulaires/nouveau', methods=['GET', 'POST'])
    @bp.route('/formulaires/<int:fid>/modifier', methods=['GET', 'POST'])
    @org_required
    def form_edit(fid=None):
        f = get_form(fid) if fid else None
        if request.method == 'POST':
            data = request.get_json(silent=True) or {}
            title = (data.get('title') or '').strip()
            fields = clean_fields(data.get('fields'))
            if not title or not fields:
                return jsonify({'ok': False, 'error': 'Indiquez un titre et au moins une question valide.'}), 400
            if f is None:
                f = Form(org_id=current_user.org_id, created_by=current_user.id)
                db.session.add(f)
            elif FormResponse.query.filter_by(form_id=f.id).count() and [x['id'] for x in f.champs()] != [x['id'] for x in fields]:
                pass   # des réponses existent : les identifiants sont conservés par position, les anciennes réponses restent lisibles
            f.title = title[:200]
            f.description = (data.get('description') or '')[:2000]
            f.fields = json.dumps(fields, ensure_ascii=False)
            f.is_open = bool(data.get('is_open', True))
            if data.get('public') and not f.public_token:
                f.public_token = secrets.token_urlsafe(16)
            if not data.get('public'):
                f.public_token = None
            db.session.commit()
            return jsonify({'ok': True, 'url': url_for('ent.form_responses', fid=f.id)})
        return render_template('ent_form_edit.html', form=f, TYPES=TYPES_CHAMPS)

    @bp.route('/formulaires/<int:fid>/supprimer', methods=['POST'])
    @org_admin_required
    def form_delete(fid):
        f = get_form(fid)
        FormResponse.query.filter_by(form_id=f.id).delete()
        Dashboard.query.filter_by(org_id=f.org_id, source_kind='form', source_id=f.id).delete()
        db.session.delete(f)
        db.session.commit()
        flash('Formulaire supprimé avec ses réponses.', 'success')
        return redirect(url_for('ent.forms_list'))

    @bp.route('/formulaires/<int:fid>/basculer', methods=['POST'])
    @org_required
    def form_toggle(fid):
        f = get_form(fid)
        f.is_open = not f.is_open
        db.session.commit()
        return redirect(url_for('ent.forms_list'))

    def validate_answers(form, src):
        data, errors = {}, []
        for c in form.champs():
            k = c['id']
            if c['type'] == 'multi':
                v = [x for x in src.getlist(k) if x in c['options']]
                val = v
                empty = not v
            else:
                v = (src.get(k) or '').strip()
                val = v
                empty = v == ''
                if not empty:
                    if c['type'] == 'number':
                        try:
                            val = float(v.replace(',', '.').replace(' ', ''))
                        except ValueError:
                            errors.append('« %s » doit être un nombre.' % c['label'])
                            continue
                    elif c['type'] == 'date':
                        try:
                            datetime.strptime(v, '%Y-%m-%d')
                        except ValueError:
                            errors.append('« %s » doit être une date valide.' % c['label'])
                            continue
                    elif c['type'] == 'rating':
                        if v not in ('1', '2', '3', '4', '5'):
                            errors.append('« %s » : note invalide.' % c['label'])
                            continue
                        val = int(v)
                    elif c['type'] in ('choice', 'yesno'):
                        allowed = c['options'] if c['type'] == 'choice' else ['Oui', 'Non']
                        if v not in allowed:
                            errors.append('« %s » : choix invalide.' % c['label'])
                            continue
                    else:
                        val = v[:4000]
            if empty and c['required']:
                errors.append('La question « %s » est obligatoire.' % c['label'])
            data[k] = None if empty else val
        return data, errors

    @bp.route('/formulaires/<int:fid>/remplir', methods=['GET', 'POST'])
    @org_required
    def form_fill(fid):
        f = get_form(fid)
        if not f.is_open:
            flash('Ce formulaire est fermé.', 'warning')
            return redirect(url_for('ent.forms_list'))
        if request.method == 'POST':
            data, errors = validate_answers(f, request.form)
            if errors:
                for e in errors:
                    flash(e, 'danger')
                return render_template('ent_form_fill.html', form=f, public=False, values=request.form)
            db.session.add(FormResponse(form_id=f.id, user_id=current_user.id, respondent=name_of(current_user),
                                        data=json.dumps(data, ensure_ascii=False)))
            db.session.commit()
            flash('Réponse enregistrée. Merci !', 'success')
            return redirect(url_for('ent.forms_list'))
        return render_template('ent_form_fill.html', form=f, public=False, values={})

    @app.route('/f/<token>', methods=['GET', 'POST'])
    def public_form(token):
        f = Form.query.filter_by(public_token=token).first_or_404()
        if not f.is_open:
            return render_template('ent_form_fill.html', form=f, public=True, closed=True, values={})
        if request.method == 'POST':
            if request.form.get('website'):               # champ piège anti-robots
                return render_template('ent_form_fill.html', form=f, public=True, done=True, values={})
            data, errors = validate_answers(f, request.form)
            if FormResponse.query.filter_by(form_id=f.id).count() >= MAX_LIGNES:
                errors.append('Ce formulaire a atteint son nombre maximal de réponses.')
            if errors:
                for e in errors:
                    flash(e, 'danger')
                return render_template('ent_form_fill.html', form=f, public=True, values=request.form)
            db.session.add(FormResponse(form_id=f.id, respondent=(request.form.get('__nom') or 'Anonyme')[:120],
                                        data=json.dumps(data, ensure_ascii=False)))
            db.session.commit()
            return render_template('ent_form_fill.html', form=f, public=True, done=True, values={})
        return render_template('ent_form_fill.html', form=f, public=True, values={})

    def form_table(f):
        champs = f.champs()
        cols = [{'name': c['label'], 'type': 'number' if c['type'] in ('number', 'rating') else ('date' if c['type'] == 'date' else 'text')} for c in champs]
        cols += [{'name': 'Répondant', 'type': 'text'}, {'name': 'Date de réponse', 'type': 'date'}]
        rows = []
        for r in FormResponse.query.filter_by(form_id=f.id).order_by(FormResponse.created_at).limit(MAX_LIGNES).all():
            d = _j(r.data, {})
            row = {}
            for c in champs:
                v = d.get(c['id'])
                row[c['label']] = ', '.join(v) if isinstance(v, list) else v
            row['Répondant'] = r.respondent or ''
            row['Date de réponse'] = r.created_at.strftime('%Y-%m-%d')
            rows.append(row)
        return cols, rows

    @bp.route('/formulaires/<int:fid>/reponses')
    @org_required
    def form_responses(fid):
        f = get_form(fid)
        cols, rows = form_table(f)
        return render_template('ent_form_responses.html', form=f, cols=cols, rows=rows, n=len(rows),
                               public_url=url_for('public_form', token=f.public_token, _external=True) if f.public_token else None)

    @bp.route('/formulaires/<int:fid>/reponses/<int:rid>/supprimer', methods=['POST'])
    @org_admin_required
    def response_delete(fid, rid):
        f = get_form(fid)
        FormResponse.query.filter_by(id=rid, form_id=f.id).delete()
        db.session.commit()
        return redirect(url_for('ent.form_responses', fid=fid))

    @bp.route('/formulaires/<int:fid>/export.csv')
    @org_required
    def form_export(fid):
        f = get_form(fid)
        cols, rows = form_table(f)
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=';')
        w.writerow([c['name'] for c in cols])
        for r in rows:
            w.writerow([('' if r.get(c['name']) is None else r.get(c['name'])) for c in cols])
        return Response('﻿' + buf.getvalue(), mimetype='text/csv; charset=utf-8',
                        headers={'Content-Disposition': 'attachment; filename=reponses_%d.csv' % f.id})

    # ------------------------------------------------------------------ jeux de données
    @bp.route('/donnees', methods=['GET', 'POST'])
    @org_required
    def datasets():
        if request.method == 'POST':
            file = request.files.get('file')
            if not file or not file.filename:
                flash('Choisissez un fichier CSV ou Excel.', 'warning')
                return redirect(url_for('ent.datasets'))
            try:
                import pandas as pd
                ext = file.filename.rsplit('.', 1)[-1].lower()
                if ext in ('xlsx', 'xls'):
                    df = pd.read_excel(file)
                elif ext in ('csv', 'txt'):
                    raw = file.read()
                    try:
                        txt = raw.decode('utf-8-sig')
                    except UnicodeDecodeError:
                        txt = raw.decode('latin-1')
                    df = pd.read_csv(io.StringIO(txt), sep=None, engine='python')
                else:
                    raise ValueError('Format non pris en charge (CSV, XLSX).')
                df = df.iloc[:MAX_LIGNES, :60]
                cols = []
                for c in df.columns:
                    s = df[c]
                    if pd.api.types.is_numeric_dtype(s):
                        t = 'number'
                    elif pd.api.types.is_datetime64_any_dtype(s):
                        t = 'date'
                    else:
                        t = 'text'
                    cols.append({'name': str(c)[:80], 'type': t})
                df.columns = [c['name'] for c in cols]
                rows = []
                for rec in df.to_dict('records'):
                    row = {}
                    for k, v in rec.items():
                        if v is None or (isinstance(v, float) and v != v):
                            row[k] = None
                        elif hasattr(v, 'strftime'):
                            row[k] = v.strftime('%Y-%m-%d')
                        elif hasattr(v, 'item'):
                            row[k] = v.item()
                        else:
                            row[k] = v
                    rows.append(row)
                ds = OrgDataset(org_id=current_user.org_id, name=(request.form.get('name') or file.filename)[:200],
                                columns=json.dumps(cols, ensure_ascii=False), rows=json.dumps(rows, ensure_ascii=False),
                                n_rows=len(rows), created_by=current_user.id)
                db.session.add(ds)
                db.session.commit()
                flash('Jeu de données importé : %d lignes, %d colonnes.' % (len(rows), len(cols)), 'success')
            except Exception as e:
                flash('Import impossible : %s' % e, 'danger')
            return redirect(url_for('ent.datasets'))
        items = OrgDataset.query.filter_by(org_id=current_user.org_id).order_by(OrgDataset.created_at.desc()).all()
        return render_template('ent_data.html', items=items)

    @bp.route('/donnees/<int:did>/supprimer', methods=['POST'])
    @org_admin_required
    def dataset_delete(did):
        ds = OrgDataset.query.filter_by(id=did, org_id=current_user.org_id).first_or_404()
        Dashboard.query.filter_by(org_id=ds.org_id, source_kind='dataset', source_id=ds.id).delete()
        db.session.delete(ds)
        db.session.commit()
        flash('Jeu de données supprimé.', 'success')
        return redirect(url_for('ent.datasets'))

    # ------------------------------------------------------------------ tableaux de bord
    def source_payload(kind, sid):
        if kind == 'form':
            f = get_form(sid)
            cols, rows = form_table(f)
            return {'name': f.title, 'columns': cols, 'rows': rows}
        ds = OrgDataset.query.filter_by(id=sid, org_id=current_user.org_id).first_or_404()
        return {'name': ds.name, 'columns': _j(ds.columns, []), 'rows': _j(ds.rows, [])}

    @bp.route('/api/source/<kind>/<int:sid>')
    @org_required
    def api_source(kind, sid):
        if kind not in ('form', 'dataset'):
            abort(404)
        return jsonify(source_payload(kind, sid))

    @bp.route('/tableaux-de-bord')
    @org_required
    def dash_list():
        oid = current_user.org_id
        ds = Dashboard.query.filter_by(org_id=oid).order_by(Dashboard.updated_at.desc()).all()
        forms = Form.query.filter_by(org_id=oid).all()
        sets = OrgDataset.query.filter_by(org_id=oid).all()
        names = {('form', f.id): f.title for f in forms}
        names.update({('dataset', s.id): s.name for s in sets})
        return render_template('ent_dash_list.html', dashboards=ds, forms=forms, sets=sets, names=names)

    @bp.route('/tableaux-de-bord/creer', methods=['POST'])
    @org_required
    def dash_create():
        src = (request.form.get('source') or '').split(':')
        if len(src) != 2 or src[0] not in ('form', 'dataset') or not src[1].isdigit():
            flash('Choisissez une source de données.', 'warning')
            return redirect(url_for('ent.dash_list'))
        payload = source_payload(src[0], int(src[1]))
        cols = payload['columns']
        nums = [c['name'] for c in cols if c['type'] == 'number']
        cats = [c['name'] for c in cols if c['type'] == 'text' and c['name'] != 'Répondant']
        widgets = [{'id': 'w1', 'type': 'kpi', 'title': 'Nombre de lignes', 'agg': 'count', 'field': '', 'group': '', 'w': 1}]
        if nums:
            widgets.append({'id': 'w2', 'type': 'kpi', 'title': 'Total : ' + nums[0], 'agg': 'sum', 'field': nums[0], 'group': '', 'w': 1})
            widgets.append({'id': 'w3', 'type': 'kpi', 'title': 'Moyenne : ' + nums[0], 'agg': 'avg', 'field': nums[0], 'group': '', 'w': 1})
        if cats:
            widgets.append({'id': 'w4', 'type': 'bar', 'title': 'Répartition par ' + cats[0], 'agg': 'count', 'field': '', 'group': cats[0], 'w': 2})
        cfg = {'widgets': widgets, 'filters': cats[:3]}
        d = Dashboard(org_id=current_user.org_id, title=(request.form.get('title') or 'Tableau de bord : ' + payload['name'])[:200],
                      source_kind=src[0], source_id=int(src[1]), config=json.dumps(cfg, ensure_ascii=False), created_by=current_user.id)
        db.session.add(d)
        db.session.commit()
        return redirect(url_for('ent.dash_view', did=d.id, edit=1))

    def get_dash(did):
        return Dashboard.query.filter_by(id=did, org_id=current_user.org_id).first_or_404()

    @bp.route('/tableaux-de-bord/<int:did>')
    @org_required
    def dash_view(did):
        d = get_dash(did)
        return render_template('ent_dash.html', dash=d, config=_j(d.config, {'widgets': [], 'filters': []}))

    @bp.route('/tableaux-de-bord/<int:did>/enregistrer', methods=['POST'])
    @org_required
    def dash_save(did):
        d = get_dash(did)
        data = request.get_json(silent=True) or {}
        ws = []
        for i, w in enumerate((data.get('widgets') or [])[:40]):
            if w.get('type') not in ('kpi', 'bar', 'line', 'pie', 'table'):
                continue
            ws.append({'id': 'w%d' % (i + 1), 'type': w['type'], 'title': str(w.get('title') or '')[:120],
                       'agg': w.get('agg') if w.get('agg') in ('count', 'sum', 'avg', 'min', 'max', 'distinct') else 'count',
                       'field': str(w.get('field') or '')[:100], 'group': str(w.get('group') or '')[:100],
                       'w': w.get('w') if w.get('w') in (1, 2, 3) else 1})
        d.config = json.dumps({'widgets': ws, 'filters': [str(x)[:100] for x in (data.get('filters') or [])][:6]}, ensure_ascii=False)
        if data.get('title'):
            d.title = str(data['title'])[:200]
        d.updated_at = _now()
        db.session.commit()
        return jsonify({'ok': True})

    @bp.route('/tableaux-de-bord/<int:did>/supprimer', methods=['POST'])
    @org_admin_required
    def dash_delete(did):
        db.session.delete(get_dash(did))
        db.session.commit()
        flash('Tableau de bord supprimé.', 'success')
        return redirect(url_for('ent.dash_list'))

    # ------------------------------------------------------------------ salle de formation
    def catalogue():
        items = []
        if Course is not None:
            for c in Course.query.order_by(Course.id).all():
                items.append({'kind': 'course', 'ref': str(c.id), 'title': c.title, 'level': c.level,
                              'url': url_for('course_detail', course_id=c.id)})
        for o, on in OUTILS_PRATIQUE.items():
            for n, nn in NIVEAUX.items():
                items.append({'kind': 'pratique', 'ref': '%s/%s' % (o, n), 'title': 'Formation pratique %s - %s' % (on, nn),
                              'level': nn, 'url': url_for('formations_player', outil=o, niveau=n)})
        return items

    def training_url(t):
        if t.kind == 'course':
            return url_for('course_detail', course_id=int(t.ref)) if t.ref.isdigit() else '#'
        o, _, n = (t.ref or '').partition('/')
        return url_for('formations_player', outil=o, niveau=n) if o in OUTILS_PRATIQUE and n in NIVEAUX else '#'

    @bp.route('/formation')
    @org_required
    def training():
        org = my_org()
        mem = members(org.id)
        ts = Training.query.filter_by(org_id=org.id).order_by(Training.created_at.desc()).all()
        done = {(d.training_id, d.user_id) for d in TrainingDone.query.filter(TrainingDone.training_id.in_([t.id for t in ts] or [0])).all()}
        mine = [t for t in ts if t.assigned_to in (None, current_user.id)]
        sessions = LiveSession.query.filter((LiveSession.org_id == org.id) | (LiveSession.org_id.is_(None))).order_by(LiveSession.starts_at.desc()).limit(20).all()
        return render_template('ent_training.html', org=org, mem=mem, ts=ts, mine=mine, done=done, sessions=sessions,
                               catalogue=catalogue(), training_url=training_url, now=_now())

    @bp.route('/formation/assigner', methods=['POST'])
    @org_admin_required
    def training_assign():
        kind, _, ref = (request.form.get('item') or '').partition('|')
        cat = {(c['kind'], c['ref']): c for c in catalogue()}
        c = cat.get((kind, ref))
        if not c:
            flash('Formation introuvable.', 'danger')
            return redirect(url_for('ent.training'))
        who = request.form.get('who') or 'all'
        assigned = None
        if who != 'all':
            u = User.query.filter_by(id=int(who) if who.isdigit() else 0, org_id=current_user.org_id).first()
            assigned = u.id if u else None
            if not u:
                flash('Membre introuvable.', 'danger')
                return redirect(url_for('ent.training'))
        due = None
        try:
            due = datetime.strptime(request.form.get('due') or '', '%Y-%m-%d').date()
        except ValueError:
            pass
        db.session.add(Training(org_id=current_user.org_id, kind=kind, ref=ref, title=c['title'], due_date=due,
                                assigned_to=assigned, created_by=current_user.id))
        db.session.commit()
        flash('Formation assignée.', 'success')
        return redirect(url_for('ent.training'))

    @bp.route('/formation/<int:tid>/terminer', methods=['POST'])
    @org_required
    def training_done(tid):
        t = Training.query.filter_by(id=tid, org_id=current_user.org_id).first_or_404()
        if t.assigned_to not in (None, current_user.id):
            abort(403)
        d = TrainingDone.query.filter_by(training_id=t.id, user_id=current_user.id).first()
        if d:
            db.session.delete(d)
        else:
            db.session.add(TrainingDone(training_id=t.id, user_id=current_user.id))
        db.session.commit()
        return redirect(url_for('ent.training'))

    @bp.route('/formation/<int:tid>/supprimer', methods=['POST'])
    @org_admin_required
    def training_delete(tid):
        t = Training.query.filter_by(id=tid, org_id=current_user.org_id).first_or_404()
        TrainingDone.query.filter_by(training_id=t.id).delete()
        db.session.delete(t)
        db.session.commit()
        return redirect(url_for('ent.training'))

    @bp.route('/formation/session', methods=['POST'])
    @org_admin_required
    def session_create():
        title = (request.form.get('title') or '').strip()
        try:
            starts = datetime.strptime(request.form.get('starts') or '', '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Date de session invalide.', 'danger')
            return redirect(url_for('ent.training'))
        link = (request.form.get('link') or '').strip()
        if link and not link.lower().startswith(('http://', 'https://')):
            link = 'https://' + link
        if title:
            db.session.add(LiveSession(org_id=current_user.org_id, title=title[:200], description=(request.form.get('description') or '')[:2000],
                                       starts_at=starts, link=link[:400], created_by=current_user.id))
            db.session.commit()
            flash('Session planifiée.', 'success')
        return redirect(url_for('ent.training'))

    # ------------------------------------------------------------------ messagerie
    @bp.route('/messages')
    @org_required
    def messages_page():
        return render_template('ent_messages.html', org=my_org(), channel=request.args.get('canal') if request.args.get('canal') in ('support', 'team') else 'support')

    def msg_dict(m):
        return {'id': m.id, 'author': m.author, 'staff': bool(m.from_staff), 'body': m.body, 'mine': m.user_id == current_user.id,
                'at': m.created_at.strftime('%d/%m %H:%M')}

    @bp.route('/api/messages', methods=['GET', 'POST'])
    @login_required
    def api_messages():
        if current_user.is_admin and request.values.get('org', '').isdigit():
            oid, staff = int(request.values['org']), True
        elif getattr(current_user, 'account_type', None) == 'entreprise' and current_user.org_id:
            oid, staff = current_user.org_id, False
        else:
            abort(403)
        ch = request.values.get('channel') or (request.get_json(silent=True) or {}).get('channel')
        if ch not in ('support', 'team') or (staff and ch == 'team'):
            abort(400)
        if request.method == 'POST':
            body = ((request.get_json(silent=True) or {}).get('body') or '').strip()[:2000]
            if not body:
                return jsonify({'ok': False}), 400
            m = Message(org_id=oid, channel=ch, user_id=current_user.id, author=name_of(current_user) if not staff else 'Équipe DataEcon.Ci',
                        from_staff=staff, body=body)
            db.session.add(m)
            db.session.commit()
            if ch == 'support' and not staff:
                staff_notify('Nouveau message entreprise', '<p>%s (%s) : %s</p>' % (name_of(current_user), Organization.query.get(oid).name, body[:500]))
            return jsonify({'ok': True, 'message': msg_dict(m)})
        after = int(request.args.get('after') or 0)
        q = Message.query.filter(Message.org_id == oid, Message.channel == ch, Message.id > after).order_by(Message.id)
        items = q.limit(200).all() if after else list(reversed(Message.query.filter(Message.org_id == oid, Message.channel == ch).order_by(Message.id.desc()).limit(100).all()))
        if items:
            mark_read(('support:%d' % oid) if staff else ch, current_user.id, items[-1].id)
        return jsonify({'messages': [msg_dict(m) for m in items]})

    # ------------------------------------------------------------------ demandes de services
    @bp.route('/demandes', methods=['GET', 'POST'])
    @org_required
    def requests_page():
        oid = current_user.org_id
        if request.method == 'POST':
            kind = request.form.get('kind')
            title = (request.form.get('title') or '').strip()
            desc = (request.form.get('description') or '').strip()
            if kind not in KINDS_DEMANDE or not title or not desc:
                flash('Complétez le type, le titre et la description de la demande.', 'danger')
            else:
                r = ServiceRequest(org_id=oid, user_id=current_user.id, kind=kind, title=title[:200], description=desc[:5000])
                db.session.add(r)
                db.session.add(Message(org_id=oid, channel='support', user_id=current_user.id, author=name_of(current_user), from_staff=False,
                                       body='Nouvelle demande (%s) : %s' % (KINDS_DEMANDE[kind], title)))
                db.session.commit()
                staff_notify('Nouvelle demande de service', '<p>%s : %s (%s)</p><p>%s</p>' % (my_org().name, title, KINDS_DEMANDE[kind], desc[:800]))
                flash('Demande envoyée. Nous vous répondons dans la messagerie.', 'success')
            return redirect(url_for('ent.requests_page'))
        items = ServiceRequest.query.filter_by(org_id=oid).order_by(ServiceRequest.created_at.desc()).all()
        return render_template('ent_requests.html', items=items, KINDS=KINDS_DEMANDE, STATUTS=STATUTS_DEMANDE,
                               kind=request.args.get('type') if request.args.get('type') in KINDS_DEMANDE else 'formation')

    # ------------------------------------------------------------------ tâches
    @bp.route('/taches')
    @org_required
    def tasks():
        oid = current_user.org_id
        mem = members(oid)
        by = {s: [] for s, _ in STATUTS_TACHE}
        for t in Task.query.filter_by(org_id=oid).order_by(Task.due_date.is_(None), Task.due_date, Task.id).all():
            by.setdefault(t.status, []).append(t)
        names = {u.id: name_of(u) for u in mem}
        return render_template('ent_tasks.html', by=by, STATUTS=STATUTS_TACHE, mem=mem, names=names, today=date.today())

    @bp.route('/taches/creer', methods=['POST'])
    @org_required
    def task_create():
        title = (request.form.get('title') or '').strip()
        if title:
            a = request.form.get('assignee')
            u = User.query.filter_by(id=int(a), org_id=current_user.org_id).first() if a and a.isdigit() else None
            due = None
            try:
                due = datetime.strptime(request.form.get('due') or '', '%Y-%m-%d').date()
            except ValueError:
                pass
            db.session.add(Task(org_id=current_user.org_id, title=title[:200], description=(request.form.get('description') or '')[:2000],
                                assignee_id=u.id if u else None, due_date=due, created_by=current_user.id))
            db.session.commit()
        return redirect(url_for('ent.tasks'))

    @bp.route('/taches/<int:tid>/statut', methods=['POST'])
    @org_required
    def task_status(tid):
        t = Task.query.filter_by(id=tid, org_id=current_user.org_id).first_or_404()
        s = request.form.get('status') or (request.get_json(silent=True) or {}).get('status')
        if s in dict(STATUTS_TACHE):
            t.status = s
            db.session.commit()
        if request.is_json:
            return jsonify({'ok': True})
        return redirect(url_for('ent.tasks'))

    @bp.route('/taches/<int:tid>/supprimer', methods=['POST'])
    @org_required
    def task_delete(tid):
        t = Task.query.filter_by(id=tid, org_id=current_user.org_id).first_or_404()
        db.session.delete(t)
        db.session.commit()
        return redirect(url_for('ent.tasks'))

    # ------------------------------------------------------------------ documents
    def doc_dir(oid):
        d = os.path.join(app.config.get('UPLOAD_FOLDER', '/app/data'), 'org_files', str(oid))
        os.makedirs(d, exist_ok=True)
        return d

    @bp.route('/documents', methods=['GET', 'POST'])
    @org_required
    def documents():
        oid = current_user.org_id
        if request.method == 'POST':
            f = request.files.get('file')
            if not f or not f.filename:
                flash('Choisissez un fichier.', 'warning')
            else:
                name = secure_filename(f.filename) or 'document'
                ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
                data = f.read(MAX_DOC + 1)
                if ext not in EXT_DOCS:
                    flash('Type de fichier non autorisé.', 'danger')
                elif len(data) > MAX_DOC:
                    flash('Fichier trop volumineux (25 Mo maximum).', 'danger')
                else:
                    stored = uuid.uuid4().hex + '_' + name
                    with open(os.path.join(doc_dir(oid), stored), 'wb') as fh:
                        fh.write(data)
                    db.session.add(Document(org_id=oid, name=name[:200], stored=stored, size=len(data), uploaded_by=current_user.id))
                    db.session.commit()
                    flash('Document ajouté.', 'success')
            return redirect(url_for('ent.documents'))
        docs = Document.query.filter_by(org_id=oid).order_by(Document.created_at.desc()).all()
        names = {u.id: name_of(u) for u in members(oid)}
        return render_template('ent_docs.html', docs=docs, names=names)

    @bp.route('/documents/<int:did>')
    @org_required
    def document_get(did):
        d = Document.query.filter_by(id=did, org_id=current_user.org_id).first_or_404()
        return send_file(os.path.join(doc_dir(d.org_id), d.stored), as_attachment=True, download_name=d.name)

    @bp.route('/documents/<int:did>/supprimer', methods=['POST'])
    @org_required
    def document_delete(did):
        d = Document.query.filter_by(id=did, org_id=current_user.org_id).first_or_404()
        if d.uploaded_by != current_user.id and current_user.org_role not in ('owner', 'admin'):
            abort(403)
        try:
            os.remove(os.path.join(doc_dir(d.org_id), d.stored))
        except OSError:
            pass
        db.session.delete(d)
        db.session.commit()
        return redirect(url_for('ent.documents'))

    app.register_blueprint(bp)

    # ------------------------------------------------------------------ administration plateforme
    @app.route('/admin/entreprises')
    @staff_required
    def admin_entreprises():
        orgs = Organization.query.order_by(Organization.created_at.desc()).all()
        rows = []
        for o in orgs:
            rows.append({'org': o, 'n': User.query.filter_by(org_id=o.id).count(),
                         'open': ServiceRequest.query.filter(ServiceRequest.org_id == o.id, ServiceRequest.status.in_(['nouvelle', 'en_cours'])).count(),
                         'unread': unread('support:%d' % o.id, o.id, 'support', current_user.id)})
        return render_template('admin_entreprises.html', rows=rows)

    @app.route('/admin/entreprises/<int:oid>', methods=['GET', 'POST'])
    @staff_required
    def admin_entreprise(oid):
        org = Organization.query.get_or_404(oid)
        if request.method == 'POST':
            act = request.form.get('act')
            if act == 'request':
                r = ServiceRequest.query.filter_by(id=int(request.form.get('rid') or 0), org_id=oid).first()
                if r:
                    if request.form.get('status') in STATUTS_DEMANDE:
                        r.status = request.form['status']
                    r.admin_note = (request.form.get('note') or '')[:3000]
                    r.updated_at = _now()
                    db.session.commit()
                    flash('Demande mise à jour.', 'success')
            elif act == 'session':
                try:
                    starts = datetime.strptime(request.form.get('starts') or '', '%Y-%m-%dT%H:%M')
                    db.session.add(LiveSession(org_id=None if request.form.get('all') else oid, title=(request.form.get('title') or '')[:200],
                                               description=(request.form.get('description') or '')[:2000], starts_at=starts,
                                               link=(request.form.get('link') or '')[:400], created_by=current_user.id))
                    db.session.commit()
                    flash('Session planifiée.', 'success')
                except ValueError:
                    flash('Date invalide.', 'danger')
            return redirect(url_for('admin_entreprise', oid=oid))
        reqs = ServiceRequest.query.filter_by(org_id=oid).order_by(ServiceRequest.created_at.desc()).all()
        mem = members(oid)
        stats = {'forms': Form.query.filter_by(org_id=oid).count(),
                 'resp': FormResponse.query.filter(FormResponse.form_id.in_([f.id for f in Form.query.filter_by(org_id=oid).all()] or [0])).count(),
                 'datasets': OrgDataset.query.filter_by(org_id=oid).count(), 'dash': Dashboard.query.filter_by(org_id=oid).count(),
                 'tasks': Task.query.filter_by(org_id=oid).count(), 'docs': Document.query.filter_by(org_id=oid).count()}
        return render_template('admin_entreprise.html', org=org, mem=mem, reqs=reqs, stats=stats, STATUTS=STATUTS_DEMANDE,
                               KINDS=KINDS_DEMANDE, ROLES=ROLES)

    def migrate():
        from sqlalchemy import text
        for stmt in ('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS account_type VARCHAR(12) DEFAULT \'particulier\'',
                     'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS org_id INTEGER',
                     'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS org_role VARCHAR(10)',
                     'CREATE INDEX IF NOT EXISTS ix_user_org_id ON "user" (org_id)'):
            try:
                db.session.execute(text(stmt))
                db.session.commit()
            except Exception:
                db.session.rollback()

    app.config['migrer_entreprise'] = migrate
    return {'Organization': Organization, 'Form': Form, 'FormResponse': FormResponse, 'Task': Task}
