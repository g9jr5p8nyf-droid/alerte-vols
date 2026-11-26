"""Test grandeur nature : Black Friday d'AMS Beauty (ams-beauty.com).

Ce n'est pas lié aux vols : c'est un vrai test de l'alerte sur une vente
attendue (27/11/2026), avec la même logique en deux niveaux que la billetterie :
  ⚠️  ça se prépare : « Black Friday » apparaît sur le site, une nouvelle
      collection Black Friday est créée, ou le site passe en mode « mot de passe » ;
  🚨  c'est ouvert : des produits sont vraiment en promotion (prix barrés) ou la
      collection Black Friday contient des produits.

État au 26/11/2026 à 13h30 : aucune mention de Black Friday, 0 produit en
promotion, aucune collection Black Friday.
Vérifie chaque minute. Pour arrêter le test : supprimer ce fichier.
"""
import os
import re
import time
import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
DOSSIER = os.path.dirname(os.path.abspath(__file__))
SITE = "https://ams-beauty.com"
MOTS = re.compile(r"black[\s_-]*friday|blackfriday|cyber[\s_-]*monday|black[\s_-]*week", re.I)
SEUIL_PROMOS = 5  # nombre de produits à prix barré pour considérer que c'est ouvert
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


def permis(nom, delai):
    """Vrai si aucun message « nom » n'a été envoyé depuis « delai » secondes."""
    chemin = os.path.join(DOSSIER, ".ams_" + nom)
    try:
        if time.time() - os.path.getmtime(chemin) < delai:
            return False
    except OSError:
        pass
    open(chemin, "w").close()
    return True


def get(chemin):
    return requests.get(SITE + chemin, headers=ENTETES, timeout=25)


def verifier():
    signes_prep, signes_ouvert = [], []

    # 1. Page d'accueil : mention Black Friday, ou site verrouillé par mot de passe
    r = get("/")
    if "/password" in r.url:
        signes_prep.append(("password", "le site est passé en mode « mot de passe » (préparation de la vente)"))
    elif r.status_code == 200:
        texte = re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text, flags=re.S)
        texte = re.sub(r"<[^>]+>", " ", texte)
        m = MOTS.search(texte)
        if m:
            extrait = " ".join(texte[max(0, m.start() - 60):m.end() + 80].split())
            signes_prep.append(("accueil", "« Black Friday » apparaît sur la page d'accueil : … " + extrait + " …"))

    # 2. Collections : nouvelle collection Black Friday (et contient-elle des produits ?)
    r = get("/collections.json?limit=250")
    if r.status_code == 200:
        for c in r.json().get("collections", []):
            if MOTS.search(c.get("title", "") + " " + c.get("handle", "").replace("-", " ")) \
                    or c.get("handle") in ("bf", "bf-2026"):
                lien = SITE + "/collections/" + c["handle"]
                if c.get("products_count", 0) > 0:
                    signes_ouvert.append("collection « " + c["title"] + " » avec "
                                         + str(c["products_count"]) + " produits : " + lien)
                else:
                    signes_prep.append(("col_" + c["handle"], "collection « " + c["title"] + " » créée (encore vide) : " + lien))

    # 3. Produits à prix barré (la vraie promotion)
    promos = []
    for page in (1, 2):
        r = get("/products.json?limit=250&page=" + str(page))
        if r.status_code != 200:
            break
        produits = r.json().get("products", [])
        for p in produits:
            for v in p.get("variants", []):
                if v.get("compare_at_price") and float(v["compare_at_price"]) > float(v["price"]):
                    promos.append(p["title"] + " " + v["price"] + "€ au lieu de " + v["compare_at_price"] + "€")
                    break
        if len(produits) < 250:
            break
    if len(promos) >= SEUIL_PROMOS:
        signes_ouvert.append(str(len(promos)) + " produits à prix barré, par exemple : "
                             + " ; ".join(promos[:3]))

    if signes_ouvert and permis("ouvert", 600):
        envoyer("🚨🚨 TEST AMS BEAUTY : le Black Friday semble ouvert !\n- "
                + "\n- ".join(signes_ouvert) + "\n" + SITE)
    elif signes_prep and permis("prep_" + "+".join(sorted(k for k, _ in signes_prep))[:120], 10**9):
        envoyer("⚠️ TEST AMS BEAUTY : le Black Friday se prépare.\n- "
                + "\n- ".join(t for _, t in signes_prep) + "\nCe n'est pas encore l'ouverture : attends le 🚨🚨.\n" + SITE)


if __name__ == "__main__":
    verifier()
