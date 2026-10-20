import os
import requests

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
URL = "https://voyage.benin.bj"
PHRASE = "bientôt disponible"


def envoyer(msg):
    requests.post(
        "https://api.telegram.org/bot" + TOKEN + "/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg},
        timeout=20,
    )


try:
    r = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    page = r.content.decode("utf-8", errors="ignore").lower()
    ok = r.status_code == 200 and len(page) > 500
except Exception as e:
    print("Erreur de lecture :", e)
    page = ""
    ok = False

attente = PHRASE in page
print("Page lue :", ok, "| phrase d'attente vue :", attente)

# Lancement manuel = message de test
if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
    envoyer("✅ Test GitHub OK. Page lue : " + str(ok)
            + " | phrase d'attente vue : " + str(attente))

# Vraie alerte : la page est lue et la phrase d'attente a disparu
if ok and not attente:
    envoyer("🚨 La page a changé, va vite voir : " + URL)
