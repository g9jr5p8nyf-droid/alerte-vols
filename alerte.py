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

# Empreinte de la configuration de la billetterie verrouillée (règles de
# sécurité, page de mot de passe). Le 24/11/2026, l'ajout d'un anti-robots
# (Cloudflare Turnstile) l'a modifiée sans toucher au mot de passe : un
# changement de ce genre montre que l'équipe prépare le lancement.
EMPREINTE_CONNUE = "fa8df02c4f2210e2"
config_changee = False
empreinte = None
if statut_b == 401:
    import hashlib
    csp = " ".join(rb.headers.get("Content-Security-Policy", "").split())
    signature = (csp + "|" + rb.headers.get("WWW-Authenticate", "") + "|"
                 + hashlib.sha256(rb.content).hexdigest())
    empreinte = hashlib.sha256(signature.encode()).hexdigest()[:16]
    config_changee = empreinte != EMPREINTE_CONNUE
print("Configuration billetterie :", empreinte, "| changée :", config_changee)

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

# Avec une vérification par minute, on n'envoie pas le même message à chaque
# tour : premier message tout de suite, puis un rappel toutes les 10 minutes.
def rappel_permis(nom, delai=600):
    import time
    marque = os.path.join(os.path.dirname(os.path.abspath(__file__)), "." + nom)
    try:
        if time.time() - os.path.getmtime(marque) < delai:
            return False
    except OSError:
        pass
    open(marque, "w").close()
    return True


# Un seul message par nouvelle configuration (au plus un rappel par session)
if config_changee and rappel_permis("alerte_config_" + empreinte, delai=10**9):
    envoyer("⚠️ La configuration de la billetterie Bénin Tours vient de changer "
            "(elle est toujours protégée par un mot de passe).\n"
            "L'équipe est en train de la préparer : l'ouverture approche. "
            "Garde ta fiche prête !\n" + URL_BILLETTERIE)

if billetterie_ouverte and rappel_permis("alerte_billetterie"):
    envoyer("🚨🚨 La billetterie Bénin Tours n'est plus protégée par un mot de "
            "passe : la vente est peut-être ouverte !\nVa vite voir : "
            + URL_BILLETTERIE + "\n(et aussi " + URL + ")")

if raisons:
    if rappel_permis("alerte_site"):
        envoyer("🚨 Le site des vols a changé, va vite voir : " + URL
                + "\n- " + "\n- ".join(raisons))
elif maintenance and rappel_permis("alerte_maintenance"):
    envoyer("⚠️ Le site affiche une maintenance (code " + str(statut) + ").\n"
            + "Ils sont peut-être en train de mettre la billetterie en ligne : " + URL)

# Garde-fou : si un site ne répond plus normalement pendant 10 vérifications
# d'affilée (blocage des serveurs de GitHub, anti-robots, panne, adresse
# changée…), l'alerte ne peut plus voir l'ouverture : on prévient.
def suivre_anomalie(nom, anormal, detail, seuil=10):
    import json
    fichier = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".anomalies")
    try:
        compteurs = json.load(open(fichier))
    except Exception:
        compteurs = {}
    compteurs[nom] = compteurs.get(nom, 0) + 1 if anormal else 0
    json.dump(compteurs, open(fichier, "w"))
    if compteurs[nom] >= seuil and rappel_permis("alerte_anomalie_" + nom, delai=7200):
        envoyer("⚠️ Attention : " + detail + " depuis environ " + str(compteurs[nom])
                + " minutes. L'alerte ne peut peut-être plus détecter l'ouverture : "
                "va vérifier toi-même le site, et préviens-moi.")


suivre_anomalie("site", statut != 200,
                "voyage.benin.bj ne répond plus normalement (code " + str(statut) + ")")
suivre_anomalie("billetterie", statut_b not in (200, 401),
                "la billetterie voyage.benintours.bj ne répond plus normalement (code "
                + str(statut_b) + ")")

# Alerte précoce : nouveaux certificats sur les domaines des vols (toutes les 30 min)
try:
    import alerte_certs
    alerte_certs.verifier()
except Exception as e:
    print("Vérification des certificats ignorée :", e)

# Test de bout en bout contrôlé par l'utilisatrice (sans effet sur les vols)
try:
    import alerte_test
    alerte_test.verifier()
except Exception as e:
    print("Test de la page ignoré :", e)

# Alerte précoce : nouveaux fichiers dans le dossier public de voyage.benin.bj (toutes les 5 min)
try:
    import alerte_dossiers
    alerte_dossiers.verifier()
except Exception as e:
    print("Vérification du dossier ignorée :", e)

# Alerte retour en stock : palette VIBRANT MOOD (supprimer alerte_ams.py pour arrêter)
try:
    import alerte_ams
    alerte_ams.verifier()
except Exception as e:
    print("Test AMS Beauty ignoré :", e)
