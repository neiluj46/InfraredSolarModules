"""Projection au sol, fusion des vues et GeoJSON (scripts/export_orthostudio.py)."""

import math
import sys
from pathlib import Path

import numpy as np
import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
pytest.importorskip("torch")
import export_orthostudio as ex  # noqa: E402

ORTHOSTUDIO = Path.home() / "OrthoStudio_test"


@pytest.mark.skipif(not (ORTHOSTUDIO / "georef" / "camera.py").is_file(), reason="OrthoStudio absent")
@pytest.mark.parametrize("angles", [(0, -90, 0), (37, -90, 0), (-120, -70, 2), (200, -45, -3)])
def test_rotation_identique_a_orthostudio(angles):
    sys.path.insert(0, str(ORTHOSTUDIO))
    from georef.camera import rotation_dji
    assert np.allclose(ex.rotation_dji(*angles), rotation_dji(*angles))


def test_nadir_orientation_et_echelle():
    f, _ = ex.focale_px({"largeur": 640, "hauteur": 512, "modele": "M3T"})
    cx, cy = 319.5, 255.5
    R = ex.rotation_dji(0, -90, 0)                                   # haut de l'image vers le nord
    e, n = ex.vers_sol([cx + 100, cx, cx], [cy, cy - 100, cy], f, cx, cy, R, 30)
    assert e[0] > 0 and abs(n[0]) < 1e-9                             # droite = est
    assert n[1] > 0 and abs(e[1]) < 1e-9                             # haut = nord
    assert abs(e[2]) < 1e-9 and abs(n[2]) < 1e-9                     # centre à l'aplomb
    e, n = ex.vers_sol([0, 639], [0, 511], f, cx, cy, R, 30)          # diagonale au sol = 2 h tan(DFOV / 2)
    assert math.hypot(e[1] - e[0], n[1] - n[0]) == pytest.approx(2 * 30 * math.tan(math.radians(30.5)), rel=0.01)
    R = ex.rotation_dji(90, -90, 0)                                  # cap à l'est : haut de l'image = est
    e, n = ex.vers_sol([cx], [cy - 100], f, cx, cy, R, 30)
    assert e[0] > 0 and abs(n[0]) < 1e-9


def test_visee_oblique_et_horizon():
    f, _ = ex.focale_px({"largeur": 640, "hauteur": 512, "modele": "M3T"})
    R = ex.rotation_dji(0, -45, 0)
    e, n = ex.vers_sol([319.5], [255.5], f, 319.5, 255.5, R, 30)
    assert n[0] == pytest.approx(30) and abs(e[0]) < 1e-9            # 45° : autant devant que de hauteur
    R = ex.rotation_dji(0, 0, 0)                                     # horizontal : le haut de l'image ne touche pas le sol
    e, n = ex.vers_sol([319.5], [0], f, 319.5, 255.5, R, 30)
    assert np.isnan(e[0])


def test_focales():
    assert ex.focale_px({"largeur": 640, "hauteur": 512, "modele": "M4T"})[1].startswith("DFOV DJI 45")
    f, s = ex.focale_px({"largeur": 640, "hauteur": 512, "modele": "ZH20T"}, 58)
    assert "équivalente 58" in s and f == pytest.approx(math.hypot(640, 512) * 58 / math.hypot(36, 24))
    assert "hypothèse" in ex.focale_px({"largeur": 640, "hauteur": 512, "modele": "?"})[1]


def test_wgs84_aller_retour():
    lon, lat = ex.vers_wgs84(44.5, 1.4, [100.0, -250.0], [50.0, 300.0])
    e, n = ex.depuis_wgs84(44.5, 1.4, lon, lat)
    assert np.allclose(e, [100, -250], atol=1e-6) and np.allclose(n, [50, 300], atol=1e-6)
    _, lat1 = ex.vers_wgs84(44.5, 1.4, 0, 111_120)                   # ~1° de latitude
    assert lat1 - 44.5 == pytest.approx(1.0, abs=0.005)


def module(cx, cy, forme="sain"):
    return {"cx": cx, "cy": cy, "coins": [[cx - 30, cy - 18], [cx + 30, cy - 18], [cx + 30, cy + 18], [cx - 30, cy + 18]],
            "forme": forme, "libelle": forme, "ecart_K": 5.0 if forme != "sain" else 0.5, "t_max": 40.0,
            "t_moyenne": 30.0, "dT_voisins": 0.1}


def meta(lat=44.5, lon=1.4, yaw=0.0):
    return {"largeur": 640, "hauteur": 512, "modele": "M3T", "lat": lat, "lon": lon, "alt_rel": 30.0,
            "nacelle": [yaw, -90.0, 0.0], "vol": [yaw, 0, 0]}


def deux_vues(forme_a, forme_b):
    """Même module vu sur deux photos : la 2ᵉ prise 5 m plus au nord, le module y est 5 m plus bas dans l'image."""
    f, _ = ex.focale_px(meta())
    px = 5 * f / 30
    a, b = [module(400, 200, forme_a), module(150, 150)], [module(400, 200 + px, forme_b)]
    ex.placer(a, meta())
    ex.placer(b, meta(lat=float(ex.vers_wgs84(44.5, 1.4, 0.0, 5.0)[1])))
    for m in a:
        m["photo"] = "a.JPG"
    for m in b:
        m["photo"] = "b.JPG"
    return a + b


def test_placer_alertes():
    mods = [module(320, 256)]
    al = ex.placer(mods, {**meta(), "lat": None})
    assert "pas de position" in al[0] and "sol" not in mods[0]
    mods = [module(320, 256)]
    al = ex.placer(mods, {**meta(), "nacelle": None})
    assert any("cap du drone" in x for x in al) and "sol" in mods[0]
    assert mods[0]["sol"]["largeur_m"] == pytest.approx(36 * 30 / ex.focale_px(meta())[0], rel=0.01)


def test_fusion_confirmation():
    m = ex.fusionner(deux_vues("point_chaud", "point_chaud"))
    chauds = [x for x in m if x["forme"] != "sain"]
    assert len(m) == 2 and len(chauds) == 1
    assert chauds[0]["vues"] == 2 and chauds[0]["confirmee"]
    m = ex.fusionner(deux_vues("point_chaud", "sain"))                # vu une fois sur deux : reflet ?
    x = [x for x in m if x["vues"] == 2][0]
    assert x["vues_anomalie"] == 1 and (x["forme"] == "sain" or not x["confirmee"])


def test_geojson():
    m = ex.fusionner(deux_vues("diode_possible", "diode_possible"))
    fc = ex.geojson(m)
    assert fc["type"] == "FeatureCollection" and len(fc["features"]) == 1
    f = fc["features"][0]
    anneau = f["geometry"]["coordinates"][0]
    assert len(anneau) == 5 and anneau[0] == anneau[-1]
    assert all(1.39 < lon < 1.41 and 44.49 < lat < 44.51 for lon, lat in anneau)
    p = f["properties"]
    assert p["forme"] == "diode_possible" and p["confirmee"] and {"T_max", "T_mean", "dT"} <= set(p)
    assert len(ex.geojson(m, tous=True)["features"]) == 2


@pytest.mark.skipif(not (RACINE / "models" / "detector.pt").is_file()
                    or not (RACINE / "dji_sdk" / "samples" / "M3T").is_dir(), reason="modèle ou SDK absent")
def test_traiter_exemples_dji(tmp_path):
    """Chaîne complète sur les exemples DJI (sans GPS ni XMP) : rien ne plante, les alertes sont dites."""
    import shutil
    e = tmp_path / "vol"
    shutil.copytree(RACINE / "dji_sdk" / "samples" / "M3T", e)
    fc, modules = ex.traiter(e, tmp_path / "r.geojson")
    assert (tmp_path / "r.geojson").is_file() and fc["features"] == [] and modules == []
    j = fc["metadata"]["photos"]
    assert len(j) == 5 and all("pas de position GPS" in " ".join(x["alertes"]) for x in j)
