import os
import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
URL = "https://voyage.benin.bj"
PHRASE = "bientôt disponible"

# Date de dernière modification de la page d'attente (relevée le 10/11/2026).
# Si le serveur annonce une autre date, quelqu'un a touché au site.
DATE_CONNUE = "Fri, 07 Aug 2026 17:12:31 GMT"


def envoyer(msg):
    if not TOKEN or not CHAT_ID:
        print("[Telegram non configuré] " + msg)
        return
    try:
        r = requests.post(
            "https://api.telegram.org/bot" + TOKEN + "/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=20,
        )
        if not r.ok:
            print("Erreur Telegram :", r.status_code, r.text[:200])
    except Exception as e:
        print("Erreur Telegram :", e)


statut = None
page = ""
date = None
url_finale = URL
try:
    r = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    statut = r.status_code
    page = r.content.decode("utf-8", errors="ignore").lower()
    date = r.headers.get("Last-Modified")
    url_finale = r.url
except Exception as e:
    print("Erreur de lecture :", e)

ok = statut == 200 and len(page) > 500
attente = PHRASE in page
date_changee = ok and date is not None and date != DATE_CONNUE
redirige = ok and url_finale.rstrip("/") != URL
maintenance = statut == 503 or (statut == 200 and "maintenance" in page)

print("Statut :", statut, "| page lue :", ok, "| phrase d'attente vue :", attente)
print("Date de modification :", date, "| changée :", date_changee)
print("Adresse finale :", url_finale)

# Billetterie de Bénin Tours, protégée par un mot de passe (code 401) depuis
# au moins le 11/11/2026. Si la protection disparaît, la vente est ouverte.
URL_BILLETTERIE = "https://voyage.benintours.bj"
statut_b = None
try:
    rb = requests.get(URL_BILLETTERIE, timeout=30,
                      headers={"User-Agent": "Mozilla/5.0"})
    statut_b = rb.status_code
except Exception as e:
    print("Erreur de lecture billetterie :", e)

# Seul un vrai accès public compte (200) : une panne (5xx) ou une erreur
# réseau ne déclenche rien, pour éviter les fausses alertes.
billetterie_ouverte = statut_b == 200
print("Billetterie Bénin Tours : code", statut_b,
      "| verrouillée :", statut_b == 401, "| ouverte :", billetterie_ouverte)

# Lancement manuel = message de test
if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
    envoyer("✅ Test GitHub OK\n"
            + "Page lue : " + str(ok) + "\n"
            + "Phrase d'attente vue : " + str(attente) + "\n"
            + "Date du site : " + str(date) + "\n"
            + "Billetterie Bénin Tours : "
            + ("verrouillée" if statut_b == 401 else "code " + str(statut_b)))

# Vraie alerte : un des signaux indique que le site a bougé
raisons = []
if ok and not attente:
    raisons.append("la phrase « bientôt disponible » a disparu")
if date_changee:
    raisons.append("le site a été modifié le " + date)
if redirige:
    raisons.append("le site redirige vers " + url_finale)

if billetterie_ouverte:
    envoyer("🚨🚨 La billetterie Bénin Tours n'est plus protégée par un mot de "
            "passe : la vente est peut-être ouverte !\nVa vite voir : "
            + URL_BILLETTERIE + "\n(et aussi " + URL + ")")

if raisons:
    envoyer("🚨 Le site des vols a changé, va vite voir : " + URL
            + "\n- " + "\n- ".join(raisons))
elif maintenance:
    envoyer("⚠️ Le site affiche une maintenance (code " + str(statut) + ").\n"
            + "Ils sont peut-être en train de mettre la billetterie en ligne : " + URL)
