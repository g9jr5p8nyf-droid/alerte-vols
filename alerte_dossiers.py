"""Alerte précoce : nouveaux fichiers déposés sur voyage.benin.bj.

Le dossier public https://voyage.benin.bj/assets/ affiche la liste de ses
fichiers avec leur date. Avant de mettre en ligne la vraie page des vols,
l'équipe devra sans doute y déposer de nouvelles images (affiche, dates,
logos des compagnies...). Un nouveau fichier ou une date qui change peut donc
arriver avant que la page d'accueil elle-même ne change.

Au 26/11/2026, tous les fichiers datent du 07/08/2026.
Vérifie toutes les 5 minutes et envoie un message « ⚠️ » une seule fois
pour chaque nouvel état du dossier.
"""
import os
import re
import time
import hashlib
import html
import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
DOSSIER = os.path.dirname(os.path.abspath(__file__))
DERNIERE = os.path.join(DOSSIER, ".dossiers_derniere")
ENVOYES = os.path.join(DOSSIER, ".dossiers_envoyes")

URL_DOSSIER = "https://voyage.benin.bj/assets/"
# Contenu connu au 26/11/2026 : (nom, date)
CONNUS = {
    ("bg-ganvie.webp", "2026-08-07 17:12"),
    ("bg-illustration.webp", "2026-08-07 17:12"),
    ("bg-nikki.webp", "2026-08-07 17:12"),
    ("destinations/", "2026-08-07 17:12"),
    ("favicon.webp", "2026-08-07 17:12"),
    ("hero-bg.webp", "2026-08-07 17:12"),
    ("illustration.jpg", "2026-08-07 17:12"),
    ("logo/", "2026-08-07 17:12"),
}
INTERVALLE = 300


def envoyer(msg):
    if not TOKEN or not CHAT_ID:
        print("[Telegram non configuré] " + msg)
        return
    try:
        requests.post("https://api.telegram.org/bot" + TOKEN + "/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg}, timeout=20)
    except Exception as e:
        print("Erreur Telegram :", e)


def lire_dossier():
    r = requests.get(URL_DOSSIER, timeout=20)
    if r.status_code != 200 or "Index of /assets" not in r.text:
        return None  # dossier masqué ou site en panne : rien à conclure
    lignes = re.findall(
        r'<a href="([^"?/][^"]*)">.*?</a>\s*</td><td align="right">([^<]*)</td>',
        r.text)
    return {(html.unescape(n), d.strip()) for n, d in lignes}


def verifier():
    try:
        if time.time() - os.path.getmtime(DERNIERE) < INTERVALLE:
            return
    except OSError:
        pass
    open(DERNIERE, "w").close()

    contenu = lire_dossier()
    if not contenu or contenu == CONNUS:
        return
    empreinte = hashlib.sha256(repr(sorted(contenu)).encode()).hexdigest()[:16]
    try:
        deja = open(ENVOYES).read().split()
    except OSError:
        deja = []
    if empreinte in deja:
        return

    nouveaux = sorted(contenu - CONNUS)
    disparus = sorted(n for n, _ in CONNUS - contenu if n not in {m for m, _ in contenu})
    detail = ""
    if nouveaux:
        detail += "\nNouveau ou modifié : " + ", ".join(n + " (" + d + ")" for n, d in nouveaux[:10])
    if disparus:
        detail += "\nSupprimé : " + ", ".join(disparus[:10])
    envoyer("⚠️ De nouveaux fichiers ont été déposés sur voyage.benin.bj : "
            "la page des vols est peut-être en préparation." + detail +
            "\nCe n'est pas encore l'ouverture : attends l'alerte 🚨🚨.\n" + URL_DOSSIER)
    with open(ENVOYES, "a") as f:
        f.write(empreinte + "\n")
