"""Étape 2 : R-JPEG thermiques DJI → températures par pixel (°C) et métadonnées de prise de vue.

    .venv/bin/python scripts/extract_data.py [--entree data/raw_rjpegs] [--sortie data/processed] [--npy]
        [--exact --reflexion °C] [--emissivite e] [--distance m] [--humidite %]

Écrit `<sortie>/metadata_db.json` (une entrée par photo) et, avec --npy, `<sortie>/<nom>.npy` (float32, °C).

Deux modes (décidés le 06/11/2026 ; sources, calculs et mesures dans REPRISE.md, « Réglages de mesure ») :
- **par défaut, les réglages de la photo** (ceux du pilote, souvent 0,95 / 5 m / 50 % / 25 °C) : mêmes chiffres
  que DJI Pilot et que l'onglet Thermique d'OrthoStudio. Sous ciel clair, les écarts entre modules sont
  sous-estimés de 4,5 à 7,5 % (calcul de Planck) et les températures absolues de 6 à 8 °C : elles ne sont
  qu'indicatives.
- **--exact, températures exactes** : émissivité du verre 0,85 (ZAE Bayern : 0,82 au maximum en vue
  perpendiculaire, stable jusqu'à ~40°) **et** température réfléchie mesurée sur place (réflecteur en aluminium
  froissé), obligatoire : 0,85 seule ne corrige pas les températures (encore ~6 °C trop basses sous ciel clair).
La distance reste celle de la photo, même en mode exact : la correction de distance de DJI n'est pas une simple
transmission atmosphérique (à 25 m, elle multiplie les écarts par 1,29 sur le M4T, 1,16 sur le M3T, 1,01 sur le
M30T, sans dépendre de l'humidité sur le M4T) ; un essai sur cible de température connue à 5, 15, 25 et 40 m
dira s'il faut la régler sur l'altitude. Les anomalies (étapes 3 à 5) se jugent sur des écarts avec les modules
voisins de la même photo.

Les JPEG visibles d'un vol thermique (rangés dans le même dossier) sont marqués `"radiometrique": false`.
Lecture des métadonnées reprise de `georef/metadata.py` d'OrthoStudio (XMP drone-dji, EXIF, MakerNote DJI).
"""

import argparse
import json
import math
import os
import re
import struct
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
EMISSIVITE_VERRE = 0.85
EXTENSIONS = {".jpg", ".jpeg"}
EXIF_IFD, GPS_IFD, TAG_MAKERNOTE = 0x8769, 0x8825, 37500
TAG_MAKE, TAG_MODEL, TAG_DATETIME, TAG_DATETIME_ORIGINAL = 271, 272, 306, 36867
# Réglage → (option de dji_irp, clé des paramètres et des plages du SDK, libellé)
REGLAGES = {"emissivite": ("--emissivity", "emissivity", "émissivité"),
            "distance": ("--distance", "distance", "distance (m)"),
            "humidite": ("--humidity", "humidity", "humidité (%)"),
            "reflexion": ("--reflection", "reflection", "température réfléchie (°C)")}


class ErreurMesure(RuntimeError):
    """dji_irp a refusé le fichier ou un réglage."""


class NonRadiometrique(ErreurMesure):
    """Le fichier n'est pas un R-JPEG DJI (photo visible, image retouchée…) : code −7 du SDK."""


def outil():
    """dji_irp : variable DJI_IRP, sinon celui du dépôt (installé par scripts/install_dji_sdk.sh)."""
    chemin = Path(os.environ.get("DJI_IRP") or RACINE / "dji_sdk" / "bin" / "dji_irp")
    if not chemin.is_file():
        raise FileNotFoundError(f"dji_irp introuvable ({chemin}) : lancer scripts/install_dji_sdk.sh")
    return chemin


def _lancer(args):
    r = subprocess.run([str(outil()), *map(str, args)], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        detail = (r.stderr.strip().splitlines() or ["(pas de message)"])[-1]
        if ": -7 " in detail:
            raise NonRadiometrique(detail)
        raise ErreurMesure(f"dji_irp {' '.join(map(str, args[:4]))} : code {r.returncode}, {detail}")
    return r.stdout


def parametres(chemin):
    """`dji_irp -a info` : taille, versions, paramètres de mesure de la photo et plages acceptées par le modèle.
    Le SDK écrit parfois des messages avant le JSON : seule la ligne qui commence par « { » est lue."""
    sortie = _lancer(["-s", chemin, "-a", "info"])
    ligne = next((l for l in sortie.splitlines() if l.startswith("{")), None)
    if ligne is None:
        raise ErreurMesure(f"dji_irp -a info : pas de JSON pour {chemin}")
    return json.loads(ligne)


def reglages_mode(exact=False, emissivite=None, distance=None, humidite=None, reflexion=None):
    """Réglages demandés selon le mode. Exact : émissivité 0,85 (sauf valeur donnée) et température réfléchie
    obligatoire ; ValueError sinon."""
    if exact:
        if reflexion is None:
            raise ValueError("mode exact : la température réfléchie mesurée sur place est obligatoire (--reflexion)")
        emissivite = EMISSIVITE_VERRE if emissivite is None else emissivite
    return {"emissivite": emissivite, "distance": distance, "humidite": humidite, "reflexion": reflexion}


def reglages_effectifs(info, emissivite=None, distance=None, humidite=None, reflexion=None):
    """{réglage: valeur} appliqués à la mesure (None = valeur de la photo) ; ValueError hors de la plage du modèle.
    Une valeur hors plage est refusée par le SDK (code −3), pas bornée : on le dit avant de lancer la mesure."""
    demandes = {"emissivite": emissivite, "distance": distance, "humidite": humidite, "reflexion": reflexion}
    photo = info.get("measurement_params") or {}
    plages = info.get("measurement_ranges") or {}
    out = {}
    for nom, valeur in demandes.items():
        _, cle, libelle = REGLAGES[nom]
        if valeur is None:
            out[nom] = photo.get(cle)
            continue
        if not photo:
            raise ValueError(f"{libelle} non réglable pour ce modèle (paramètres de mesure illisibles)")
        lo, hi = plages.get(cle) or (-math.inf, math.inf)
        if not lo <= float(valeur) <= hi:
            raise ValueError(f"{libelle} {valeur} hors de la plage acceptée par ce modèle [{lo:g} ; {hi:g}]")
        out[nom] = float(valeur)
    return out


def temperatures(chemin, emissivite=None, distance=None, humidite=None, reflexion=None, info=None):
    """Matrice des températures (°C, float32, lignes × colonnes de l'image thermique) par `dji_irp -a measure`.
    Réglages à None : ceux de la photo (mode exact : voir `reglages_mode`)."""
    info = info or parametres(chemin)
    eff = reglages_effectifs(info, emissivite, distance, humidite, reflexion)
    demandes = {"emissivite": emissivite, "distance": distance, "humidite": humidite, "reflexion": reflexion}
    options = [x for nom, v in demandes.items() if v is not None for x in (REGLAGES[nom][0], eff[nom])]
    l, h = int(info["width"]), int(info["height"])
    with tempfile.TemporaryDirectory() as d:
        sortie = Path(d) / "t.raw"
        _lancer(["-s", chemin, "-a", "measure", "-o", sortie, "--measurefmt", "float32", *options])
        t = np.fromfile(sortie, dtype="<f4")
    if t.size != l * h:
        raise ErreurMesure(f"{chemin} : {t.size} valeurs pour une image {l} × {h}")
    return t.reshape(h, l)


# --------------------------------------------------------------------------------------------- métadonnées

def xmp_valeur(xmp, nom):
    """Valeur d'une propriété XMP, en attribut (ns:Nom="…") ou en élément (<ns:Nom>…</ns:Nom>)."""
    m = re.search(rf'[\w-]+:{nom}="([^"]*)"', xmp) or re.search(rf"<[\w-]+:{nom}>([^<]*)</", xmp)
    return m.group(1).strip() if m else None


def _num(v):
    if v is None or v == "":
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        try:                                         # IFDRational, tuple (num, den)
            x = float(v[0]) / float(v[1])
        except Exception:
            return None
    return x if math.isfinite(x) else None           # rationnel 0/0 : champ vide


def _dms(v, ref):
    try:
        d, m, s = (float(x) for x in v)
    except Exception:
        return None
    val = d + m / 60 + s / 3600
    if not math.isfinite(val):
        return None
    return -val if ref in ("S", "W") else val


def _date(texte):
    try:
        return datetime.strptime(str(texte).strip().rstrip("\x00"), "%Y:%m:%d %H:%M:%S").isoformat()
    except (TypeError, ValueError):
        return None


def angles_makernote(mn):
    """Flottants 6-11 de la MakerNote DJI (6-8 : tangage / cap / roulis du drone, 9-11 : de la nacelle), {} sinon."""
    if not isinstance(mn, (bytes, bytearray)) or len(mn) < 14:
        return {}
    n = struct.unpack_from("<H", mn)[0]
    if not 0 < n < 200 or len(mn) < 2 + 12 * n:
        return {}
    out = {}
    for i in range(n):
        tag, typ, cnt, val = struct.unpack_from("<HHI4s", mn, 2 + 12 * i)
        if typ == 11 and cnt == 1 and 6 <= tag <= 11:
            v = struct.unpack("<f", val)[0]
            if abs(v) <= 360:
                out[tag] = round(float(v), 2)
    return out


def metadonnees(chemin):
    """Modèle, date, position, altitudes, attitude de la nacelle et du drone d'une photo DJI (sans les pixels).
    Angles en degrés [yaw, pitch, roll] ; pitch nacelle −90 = visée verticale. alt_rel : au-dessus du décollage."""
    chemin = Path(chemin)
    with Image.open(chemin) as img:
        largeur, hauteur = img.size
        exif = img.getexif()
        xmp = img.info.get("xmp") or b""
        ifd, gps = dict(exif.get_ifd(EXIF_IFD)), dict(exif.get_ifd(GPS_IFD))
    xmp = xmp.decode("utf-8", "ignore") if isinstance(xmp, (bytes, bytearray)) else str(xmp)
    m = {"fichier": chemin.name, "chemin": str(chemin), "largeur": largeur, "hauteur": hauteur,
         "fabricant": str(exif.get(TAG_MAKE) or "").strip().rstrip("\x00"),
         "modele": str(exif.get(TAG_MODEL) or "").strip().rstrip("\x00"),
         "date": _date(ifd.get(TAG_DATETIME_ORIGINAL) or exif.get(TAG_DATETIME)),
         "lat": None, "lon": None, "alt_abs": None, "alt_rel": None, "nacelle": None, "vol": None,
         "source_angles": None, "alertes": []}
    if 2 in gps and 4 in gps:
        m["lat"], m["lon"] = _dms(gps[2], gps.get(1)), _dms(gps[4], gps.get(3))
    alt_gps = _num(gps.get(6))
    if alt_gps is not None and gps.get(5) in (1, b"\x01"):
        alt_gps = -alt_gps
    m["alt_abs"] = _num(xmp_valeur(xmp, "AbsoluteAltitude"))
    if m["alt_abs"] is None:
        m["alt_abs"] = alt_gps
    m["alt_rel"] = _num(xmp_valeur(xmp, "RelativeAltitude"))
    angles = lambda p: [_num(xmp_valeur(xmp, f"{p}{a}Degree")) for a in ("Yaw", "Pitch", "Roll")]   # noqa: E731
    nacelle, vol = angles("Gimbal"), angles("Flight")
    if any(v is not None for v in nacelle):
        m["nacelle"], m["vol"], m["source_angles"] = nacelle, vol, "xmp"
    else:
        mn = angles_makernote(ifd.get(TAG_MAKERNOTE))
        if mn:
            m["nacelle"] = [mn.get(10), mn.get(9), mn.get(11)]
            m["vol"] = [mn.get(7), mn.get(6), mn.get(8)]
            m["source_angles"] = "makernote"
    if m["lat"] is None or m["lon"] is None:
        m["alertes"].append("pas de position GPS")
    if not xmp:
        m["alertes"].append("pas d'XMP DJI (altitude relative et attitude de la nacelle inconnues)")
    return m


# --------------------------------------------------------------------------------------------- lot

def traiter(entree, sortie, npy=False, exact=False, **reglages):
    """Toutes les photos de `entree` (sous-dossiers compris) → `sortie/metadata_db.json` (+ matrices .npy)."""
    reglages = reglages_mode(exact, **reglages)
    entree, sortie = Path(entree), Path(sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    photos = sorted(p for p in entree.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS)
    base = []
    for p in photos:
        rel = p.relative_to(entree)
        try:
            m = metadonnees(p)
        except OSError as e:
            base.append({"fichier": str(rel), "erreur": f"illisible : {e}"})
            continue
        m["fichier"] = str(rel)
        try:
            info = parametres(p)
            t = temperatures(p, info=info, **reglages)
        except NonRadiometrique:                     # JPEG visible du même vol : pas une erreur
            m["radiometrique"] = False
            base.append(m)
            continue
        except (ErreurMesure, ValueError) as e:      # réglage hors plage, modèle non pris en charge…
            m["erreur"] = str(e)
            base.append(m)
            continue
        m["radiometrique"] = True
        m["mode"] = "exact" if exact else "photo"
        m["parametres_photo"] = info.get("measurement_params")
        m["reglages"] = reglages_effectifs(info, **reglages)
        ok = t[np.isfinite(t)]
        m["temperatures"] = {"min": round(float(ok.min()), 2), "mediane": round(float(np.median(ok)), 2),
                             "max": round(float(ok.max()), 2)}
        if npy:
            f = sortie / rel.with_suffix(".npy")
            f.parent.mkdir(parents=True, exist_ok=True)
            np.save(f, t)
            m["matrice"] = str(f.relative_to(sortie))
        base.append(m)
    (sortie / "metadata_db.json").write_text(json.dumps(base, ensure_ascii=False, indent=1), encoding="utf-8")
    return base


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    a.add_argument("--entree", default=RACINE / "data" / "raw_rjpegs", type=Path)
    a.add_argument("--sortie", default=RACINE / "data" / "processed", type=Path)
    a.add_argument("--npy", action="store_true", help="écrire aussi les matrices de températures (.npy)")
    a.add_argument("--exact", action="store_true",
                   help="températures exactes : émissivité 0,85 + --reflexion mesurée (obligatoire)")
    a.add_argument("--reflexion", type=float, help="température réfléchie mesurée sur place (°C)")
    a.add_argument("--emissivite", type=float, help="remplace celle de la photo (ou le 0,85 du mode exact)")
    a.add_argument("--distance", type=float, help="déconseillé : voir l'en-tête")
    a.add_argument("--humidite", type=float)
    o = a.parse_args(argv)
    try:
        base = traiter(o.entree, o.sortie, o.npy, o.exact, emissivite=o.emissivite, distance=o.distance,
                       humidite=o.humidite, reflexion=o.reflexion)
    except ValueError as e:
        a.error(str(e))
    erreurs = sum("erreur" in m for m in base)
    visibles = sum(m.get("radiometrique") is False for m in base)
    print(f"{len(base)} photo(s) : {len(base) - erreurs - visibles} thermique(s), {visibles} visible(s), "
          f"{erreurs} en erreur → {o.sortie / 'metadata_db.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
