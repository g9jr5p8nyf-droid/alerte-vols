"""Alerte précoce : nouveau certificat de sécurité sur les domaines des vols.

Avant de mettre une adresse en ligne, il faut lui créer un certificat, et
chaque certificat est inscrit dans un registre public (crt.sh). L'an dernier,
les adresses de la billetterie ont été créées les 27 et 28 novembre 2025,
un à deux jours avant l'ouverture du 29 novembre.

Vérifie toutes les 30 minutes (le registre est lent) et envoie un message
« ⚠️ » pour chaque nouveau certificat lié aux vols.
"""
import os
import time
import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
DOSSIER = os.path.dirname(os.path.abspath(__file__))
DERNIERE = os.path.join(DOSSIER, ".certs_derniere")  # heure de la dernière vérification
ENVOYES = os.path.join(DOSSIER, ".certs_envoyes")    # certificats déjà signalés

# Certificats déjà connus au 22/11/2026 : on ne signale que ceux créés après
DEPUIS = "2026-11-27T18:00"  # après l'ouverture et le passage à Cloudflare
# benin.bj a beaucoup de sites publics : on ne garde que les noms liés aux vols.
# benintours.bj : tout nouveau certificat compte.
MOTS_BENIN = ("voyage", "charter", "vol", "billet", "reserv", "booking", "diaspora", "flight")


def envoyer(msg):
    if not TOKEN or not CHAT_ID:
        print("[Telegram non configuré] " + msg)
        return
    try:
        requests.post("https://api.telegram.org/bot" + TOKEN + "/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg}, timeout=20)
    except Exception as e:
        print("Erreur Telegram :", e)


def lire_registre(domaine):
    # Un seul essai court : le registre est parfois lent, et il ne doit pas
    # retarder la vérification des sites qui tourne chaque minute.
    try:
        r = requests.get("https://crt.sh/", params={"q": "%." + domaine, "output": "json"},
                         timeout=20)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None  # registre indisponible : nouvel essai dans 5 minutes


def verifier(intervalle=1800):
    try:
        if time.time() - os.path.getmtime(DERNIERE) < intervalle:
            return
    except OSError:
        pass
    open(DERNIERE, "w").close()

    try:
        envoyes = set(open(ENVOYES).read().split())
    except OSError:
        envoyes = set()

    nouveaux, indisponible = [], False
    for domaine in ("benin.bj", "benintours.bj"):
        certs = lire_registre(domaine)
        if certs is None:
            print("Certificats", domaine, ": registre indisponible")
            indisponible = True
            continue
        # Adresses qui existaient déjà : leurs renouvellements automatiques
        # (tous les 2-3 mois) ne sont pas un signe de lancement.
        connues = {frozenset(c.get("name_value", "").lower().split())
                   for c in certs if c.get("not_before", "") < DEPUIS}
        vus = set()
        for c in certs:
            noms = frozenset(c.get("name_value", "").lower().split())
            if c.get("not_before", "") < DEPUIS or noms in connues or noms in vus:
                continue
            if domaine == "benin.bj" and not any(m in n for n in noms for m in MOTS_BENIN):
                continue
            vus.add(noms)
            if str(c.get("id")) not in envoyes:
                nouveaux.append(c)
    if indisponible:
        # On réessaie dans 5 minutes plutôt que 30
        os.utime(DERNIERE, (time.time() - intervalle + 300,) * 2)
    print("Certificats : %d nouveau(x)" % len(nouveaux))

    for c in nouveaux:
        envoyer("⚠️ Nouveau certificat de sécurité détecté pour : "
                + c.get("name_value", "").replace("\n", ", ")
                + " (créé le " + c.get("not_before", "")[:16].replace("T", " ") + " UTC).\n"
                "Une adresse liée aux vols est en préparation : l'an dernier, la "
                "billetterie avait ouvert 1 à 2 jours après. Garde ta fiche prête !")
        envoyes.add(str(c.get("id")))
    open(ENVOYES, "w").write("\n".join(sorted(envoyes)))


if __name__ == "__main__":
    verifier(intervalle=0)
