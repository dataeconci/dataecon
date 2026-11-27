"""Éléments de finition professionnelle : pages légales, contact, erreurs, SEO, en-têtes de sécurité."""
import os
import time
from datetime import date
from flask import render_template, request, redirect, url_for, flash, session, Response, abort
from markupsafe import escape

PAGES = {
    'mentions-legales': ('Mentions légales', 'mentions'),
    'confidentialite': ('Politique de confidentialité', 'confidentialite'),
    'conditions': ("Conditions générales d'utilisation", 'conditions'),
}
CONTACT_EMAIL = os.environ.get('CONTACT_EMAIL', 'dataeconci@gmail.com')


def init_pro(app, notify=None):
    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
        resp.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        resp.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        resp.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=()')
        return resp

    @app.context_processor
    def _pro_ctx():
        return {'contact_email': CONTACT_EMAIL, 'annee': date.today().year,
                'site_url': request.url_root.rstrip('/')}

    def _err(code, titre, texte):
        def handler(e):
            return render_template('error.html', code=code, titre=titre, texte=texte), code
        return handler

    for code, titre, texte in [
        (403, 'Accès refusé', "Vous n'avez pas l'autorisation d'accéder à cette page."),
        (404, 'Page introuvable', "La page demandée n'existe pas ou a été déplacée."),
        (413, 'Fichier trop volumineux', "Le fichier envoyé dépasse la taille autorisée."),
        (429, 'Trop de requêtes', "Veuillez patienter quelques instants avant de réessayer."),
        (500, 'Erreur du service', "Une erreur est survenue de notre côté. Réessayez dans un instant."),
    ]:
        app.register_error_handler(code, _err(code, titre, texte))

    def _legal(slug):
        titre, tpl = PAGES[slug]
        return render_template('legal.html', titre=titre, tpl='legal/%s.html' % tpl, slug=slug)

    for slug in PAGES:
        app.add_url_rule('/' + slug, 'legal_' + slug.replace('-', '_'),
                         (lambda s=slug: _legal(s)))

    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        if request.method == 'POST':
            if request.form.get('website'):  # champ piège anti-robot
                return redirect(url_for('contact'))
            nom = (request.form.get('nom') or '').strip()[:120]
            email = (request.form.get('email') or '').strip()[:160]
            sujet = (request.form.get('sujet') or '').strip()[:160]
            msg = (request.form.get('message') or '').strip()[:4000]
            last = session.get('contact_ts', 0)
            if not nom or '@' not in email or len(msg) < 10:
                flash('Veuillez renseigner votre nom, une adresse e-mail valide et un message.', 'danger')
            elif time.time() - last < 60:
                flash('Veuillez patienter une minute avant un nouvel envoi.', 'warning')
            else:
                session['contact_ts'] = time.time()
                if notify:
                    try:
                        notify(os.environ.get('ADMIN_NOTIFY_EMAIL') or CONTACT_EMAIL, 'DataEcon.Ci',
                               'Contact : ' + (sujet or 'Nouveau message'),
                               '<p><b>De :</b> %s &lt;%s&gt;</p><p><b>Sujet :</b> %s</p><p>%s</p>'
                               % (escape(nom), escape(email), escape(sujet),
                                  escape(msg).replace('\n', '<br>')))
                    except Exception:
                        pass
                flash('Votre message a bien été envoyé. Nous vous répondrons rapidement.', 'success')
            return redirect(url_for('contact'))
        return render_template('contact.html')

    @app.route('/robots.txt')
    def robots():
        txt = ("User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /entreprise\nDisallow: /api\n"
               "Disallow: /dashboard\nDisallow: /profile\nSitemap: %s/sitemap.xml\n" % request.url_root.rstrip('/'))
        return Response(txt, mimetype='text/plain')

    @app.route('/sitemap.xml')
    def sitemap():
        base = request.url_root.rstrip('/')
        urls = ['/', '/about', '/carrieres', '/contact', '/login', '/register'] + ['/' + s for s in PAGES]
        body = ''.join('<url><loc>%s%s</loc></url>' % (base, u) for u in urls)
        return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>' % body,
                        mimetype='application/xml')
