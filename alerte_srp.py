"""Test de l'alerte : prévient sur Telegram quand la vente Planète Sauvage
apparaît sur Showroomprivé.

On interroge la recherche publique du site (la même que sa barre de
recherche), qui contient la liste des ventes en cours.
"""
import os
import unicodedata
import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

RECHERCHE = "https://6NMNDPDXJX-dsn.algolia.net/1/indexes/srp_sales_fr/query"
ENTETES = {
    "X-Algolia-Application-Id": "6NMNDPDXJX",
    "X-Algolia-API-Key": "9627c7d92b37dd5a5b7598b323a3cdb7",  # clé publique du site
    "Referer": "https://www.showroomprive.com/",
}
CHERCHE = "planete sauvage"
# Évite de renvoyer la même alerte à chaque tour (toutes les 5 minutes)
DEJA_ENVOYE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".srp_envoye")


def simplifier(texte):
    texte = unicodedata.normalize("NFKD", str(texte or ""))
    return "".join(c for c in texte if not unicodedata.combining(c)).lower()


def envoyer(msg):
    if not TOKEN or not CHAT_ID:
        print("[Telegram non configuré] " + msg)
        return
    try:
        requests.post("https://api.telegram.org/bot" + TOKEN + "/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg}, timeout=20)
    except Exception as e:
        print("Erreur Telegram :", e)


def verifier():
    try:
        r = requests.post(RECHERCHE, headers=ENTETES, timeout=20,
                          json={"query": "sauvage", "hitsPerPage": 20})
        ventes = r.json().get("hits", [])
    except Exception as e:
        print("Showroomprivé : erreur de lecture :", e)
        return

    trouvees = [v for v in ventes
                if CHERCHE in simplifier(v.get("label"))
                or any(CHERCHE in simplifier(b) for b in v.get("brands") or [])]
    print("Showroomprivé : vente Planète Sauvage en ligne :", bool(trouvees))

    if trouvees and not os.path.exists(DEJA_ENVOYE):
        v = trouvees[0]
        envoyer("🦁 Test réussi ! La vente « " + str(v.get("label")) + " » est en "
                "ligne sur Showroomprivé :\n" + str(v.get("saleUrl")))
        open(DEJA_ENVOYE, "w").close()


if __name__ == "__main__":
    verifier()
