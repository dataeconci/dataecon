# -*- coding: utf-8 -*-
"""
Examens de certification et certificats DataEcon.Ci

Règles :
- un examen par cours (outil + niveau) : 10 questions tirées au hasard dans la banque,
  options mélangées, durée limitée, note de passage 70 %
- 2 tentatives maximum ; après 2 échecs consécutifs, nouvelle tentative possible
  30 jours après le second échec
- la correction se fait uniquement côté serveur
- un certificat PDF (avec code unique et QR code) est délivré en cas de réussite
"""
import os
import json
import random
import secrets
from io import BytesIO
from datetime import datetime, timedelta

from flask import (render_template, redirect, url_for, flash, request, send_file,
                   abort)
from flask_login import login_required, current_user

OUTILS = {'python': 'Python', 'r': 'R', 'sql': 'SQL', 'tableau': 'Tableau'}
NIVEAUX = {'debutant': 'Débutant', 'intermediaire': 'Intermédiaire', 'avance': 'Avancé'}

NB_QUESTIONS = 10
DUREE_MIN = 20
NOTE_PASSAGE = 70          # pourcentage
MAX_TENTATIVES = 2
BLOCAGE_JOURS = 30

EXAM_DIR = os.path.join(os.path.dirname(__file__), 'data', 'exams')


# ---------------------------------------------------------------- logique pure
def etat_tentatives(tentatives, maintenant=None):
    """
    tentatives : liste de dicts {started_at, submitted_at, passed} (soumises, ordre quelconque).
    Retourne {'restantes': int, 'bloque_jusqu_au': datetime|None, 'bloque': bool, 'echecs': int}
    Un cycle = 2 échecs ; le verrou dure 30 jours à partir de la soumission du 2e échec ;
    une fois le verrou levé, le compteur repart à zéro.
    """
    maintenant = maintenant or datetime.utcnow()
    echecs = 0
    verrou = None
    for t in sorted(tentatives, key=lambda x: x['started_at']):
        if verrou and t['started_at'] >= verrou:
            echecs, verrou = 0, None
        if t.get('passed'):
            continue
        echecs += 1
        if echecs >= MAX_TENTATIVES:
            verrou = t['submitted_at'] + timedelta(days=BLOCAGE_JOURS)
    if verrou and maintenant >= verrou:
        echecs, verrou = 0, None
    bloque = bool(verrou and maintenant < verrou)
    return {
        'restantes': 0 if bloque else max(0, MAX_TENTATIVES - echecs),
        'bloque_jusqu_au': verrou if bloque else None,
        'bloque': bloque,
        'echecs': echecs,
    }


def charger_banque(outil, niveau):
    chemin = os.path.join(EXAM_DIR, f'{outil}_{niveau}.json')
    if not os.path.exists(chemin):
        return []
    with open(chemin, 'r', encoding='utf-8') as f:
        return json.load(f).get('questions', [])


def tirer_questions(banque, n=NB_QUESTIONS):
    """Tire n questions et mélange les options. Retourne la liste de dicts stockés en base."""
    choix = random.sample(banque, min(n, len(banque)))
    sortie = []
    for q in choix:
        ordre = list(range(len(q['options'])))
        random.shuffle(ordre)
        sortie.append({'id': q['id'], 'ordre': ordre})
    return sortie


def corriger(banque, tirage, reponses):
    """reponses : {question_id: index affiché choisi}. Retourne (score_pct, bonnes, details)."""
    par_id = {q['id']: q for q in banque}
    bonnes = 0
    details = []
    for t in tirage:
        q = par_id.get(t['id'])
        if not q:
            continue
        ordre = t['ordre']
        bonne_pos = ordre.index(q['correct'])
        choisi = reponses.get(t['id'])
        ok = choisi is not None and choisi == bonne_pos
        bonnes += 1 if ok else 0
        details.append({
            'theme': q.get('theme', ''),
            'question': q['question'],
            'code': q.get('code', ''),
            'options': [q['options'][i] for i in ordre],
            'choisi': choisi,
            'bonne': bonne_pos,
            'ok': ok,
            'explication': q.get('explication', ''),
        })
    total = max(1, len(details))
    return round(100.0 * bonnes / total, 1), bonnes, details


# ---------------------------------------------------------------- PDF
def generer_pdf(nom_complet, outil_nom, niveau_nom, score, date_emission, code, url_verif):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.colors import HexColor, white
    from reportlab.pdfgen import canvas
    from reportlab.graphics.barcode import qr
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderPDF

    navy, steel, gold = HexColor('#0b2a4a'), HexColor('#1f5f99'), HexColor('#c2a15a')
    W, H = landscape(A4)
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))
    c.setTitle(f'Certificat DataEcon.Ci - {outil_nom} {niveau_nom}')
    c.setAuthor('DataEcon.Ci')

    c.setFillColor(HexColor('#fbfaf6'))
    c.rect(0, 0, W, H, stroke=0, fill=1)
    # bandeau latéral
    c.setFillColor(navy)
    c.rect(0, 0, 56, H, stroke=0, fill=1)
    c.setFillColor(gold)
    c.rect(56, 0, 5, H, stroke=0, fill=1)
    # cadre
    c.setStrokeColor(gold)
    c.setLineWidth(1.2)
    c.rect(84, 28, W - 112, H - 56, stroke=1, fill=0)
    c.setStrokeColor(navy)
    c.setLineWidth(0.5)
    c.rect(90, 34, W - 124, H - 68, stroke=1, fill=0)

    cx = 61 + (W - 61) / 2
    c.setFillColor(navy)
    c.setFont('Helvetica-Bold', 13)
    c.drawCentredString(cx, H - 78, 'DATAECON.CI')
    c.setFillColor(gold)
    c.setLineWidth(1)
    c.setStrokeColor(gold)
    c.line(cx - 40, H - 88, cx + 40, H - 88)

    c.setFillColor(navy)
    c.setFont('Times-Bold', 38)
    c.drawCentredString(cx, H - 142, 'CERTIFICAT DE RÉUSSITE')
    c.setFont('Helvetica', 12)
    c.setFillColor(HexColor('#475569'))
    c.drawCentredString(cx, H - 172, 'Il est certifié que')

    # nom (réduit si trop long)
    taille = 34
    c.setFont('Times-BoldItalic', taille)
    while c.stringWidth(nom_complet, 'Times-BoldItalic', taille) > W - 260 and taille > 16:
        taille -= 2
    c.setFont('Times-BoldItalic', taille)
    c.setFillColor(steel)
    c.drawCentredString(cx, H - 218, nom_complet)
    c.setStrokeColor(gold)
    c.line(cx - 190, H - 230, cx + 190, H - 230)

    c.setFillColor(HexColor('#475569'))
    c.setFont('Helvetica', 12)
    c.drawCentredString(cx, H - 258, 'a validé avec succès l\'examen de certification du cours')
    c.setFillColor(navy)
    c.setFont('Helvetica-Bold', 22)
    c.drawCentredString(cx, H - 292, f'{outil_nom} - niveau {niveau_nom}')
    c.setFillColor(HexColor('#475569'))
    c.setFont('Helvetica', 12)
    c.drawCentredString(cx, H - 320, f'avec une note de {score:.0f} % (seuil de réussite : {NOTE_PASSAGE} %)')

    # pied : date, code, QR
    c.setFont('Helvetica', 10)
    c.setFillColor(HexColor('#475569'))
    c.drawString(120, 86, 'Date de délivrance')
    c.setFont('Helvetica-Bold', 12)
    c.setFillColor(navy)
    c.drawString(120, 70, date_emission.strftime('%d/%m/%Y'))

    c.setFont('Helvetica', 10)
    c.setFillColor(HexColor('#475569'))
    c.drawCentredString(cx, 86, 'Code de vérification')
    c.setFont('Courier-Bold', 13)
    c.setFillColor(navy)
    c.drawCentredString(cx, 70, code)
    c.setFont('Helvetica', 8)
    c.setFillColor(HexColor('#64748b'))
    c.drawCentredString(cx, 54, url_verif)

    # signature manuscrite du fondateur
    sig_path = os.path.join(os.path.dirname(__file__), 'static', 'images', 'signature.png')
    sx = W - 330
    c.setStrokeColor(navy)
    c.setLineWidth(0.6)
    c.line(sx - 70, 120, sx + 70, 120)
    if os.path.exists(sig_path):
        from reportlab.lib.utils import ImageReader
        img = ImageReader(sig_path)
        iw, ih = img.getSize()
        hh = 68
        ww = hh * iw / ih
        c.drawImage(img, sx - ww / 2, 122, width=ww, height=hh, mask='auto')
    c.setFont('Helvetica-Bold', 9)
    c.setFillColor(navy)
    c.drawCentredString(sx, 108, 'Innocent GAN KADOH')
    c.setFont('Helvetica', 8)
    c.setFillColor(HexColor('#64748b'))
    c.drawCentredString(sx, 97, 'DataEcon.Ci')

    widget = qr.QrCodeWidget(url_verif)
    b = widget.getBounds()
    taille_qr = 74
    d = Drawing(taille_qr, taille_qr, transform=[taille_qr / (b[2] - b[0]), 0, 0, taille_qr / (b[3] - b[1]), 0, 0])
    d.add(widget)
    renderPDF.draw(d, c, W - 190, 44)
    c.setFont('Helvetica', 7)
    c.drawCentredString(W - 153, 38, 'Scanner pour vérifier')

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


# ---------------------------------------------------------------- enregistrement
def init_certification(app, db, User):

    class ExamAttempt(db.Model):
        __tablename__ = 'exam_attempt'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
        outil = db.Column(db.String(20), nullable=False)
        niveau = db.Column(db.String(20), nullable=False)
        started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
        submitted_at = db.Column(db.DateTime)
        score = db.Column(db.Float)
        passed = db.Column(db.Boolean, default=False)
        tirage = db.Column(db.Text, nullable=False)       # JSON [{id, ordre}]
        reponses = db.Column(db.Text)                     # JSON {id: index}
        details = db.Column(db.Text)                      # JSON corrigé

    class Certificate(db.Model):
        __tablename__ = 'certificate'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
        outil = db.Column(db.String(20), nullable=False)
        niveau = db.Column(db.String(20), nullable=False)
        code = db.Column(db.String(24), unique=True, nullable=False, index=True)
        score = db.Column(db.Float, nullable=False)
        holder_name = db.Column(db.String(200), nullable=False)
        issued_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
        __table_args__ = (db.UniqueConstraint('user_id', 'outil', 'niveau', name='uq_cert_user_course'),)

    app.config['ExamAttempt'] = ExamAttempt
    app.config['Certificate'] = Certificate

    # ----- helpers
    def _valide(outil, niveau):
        return outil in OUTILS and niveau in NIVEAUX

    def _acces(niveau):
        return current_user.has_access(NIVEAUX[niveau])

    def _nom(user):
        n = f'{user.first_name or ""} {user.last_name or ""}'.strip()
        return n or user.username

    def _finaliser(att, reponses):
        banque = charger_banque(att.outil, att.niveau)
        tirage = json.loads(att.tirage)
        score, bonnes, details = corriger(banque, tirage, reponses)
        att.submitted_at = datetime.utcnow()
        att.reponses = json.dumps(reponses)
        att.score = score
        att.passed = score >= NOTE_PASSAGE
        att.details = json.dumps(details, ensure_ascii=False)
        if att.passed:
            deja = Certificate.query.filter_by(user_id=att.user_id, outil=att.outil, niveau=att.niveau).first()
            if not deja:
                user = db.session.get(User, att.user_id)
                db.session.add(Certificate(
                    user_id=att.user_id, outil=att.outil, niveau=att.niveau,
                    code='DEC-' + secrets.token_hex(5).upper(),
                    score=score, holder_name=_nom(user)))
        db.session.commit()

    def _expirer_ouvertes(user_id, outil=None, niveau=None):
        """Clôture les tentatives ouvertes dont le temps est écoulé (comptées comme soumises)."""
        q = ExamAttempt.query.filter_by(user_id=user_id, submitted_at=None)
        if outil:
            q = q.filter_by(outil=outil, niveau=niveau)
        limite = datetime.utcnow() - timedelta(minutes=DUREE_MIN + 1)
        for att in q.all():
            if att.started_at < limite:
                _finaliser(att, json.loads(att.reponses) if att.reponses else {})

    def _etat(user_id, outil, niveau):
        soumises = ExamAttempt.query.filter(
            ExamAttempt.user_id == user_id, ExamAttempt.outil == outil,
            ExamAttempt.niveau == niveau, ExamAttempt.submitted_at.isnot(None)).all()
        return etat_tentatives([
            {'started_at': a.started_at, 'submitted_at': a.submitted_at, 'passed': a.passed}
            for a in soumises])

    # ----- hub
    @app.route('/certification')
    @login_required
    def certification_hub():
        _expirer_ouvertes(current_user.id)
        certs = {(c.outil, c.niveau): c for c in Certificate.query.filter_by(user_id=current_user.id).all()}
        lignes = []
        for o, onom in OUTILS.items():
            niveaux = []
            for n, nnom in NIVEAUX.items():
                if not charger_banque(o, n):
                    continue
                etat = _etat(current_user.id, o, n)
                niveaux.append({'code': n, 'nom': nnom, 'cert': certs.get((o, n)), 'etat': etat,
                                'acces': _acces(n)})
            lignes.append({'code': o, 'nom': onom, 'niveaux': niveaux})
        return render_template('certification_hub.html', lignes=lignes, regles=_regles())

    def _regles():
        return {'nb': NB_QUESTIONS, 'duree': DUREE_MIN, 'seuil': NOTE_PASSAGE,
                'essais': MAX_TENTATIVES, 'jours': BLOCAGE_JOURS}

    # ----- page d'un examen (règles + démarrage)
    @app.route('/certification/<outil>/<niveau>')
    @login_required
    def certification_course(outil, niveau):
        if not _valide(outil, niveau):
            abort(404)
        _expirer_ouvertes(current_user.id, outil, niveau)
        cert = Certificate.query.filter_by(user_id=current_user.id, outil=outil, niveau=niveau).first()
        ouverte = ExamAttempt.query.filter_by(user_id=current_user.id, outil=outil, niveau=niveau,
                                              submitted_at=None).first()
        historique = ExamAttempt.query.filter(
            ExamAttempt.user_id == current_user.id, ExamAttempt.outil == outil,
            ExamAttempt.niveau == niveau, ExamAttempt.submitted_at.isnot(None)
        ).order_by(ExamAttempt.submitted_at.desc()).all()
        return render_template('certification_course.html', outil=outil, outil_nom=OUTILS[outil],
                               niveau=niveau, niveau_nom=NIVEAUX[niveau], cert=cert, ouverte=ouverte,
                               etat=_etat(current_user.id, outil, niveau), acces=_acces(niveau),
                               historique=historique, regles=_regles(),
                               disponible=bool(charger_banque(outil, niveau)))

    @app.route('/certification/<outil>/<niveau>/demarrer', methods=['POST'])
    @login_required
    def certification_start(outil, niveau):
        if not _valide(outil, niveau):
            abort(404)
        if not _acces(niveau):
            flash('Cet examen nécessite un abonnement Standard ou Premium.', 'warning')
            return redirect(url_for('subscription'))
        if Certificate.query.filter_by(user_id=current_user.id, outil=outil, niveau=niveau).first():
            flash('Vous avez déjà obtenu ce certificat.', 'info')
            return redirect(url_for('certification_course', outil=outil, niveau=niveau))
        banque = charger_banque(outil, niveau)
        if not banque:
            flash('Cet examen n\'est pas encore disponible.', 'warning')
            return redirect(url_for('certification_hub'))
        _expirer_ouvertes(current_user.id, outil, niveau)
        ouverte = ExamAttempt.query.filter_by(user_id=current_user.id, outil=outil, niveau=niveau,
                                              submitted_at=None).first()
        if ouverte:
            return redirect(url_for('certification_exam', attempt_id=ouverte.id))
        etat = _etat(current_user.id, outil, niveau)
        if etat['bloque']:
            flash('Vous avez épuisé vos deux tentatives. Nouvelle tentative possible le '
                  + etat['bloque_jusqu_au'].strftime('%d/%m/%Y') + '.', 'warning')
            return redirect(url_for('certification_course', outil=outil, niveau=niveau))
        att = ExamAttempt(user_id=current_user.id, outil=outil, niveau=niveau,
                          tirage=json.dumps(tirer_questions(banque)))
        db.session.add(att)
        db.session.commit()
        return redirect(url_for('certification_exam', attempt_id=att.id))

    def _ma_tentative(attempt_id):
        att = db.session.get(ExamAttempt, attempt_id)
        if not att or att.user_id != current_user.id:
            abort(404)
        return att

    @app.route('/certification/examen/<int:attempt_id>')
    @login_required
    def certification_exam(attempt_id):
        att = _ma_tentative(attempt_id)
        if att.submitted_at:
            return redirect(url_for('certification_result', attempt_id=att.id))
        reste = DUREE_MIN * 60 - int((datetime.utcnow() - att.started_at).total_seconds())
        if reste <= 0:
            _finaliser(att, json.loads(att.reponses) if att.reponses else {})
            flash('Le temps imparti est écoulé : l\'examen a été clôturé.', 'warning')
            return redirect(url_for('certification_result', attempt_id=att.id))
        banque = {q['id']: q for q in charger_banque(att.outil, att.niveau)}
        questions = []
        for t in json.loads(att.tirage):
            q = banque[t['id']]
            questions.append({'id': q['id'], 'theme': q.get('theme', ''), 'question': q['question'],
                              'code': q.get('code', ''), 'options': [q['options'][i] for i in t['ordre']]})
        return render_template('certification_exam.html', att=att, questions=questions, reste=reste,
                               outil_nom=OUTILS[att.outil], niveau_nom=NIVEAUX[att.niveau],
                               regles=_regles())

    @app.route('/certification/examen/<int:attempt_id>/soumettre', methods=['POST'])
    @login_required
    def certification_submit(attempt_id):
        att = _ma_tentative(attempt_id)
        if att.submitted_at:
            return redirect(url_for('certification_result', attempt_id=att.id))
        reponses = {}
        for t in json.loads(att.tirage):
            v = request.form.get('q_' + t['id'])
            if v is not None and v.isdigit() and int(v) < len(t['ordre']):
                reponses[t['id']] = int(v)
        # tolérance d'une minute pour la latence réseau
        _finaliser(att, reponses)
        return redirect(url_for('certification_result', attempt_id=att.id))

    @app.route('/certification/resultat/<int:attempt_id>')
    @login_required
    def certification_result(attempt_id):
        att = _ma_tentative(attempt_id)
        if not att.submitted_at:
            return redirect(url_for('certification_exam', attempt_id=att.id))
        cert = Certificate.query.filter_by(user_id=att.user_id, outil=att.outil, niveau=att.niveau).first()
        return render_template('certification_result.html', att=att, details=json.loads(att.details or '[]'),
                               cert=cert, etat=_etat(att.user_id, att.outil, att.niveau),
                               outil_nom=OUTILS[att.outil], niveau_nom=NIVEAUX[att.niveau],
                               regles=_regles())

    # ----- certificat
    @app.route('/certificat/<code>/telecharger')
    @login_required
    def certificat_download(code):
        cert = Certificate.query.filter_by(code=code).first_or_404()
        if cert.user_id != current_user.id and not current_user.is_admin:
            abort(404)
        url_verif = url_for('certificat_verify', code=cert.code, _external=True)
        pdf = generer_pdf(cert.holder_name, OUTILS[cert.outil], NIVEAUX[cert.niveau], cert.score,
                          cert.issued_at, cert.code, url_verif)
        return send_file(pdf, mimetype='application/pdf', as_attachment=True,
                         download_name=f'certificat_dataecon_{cert.outil}_{cert.niveau}.pdf')

    @app.route('/certificat/verifier', methods=['GET', 'POST'])
    @app.route('/certificat/verifier/<code>')
    def certificat_verify(code=None):
        if request.method == 'POST':
            code = (request.form.get('code') or '').strip().upper()
            return redirect(url_for('certificat_verify', code=code)) if code else redirect(url_for('certificat_verify'))
        cert = None
        if code:
            cert = Certificate.query.filter_by(code=code.strip().upper()).first()
        return render_template('certification_verify.html', code=code, cert=cert,
                               outils=OUTILS, niveaux=NIVEAUX)

    return ExamAttempt, Certificate
