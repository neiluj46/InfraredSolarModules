"""Étape 2 (scripts/extract_data.py) sur les exemples du SDK DJI (dji_sdk/samples/, installés par
scripts/install_dji_sdk.sh, non versionnés) : sautés si dji_irp ou les exemples manquent."""

import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
import extract_data as ed  # noqa: E402

EXEMPLES = RACINE / "dji_sdk" / "samples"
M3T = EXEMPLES / "M3T" / "DJI_0001_R.JPG"
M4T = EXEMPLES / "M4T" / "DJI_0001_R.JPG"

try:
    ed.outil()
    PRET = M3T.is_file() and M4T.is_file()
except FileNotFoundError:
    PRET = False
pytestmark = pytest.mark.skipif(not PRET, reason="SDK DJI non installé (scripts/install_dji_sdk.sh)")


def test_parametres_et_plages():
    info = ed.parametres(M3T)
    assert (info["width"], info["height"]) == (640, 512)
    assert info["measurement_params"]["emissivity"] == pytest.approx(0.95)
    assert info["measurement_ranges"]["distance"] == [1, 25]          # M3T : 25 m au plus
    assert ed.parametres(M4T)["measurement_ranges"]["distance"] == [1, 300]


def test_mode_photo_par_defaut():
    info = ed.parametres(M3T)
    eff = ed.reglages_effectifs(info, **ed.reglages_mode())
    photo = info["measurement_params"]
    assert eff == {"emissivite": photo["emissivity"], "distance": photo["distance"],
                   "humidite": photo["humidity"], "reflexion": photo["reflection"]}


def test_mode_exact():
    with pytest.raises(ValueError, match="réfléchie"):
        ed.reglages_mode(exact=True)
    r = ed.reglages_mode(exact=True, reflexion=-20)
    assert r == {"emissivite": 0.85, "distance": None, "humidite": None, "reflexion": -20}
    assert ed.reglages_mode(exact=True, reflexion=-20, emissivite=0.9)["emissivite"] == 0.9


def test_plage_refusee_avant_mesure():
    info = ed.parametres(M3T)
    with pytest.raises(ValueError, match="hors de la plage"):
        ed.reglages_effectifs(info, distance=40)
    assert ed.reglages_effectifs(ed.parametres(M4T), distance=40)["distance"] == 40


def test_temperatures():
    t = ed.temperatures(M3T)
    assert t.shape == (512, 640) and t.dtype == np.float32
    assert 20 < float(np.median(t)) < 45 and np.isfinite(t).all()
    # 0,85 seule : écarts amplifiés d'environ 1/0,85 × (petite correction), températures plus hautes
    t85 = ed.temperatures(M3T, emissivite=0.85)
    assert float(np.median(t85)) > float(np.median(t))
    rapport = (t85.max() - np.median(t85)) / (t.max() - np.median(t))
    assert 1.05 < rapport < 1.25
    # température réfléchie basse (ciel clair) : les températures montent encore
    t_ciel = ed.temperatures(M3T, emissivite=0.85, reflexion=-20)
    assert float(np.median(t_ciel)) > float(np.median(t85))


def test_metadonnees_exemple():
    m = ed.metadonnees(M3T)
    assert m["fabricant"] == "DJI" and m["modele"] == "M3T"
    assert (m["largeur"], m["hauteur"]) == (640, 512)
    assert m["date"] and m["date"].startswith("20")


def test_lot(tmp_path):
    entree = tmp_path / "vol"
    (entree / "thermique").mkdir(parents=True)
    for f in (M3T, M4T):
        (entree / "thermique" / f"{f.parent.name}.JPG").write_bytes(f.read_bytes())
    Image.new("RGB", (64, 48)).save(entree / "DJI_0002_V.JPG")          # visible du même vol
    (entree / "abime.jpg").write_bytes(b"pas une image")
    base = ed.traiter(entree, tmp_path / "sortie", npy=True)
    par_nom = {m["fichier"]: m for m in base}
    assert len(base) == 4
    assert par_nom["DJI_0002_V.JPG"]["radiometrique"] is False and "erreur" not in par_nom["DJI_0002_V.JPG"]
    assert "illisible" in par_nom["abime.jpg"]["erreur"]
    m = par_nom["thermique/M3T.JPG"]
    assert m["radiometrique"] and m["mode"] == "photo" and m["reglages"]["emissivite"] == pytest.approx(0.95)
    assert np.load(tmp_path / "sortie" / m["matrice"]).shape == (512, 640)
    relu = json.loads((tmp_path / "sortie" / "metadata_db.json").read_text(encoding="utf-8"))
    assert [x["fichier"] for x in relu] == [x["fichier"] for x in base]


def test_lot_exact(tmp_path):
    entree = tmp_path / "vol"
    entree.mkdir()
    (entree / "a.JPG").write_bytes(M3T.read_bytes())
    with pytest.raises(ValueError):
        ed.traiter(entree, tmp_path / "s", exact=True)
    m = ed.traiter(entree, tmp_path / "s", exact=True, reflexion=-20)[0]
    assert m["mode"] == "exact" and m["reglages"]["emissivite"] == 0.85 and m["reglages"]["reflexion"] == -20


def test_main_exact_sans_reflexion(tmp_path):
    with pytest.raises(SystemExit) as e:
        ed.main(["--entree", str(tmp_path), "--sortie", str(tmp_path / "s"), "--exact"])
    assert e.value.code == 2
