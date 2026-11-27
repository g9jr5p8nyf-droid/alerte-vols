"""Alerte « deuxième vague » (après l'ouverture du 27/11/2026).

La billetterie est ouverte mais complète. On ne peut pas voir les places une
par une (le service des places refuse les accès automatiques). On surveille
donc ce qui annoncerait de nouvelles dates ou une nouvelle vente :
  - voyage.benin.bj change (nouvelle page, nouvelles dates) ;
  - nouveaux fichiers dans son dossier public (via alerte_dossiers) ;
  - la billetterie publie une nouvelle version de son site ;
  - la billetterie se ferme, ou rouvre après avoir été fermée ;
  - nouveaux certificats de sécurité (via alerte_certs).
Chaque changement est signalé une seule fois.
"""
import os
import re
import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
DOSSIER = os.path.dirname(os.path.abspath(__file__))
ENTETES = {"User-Agent": "Mozilla/5.0 (alerte personnelle; 1 visite/minute)"}

SITE_INFO = "https://voyage.benin.bj"
DATE_INFO_CONNUE = "Fri, 07 Aug 2026 17:12:31 GMT"
BILLETTERIE = "https://voyage.benintours.bj"
VERSION_CONNUE = "index-Ctt2UQh6.js"  # version mise en ligne le 27/11 à 11h48


def envoyer(msg):
    if not TOKEN or not CHAT_ID:
        print("[Telegram non configuré] " + msg)
        return
    try:
        requests.post("https://api.telegram.org/bot" + TOKEN + "/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg}, timeout=20)
    except Exception as e:
        print("Erreur Telegram :", e)


def memoire(nom, valeur=None):
    """Lit (ou écrit si valeur est donnée) une petite valeur gardée entre deux vérifications."""
    chemin = os.path.join(DOSSIER, ".alerte_vague_" + nom)
    if valeur is None:
        try:
            return open(chemin).read().strip()
        except OSError:
            return None
    with open(chemin, "w") as f:
        f.write(valeur)


def une_fois(nom, cle, msg):
    """Envoie msg seulement si cette valeur n'a jamais été signalée."""
    if memoire(nom) != cle:
        envoyer(msg)
        memoire(nom, cle)


def verifier_site_info():
    r = requests.get(SITE_INFO, headers=ENTETES, timeout=20)
    if r.status_code != 200:
        return
    date = r.headers.get("Last-Modified", "")
    if date and date != DATE_INFO_CONNUE:
        une_fois("info", date, "🚨 voyage.benin.bj vient d'être mis à jour : de nouvelles dates "
                 "ou une nouvelle vente sont peut-être annoncées. Va voir vite :\n" + SITE_INFO)


def verifier_billetterie():
    try:
        r = requests.get(BILLETTERIE, headers=ENTETES, timeout=20)
        statut = r.status_code
    except requests.RequestException:
        return
    if statut == 200:
        etat = "ouverte"
    elif statut == 401:
        etat = "fermee"
    else:
        return  # panne passagère : on ne conclut rien
    avant = memoire("etat")
    if avant is None:
        memoire("etat", etat)
    elif etat != avant:
        memoire("etat", etat)
        if etat == "fermee":
            envoyer("ℹ️ La billetterie voyage.benintours.bj est de nouveau fermée par mot de passe. "
                    "Je te préviens si elle rouvre (ça pourrait être une deuxième vague).")
        else:
            envoyer("🚨🚨 La billetterie voyage.benintours.bj vient de ROUVRIR ! Peut-être une "
                    "deuxième vague ou des places remises en vente. Vas-y vite :\n" + BILLETTERIE)

    if etat == "ouverte":
        m = re.search(r"/assets/(index-[^\"']+\.js)", r.text)
        if m and m.group(1) != VERSION_CONNUE:
            une_fois("version", m.group(1),
                     "⚠️ La billetterie a publié une nouvelle version de son site : de nouvelles "
                     "dates ou des places ont peut-être été ajoutées. Jette un œil :\n" + BILLETTERIE)


def verifier():
    for etape in (verifier_site_info, verifier_billetterie):
        try:
            etape()
        except Exception as e:
            print("Étape ignorée :", etape.__name__, e)
    for module in ("alerte_dossiers", "alerte_certs"):
        try:
            __import__(module).verifier()
        except Exception as e:
            print("Vérification ignorée :", module, e)


if __name__ == "__main__":
    verifier()
