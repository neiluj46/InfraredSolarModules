"""Étape 5 : R-JPEG thermiques DJI → modules détectés, forme de l'anomalie, placés au sol →
`output/orthostudio_report.geojson` (polygones WGS 84 + T_max, T_moyenne, ΔT) importable dans OrthoStudio.

    .venv/bin/python scripts/export_orthostudio.py [--entree data/raw_rjpegs] [--sortie output/orthostudio_report.geojson]
        [--exact --reflexion °C] [--hauteur-modules 1.5] [--tous]

Chaîne : `extract_data` (températures, métadonnées) → `detecteur.analyser` (modules, forme) → projection de chaque
coin de module sur un **sol plan** → fusion des vues d'un même module sur plusieurs photos.

Projection (conventions de `georef/camera.py` d'OrthoStudio, `rotation_dji` reprise telle quelle) :
- caméra sténopé sans distorsion, focale tirée du champ de vision diagonal (DFOV) officiel DJI quand il est connu
  (`DFOV_THERMIQUE`), sinon de la focale équivalente 35 mm rapportée à la diagonale (43,27 mm) ; source notée ;
- orientation : nacelle (GimbalYaw / Pitch / Roll du XMP, cap depuis le nord vrai) ; à défaut, cap du drone et
  visée verticale (signalé) ;
- plan horizontal à `RelativeAltitude − hauteur des modules` sous la caméra : suppose un terrain plat au niveau du
  décollage. Sans RTK, l'erreur de position (1 à 3 m) et de cap dépasse souvent la taille d'un module : le calage
  sur l'orthophoto d'OrthoStudio reste à faire.

Fusion : deux modules à moins d'une demi-largeur l'un de l'autre au sol sont le même module ; on garde la vue la
plus proche du centre de sa photo (moins de distorsion et de reflet). Une anomalie vue sur une seule des photos où
le module apparaît est marquée `confirmee: false` (un reflet du soleil se déplace d'une photo à l'autre, un vrai
défaut non).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anomalies  # noqa: E402
import detecteur  # noqa: E402
import extract_data  # noqa: E402

RACINE = Path(__file__).resolve().parents[1]
# Champ de vision diagonal de la caméra thermique (degrés), fiches DJI (vérifiées le 06/11/2026)
DFOV_THERMIQUE = {"M3T": 61.0, "M3TD": 61.0, "M30T": 61.0, "M4T": 45.0, "H30T": 45.2}
DIAGONALE_35 = math.hypot(36, 24)
A_WGS84, E2_WGS84 = 6378137.0, 6.69437999014e-3


# --------------------------------------------------------------------------------------------- caméra

def focale_px(meta, exif_f35=None):
    """(focale en pixels, source) d'une image thermique de `meta` (largeur, hauteur, modele)."""
    w, h = meta["largeur"], meta["hauteur"]
    diag = math.hypot(w, h)
    dfov = DFOV_THERMIQUE.get((meta.get("modele") or "").upper())
    if dfov:
        return diag / 2 / math.tan(math.radians(dfov) / 2), f"DFOV DJI {dfov:g}°"
    if exif_f35:
        return diag * exif_f35 / DIAGONALE_35, f"focale équivalente {exif_f35:g} mm (diagonale)"
    return diag / 2 / math.tan(math.radians(61) / 2), "hypothèse DFOV 61° (à vérifier)"


def rotation_dji(yaw, pitch, roll):
    """Rotation monde (ENU) → caméra (x droite, y bas, z avant), reprise de `georef/camera.py` d'OrthoStudio :
    yaw = cap de la nacelle depuis le nord vrai (horaire), pitch −90 = nadir, roll positif = droite vers le bas."""
    def rz(a):
        c, s = math.cos(a), math.sin(a)
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

    def ry(a):
        c, s = math.cos(a), math.sin(a)
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])

    def rx(a):
        c, s = math.cos(a), math.sin(a)
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])

    nacelle_depuis_camera = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]], float)
    enu_depuis_ned = np.array([[0, 1, 0], [1, 0, 0], [0, 0, -1]], float)
    r_ned = rz(math.radians(yaw)) @ ry(math.radians(pitch)) @ rx(math.radians(roll))
    return (enu_depuis_ned @ r_ned @ nacelle_depuis_camera).T


def pose(meta):
    """(yaw, pitch, roll, alertes) : nacelle, sinon cap du drone en visée verticale."""
    alertes = []
    n = meta.get("nacelle") or [None, None, None]
    yaw, pitch, roll = n
    if yaw is None:
        yaw = (meta.get("vol") or [None])[0]
        alertes.append("cap de la nacelle inconnu : cap du drone" if yaw is not None else "cap inconnu : nord supposé")
        yaw = yaw or 0.0
    if pitch is None:
        pitch = -90.0
        alertes.append("inclinaison de la nacelle inconnue : visée verticale supposée")
    return float(yaw), float(pitch), float(roll or 0.0), alertes


def vers_sol(u, v, f, cx, cy, R, hauteur):
    """Pixels (u, v) → (est, nord) en mètres depuis l'aplomb de la caméra, sur le plan situé `hauteur` m plus bas ;
    NaN pour un rayon qui ne descend pas."""
    d = np.stack([(np.asarray(u, float) - cx) / f, (np.asarray(v, float) - cy) / f, np.ones(np.size(u))], 1) @ R
    t = np.where(d[:, 2] < -1e-6, -hauteur / np.where(d[:, 2] < -1e-6, d[:, 2], -1), np.nan)
    return d[:, 0] * t, d[:, 1] * t


def vers_wgs84(lat0, lon0, est, nord):
    """Décalages locaux (m) → (lon, lat), rayons de courbure WGS 84 (exact au cm sur quelques centaines de mètres)."""
    p = math.radians(lat0)
    s2 = 1 - E2_WGS84 * math.sin(p) ** 2
    rn = A_WGS84 / math.sqrt(s2)                           # grande normale
    rm = A_WGS84 * (1 - E2_WGS84) / s2 ** 1.5               # rayon du méridien
    return (lon0 + np.degrees(np.asarray(est) / (rn * math.cos(p))), lat0 + np.degrees(np.asarray(nord) / rm))


def depuis_wgs84(lat0, lon0, lon, lat):
    p = math.radians(lat0)
    s2 = 1 - E2_WGS84 * math.sin(p) ** 2
    rn, rm = A_WGS84 / math.sqrt(s2), A_WGS84 * (1 - E2_WGS84) / s2 ** 1.5
    return np.radians(np.asarray(lon) - lon0) * rn * math.cos(p), np.radians(np.asarray(lat) - lat0) * rm


# --------------------------------------------------------------------------------------------- une photo

def placer(mods, meta, hauteur_modules=0.0, f35=None):
    """Ajoute à chaque module ses coins (lon, lat), son centre et sa largeur au sol ; renvoie les alertes."""
    yaw, pitch, roll, alertes = pose(meta)
    if meta.get("lat") is None or meta.get("lon") is None:
        return alertes + ["pas de position GPS : modules non placés"]
    hauteur = meta.get("alt_rel")
    if hauteur is None:
        return alertes + ["hauteur au-dessus du décollage inconnue : modules non placés"]
    hauteur -= hauteur_modules
    f, source = focale_px(meta, f35)
    cx, cy = meta["largeur"] / 2 - 0.5, meta["hauteur"] / 2 - 0.5
    R = rotation_dji(yaw, pitch, roll)
    for m in mods:
        pts = np.array(m["coins"] + [[m["cx"], m["cy"]]])
        e, n = vers_sol(pts[:, 0], pts[:, 1], f, cx, cy, R, hauteur)
        if not np.all(np.isfinite(e)):
            continue
        lon, lat = vers_wgs84(meta["lat"], meta["lon"], e, n)
        m["sol"] = {"coins": [[round(float(a), 8), round(float(b), 8)] for a, b in zip(lon[:4], lat[:4])],
                    "centre": [round(float(lon[4]), 8), round(float(lat[4]), 8)],
                    "largeur_m": round(float(min(math.dist((e[0], n[0]), (e[1], n[1])),
                                                 math.dist((e[1], n[1]), (e[2], n[2])))), 2),
                    "focale": source}
        m["ecart_centre"] = round(math.hypot(m["cx"] - cx, m["cy"] - cy) / math.hypot(cx, cy), 3)
    return alertes


# --------------------------------------------------------------------------------------------- fusion

def fusionner(vues):
    """Vues placées [{… sol, ecart_centre, photo}] → modules uniques : la vue la plus centrale, plus `vues`,
    `vues_anomalie`, `formes_vues`, `confirmee`."""
    vues = [v for v in vues if "sol" in v]
    if not vues:
        return []
    lat0 = float(np.mean([v["sol"]["centre"][1] for v in vues]))
    lon0 = float(np.mean([v["sol"]["centre"][0] for v in vues]))
    xy = np.array([depuis_wgs84(lat0, lon0, *v["sol"]["centre"]) for v in vues])
    ordre = np.argsort([v["ecart_centre"] for v in vues])
    pris = np.zeros(len(vues), bool)
    out = []
    for i in ordre:
        if pris[i]:
            continue
        rayon = 0.5 * vues[i]["sol"]["largeur_m"]
        groupe = [j for j in np.flatnonzero(~pris) if math.dist(xy[i], xy[j]) < rayon]
        pris[groupe] = True
        g = [vues[j] for j in groupe]
        formes = Counter(v["forme"] for v in g)
        n_anom = sum(v["forme"] != "sain" for v in g)
        m = dict(vues[i])
        m.update(vues=len(g), vues_anomalie=n_anom, formes_vues=dict(formes),
                 confirmee=(m["forme"] == "sain") or len(g) == 1 or n_anom >= 2)
        if m["forme"] == "sain" and n_anom >= 2:          # défaut vu ailleurs au moins deux fois : on le garde
            pire = next(v for v in sorted(g, key=lambda v: v["ecart_centre"]) if v["forme"] != "sain")
            m.update({k: pire[k] for k in ("forme", "libelle", "ecart_K", "t_max", "t_moyenne", "dT_voisins",
                                           "photo", "sol")}, confirmee=True)
        out.append(m)
    return out


def geojson(modules, tous=False):
    """Modules fusionnés → FeatureCollection (WGS 84). Sans `tous`, seuls les modules en anomalie."""
    feats = []
    for m in modules:
        if not tous and m["forme"] == "sain":
            continue
        anneau = m["sol"]["coins"] + [m["sol"]["coins"][0]]
        feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [anneau]},
                      "properties": {"forme": m["forme"], "libelle": m["libelle"], "anomalie": m["forme"] != "sain",
                                     "confirmee": m["confirmee"], "T_max": m.get("t_max"),
                                     "T_mean": m.get("t_moyenne"), "dT": m.get("ecart_K"),
                                     "dT_voisins": m.get("dT_voisins"), "photo": m.get("photo"),
                                     "vues": m["vues"], "vues_anomalie": m["vues_anomalie"],
                                     "largeur_m": m["sol"]["largeur_m"], "focale": m["sol"]["focale"]}})
    return {"type": "FeatureCollection", "name": "orthostudio_report", "features": feats}


# --------------------------------------------------------------------------------------------- lot

def f35_exif(chemin):
    from PIL import Image
    with Image.open(chemin) as img:
        v = dict(img.getexif().get_ifd(extract_data.EXIF_IFD)).get(41989)
    return float(v) if v else None


def traiter(entree, sortie, exact=False, reflexion=None, hauteur_modules=0.0, tous=False, modele=None):
    reglages = extract_data.reglages_mode(exact, reflexion=reflexion)
    modele = modele or detecteur.td.charger_modele()
    photos = sorted(p for p in Path(entree).rglob("*") if p.is_file() and p.suffix.lower() in extract_data.EXTENSIONS)
    vues, journal = [], []
    for p in photos:
        rel = str(p.relative_to(entree))
        try:
            meta = extract_data.metadonnees(p)
            info = extract_data.parametres(p)
            t = extract_data.temperatures(p, info=info, **reglages)
        except extract_data.NonRadiometrique:
            journal.append({"photo": rel, "radiometrique": False})
            continue
        except (extract_data.ErreurMesure, ValueError, OSError) as e:
            journal.append({"photo": rel, "erreur": str(e)})
            continue
        meta["largeur"], meta["hauteur"] = t.shape[1], t.shape[0]
        mods = detecteur.analyser(t, modele)
        alertes = placer(mods, meta, hauteur_modules, f35_exif(p))
        for m in mods:
            m["photo"] = rel
        vues += mods
        journal.append({"photo": rel, "modules": len(mods), "places": sum("sol" in m for m in mods),
                        "alertes": meta["alertes"] + alertes})
    modules = fusionner(vues)
    fc = geojson(modules, tous)
    fc["metadata"] = {"mode": "exact" if exact else "photo", "seuil_K": anomalies.SEUIL_K,
                      "hauteur_modules_m": hauteur_modules, "photos": journal}
    Path(sortie).parent.mkdir(parents=True, exist_ok=True)
    Path(sortie).write_text(json.dumps(fc, ensure_ascii=False, indent=1), encoding="utf-8")
    return fc, modules


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    a.add_argument("--entree", type=Path, default=RACINE / "data" / "raw_rjpegs")
    a.add_argument("--sortie", type=Path, default=RACINE / "output" / "orthostudio_report.geojson")
    a.add_argument("--exact", action="store_true", help="températures exactes (0,85 + --reflexion obligatoire)")
    a.add_argument("--reflexion", type=float)
    a.add_argument("--hauteur-modules", type=float, default=0.0,
                   help="hauteur des modules au-dessus du sol du décollage (m), retirée de l'altitude relative")
    a.add_argument("--tous", action="store_true", help="exporter aussi les modules sains")
    o = a.parse_args(argv)
    try:
        fc, modules = traiter(o.entree, o.sortie, o.exact, o.reflexion, o.hauteur_modules, o.tous)
    except ValueError as e:
        a.error(str(e))
    n = Counter(m["forme"] for m in modules)
    print(f"{len(modules)} module(s) au sol, {sum(v for k, v in n.items() if k != 'sain')} en anomalie "
          f"({dict(n)}) → {o.sortie}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
