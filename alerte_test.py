"""Test de bout en bout de l'alerte, contrôlé par toi.

Surveille le fichier test-alerte.txt de ton dépôt, en le lisant par internet
comme une vraie page web, avec la même règle que le site des vols : si la
phrase « bientôt disponible » disparaît, un message 🚨 part sur Telegram.
"""
import os
import time
import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PAGE = "https://raw.githubusercontent.com/g9jr5p8nyf-droid/alerte-vols/main/test-alerte.txt"
PHRASE = "bientôt disponible"
# Un seul message par test ; on réarme quand la phrase revient
DEJA_ENVOYE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".test_envoye")


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
        # Le paramètre « t » évite de lire une ancienne copie en cache
        r = requests.get(PAGE, params={"t": int(time.time())}, timeout=20,
                         headers={"Cache-Control": "no-cache"})
    except Exception as e:
        print("Page de test : erreur de lecture :", e)
        return
    if r.status_code != 200:
        print("Page de test : code", r.status_code, "(ignoré)")
        return
    attente = PHRASE in r.content.decode("utf-8", errors="ignore").lower()
    print("Page de test : phrase d'attente vue :", attente)

    if attente:
        if os.path.exists(DEJA_ENVOYE):
            os.remove(DEJA_ENVOYE)  # réarmé pour un prochain test
    elif not os.path.exists(DEJA_ENVOYE):
        envoyer("🚨 TEST : la phrase « bientôt disponible » a disparu de ta page "
                "de test. L'alerte fonctionne de bout en bout ✅")
        open(DEJA_ENVOYE, "w").close()


if __name__ == "__main__":
    verifier()
