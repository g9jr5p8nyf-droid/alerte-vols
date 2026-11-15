"""Test de l'alerte : prévient sur Telegram quand une vente Showroomprivé
attendue ouvre (Burberry, Planète Sauvage).

Chaque vente a un numéro et une page publique /link/sale/<numéro> :
- vente ouverte  -> la page de la vente (ventep.aspx), avec son nom dans og:title
- vente à venir  -> renvoi vers l'accueil avec « mes=2 »
- numéro inconnu -> renvoi vers l'accueil avec « mes=1 »
On surveille les numéros récents et on lit le nom des ventes qui ouvrent.
"""
import os
import re
import html
import unicodedata
from concurrent.futures import ThreadPoolExecutor
import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

MOTS = ["burberry", "planete sauvage"]
PREMIER, DERNIER = 160875, 161060  # numéros des ventes récentes et à venir (15/11/2026)
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130 Safari/537.36")
DOSSIER = os.path.dirname(os.path.abspath(__file__))
DEJA_ENVOYE = os.path.join(DOSSIER, ".srp_envoye")  # numéros déjà signalés
CONNUES = os.path.join(DOSSIER, ".srp_connues")      # ventes déjà ouvertes, inutile de les relire


def simplifier(texte):
    texte = unicodedata.normalize("NFKD", str(texte or ""))
    return "".join(c for c in texte if not unicodedata.combining(c)).lower()


def lire(fichier):
    try:
        return set(open(fichier).read().split())
    except OSError:
        return set()


def envoyer(msg):
    if not TOKEN or not CHAT_ID:
        print("[Telegram non configuré] " + msg)
        return
    try:
        requests.post("https://api.telegram.org/bot" + TOKEN + "/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg}, timeout=20)
    except Exception as e:
        print("Erreur Telegram :", e)


def examiner(numero):
    url = "https://www.showroomprive.com/link/sale/%d" % numero
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    except Exception:
        return numero, None, None
    if "ventep.aspx" not in r.url and "minisitep.aspx" not in r.url:
        return numero, None, None  # pas (encore) ouverte
    m = re.search(r'og:title" content="([^"]*)', r.text)
    nom = html.unescape(m.group(1)).replace(" sur Showroomprive.com", "") if m else ""
    return numero, nom, url


def verifier():
    envoyes, connues = lire(DEJA_ENVOYE), lire(CONNUES)
    a_voir = [n for n in range(PREMIER, DERNIER + 1) if str(n) not in connues]
    with ThreadPoolExecutor(max_workers=8) as pool:
        resultats = list(pool.map(examiner, a_voir))

    ouvertes = [(n, nom, url) for n, nom, url in resultats if url]
    trouvees = [(n, nom, url) for n, nom, url in ouvertes
                if any(mot in simplifier(nom) for mot in MOTS)]
    print("Showroomprivé : %d numéros vus, %d ventes ouvertes, attendues : %s"
          % (len(a_voir), len(ouvertes), [nom for _, nom, _ in trouvees] or "aucune"))

    for n, nom, url in trouvees:
        if str(n) not in envoyes:
            envoyer("🛍️ Test réussi ! La vente « " + nom + " » vient d'ouvrir sur "
                    "Showroomprivé :\n" + url)
            envoyes.add(str(n))
    # On ne relit plus les ventes ouvertes qui ne nous intéressent pas
    connues |= {str(n) for n, nom, url in ouvertes if str(n) not in
                {str(t[0]) for t in trouvees}}
    open(DEJA_ENVOYE, "w").write("\n".join(sorted(envoyes)))
    open(CONNUES, "w").write("\n".join(sorted(connues)))


if __name__ == "__main__":
    verifier()
