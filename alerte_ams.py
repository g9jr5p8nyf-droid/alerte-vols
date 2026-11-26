"""Alerte retour en stock : VIBRANT MOOD - PALETTE DE BLUSH (AMS Beauty).

Au 27/11/2026 à 0h35 : épuisée (prix Black Friday 18,45 € au lieu de 36,90 €).
Vérifie chaque minute. Dès qu'elle redevient disponible : un message 🚨🚨,
puis un rappel 10 minutes plus tard si elle l'est toujours. Si elle est de
nouveau épuisée puis revient, l'alerte repart.
Pour arrêter : supprimer ce fichier.
"""
import os
import time
import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
DOSSIER = os.path.dirname(os.path.abspath(__file__))
ETAT = os.path.join(DOSSIER, ".ams_dispo")  # existe = déjà signalée disponible
PRODUIT = "https://ams-beauty.com/products/palette-blush-essentials"
ENTETES = {"User-Agent": "Mozilla/5.0 (alerte personnelle; 1 visite/minute)"}


def envoyer(msg):
    if not TOKEN or not CHAT_ID:
        print("[Telegram non configuré] " + msg)
        return
    try:
        requests.post("https://api.telegram.org/bot" + TOKEN + "/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg}, timeout=20)
    except Exception as e:
        print("Erreur Telegram :", e)


def message(d, rappel=False):
    prix = "%.2f €" % (d["price"] / 100)
    if d.get("compare_at_price") and d["compare_at_price"] > d["price"]:
        prix += " au lieu de %.2f €" % (d["compare_at_price"] / 100)
    debut = "🔔 Rappel : " if rappel else "🚨🚨 "
    return (debut + "La palette VIBRANT MOOD est de nouveau disponible chez AMS Beauty ("
            + prix + ") ! Vas-y vite :\n" + PRODUIT)


def verifier():
    r = requests.get(PRODUIT + ".js", headers=ENTETES, timeout=20)
    if r.status_code != 200:
        return  # page retirée ou site en panne : rien à conclure
    d = r.json()
    if not d.get("available"):
        if os.path.exists(ETAT):
            os.remove(ETAT)  # de nouveau épuisée : on réarme l'alerte
        return
    if not os.path.exists(ETAT):
        envoyer(message(d))
        with open(ETAT, "w") as f:
            f.write("1")
    elif open(ETAT).read().strip() == "1" and time.time() - os.path.getmtime(ETAT) > 600:
        envoyer(message(d, rappel=True))
        with open(ETAT, "w") as f:
            f.write("2")


if __name__ == "__main__":
    verifier()
