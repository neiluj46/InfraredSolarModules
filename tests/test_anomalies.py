"""Seuil d'écart (scripts/anomalies.py) avant le classifieur, sur des modules synthétiques."""

import sys
from pathlib import Path

import numpy as np
import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
torch = pytest.importorskip("torch")
import anomalies as an  # noqa: E402

pytestmark = pytest.mark.skipif(not (RACINE / "models" / "classifier.pt").is_file(), reason="modèle absent")


@pytest.fixture(scope="module")
def modele():
    return an.charger_modele()


def module(chaud=0.0, forme=(120, 72), graine=0):
    """Module à 35 °C ± 0,3 K de bruit ; `chaud` K de plus sur un bloc d'une cellule (≈ 1/60 du module)."""
    t = 35 + np.random.default_rng(graine).normal(0, 0.3, forme)
    if chaud:
        h, l = forme
        t[h // 3:h // 3 + h // 10, l // 2:l // 2 + l // 6] += chaud
    return t.astype(np.float32)


def test_ecart_interne():
    assert an.ecart_interne(module()) < 1.5
    assert an.ecart_interne(module(chaud=10)) > 8
    t = module(chaud=10)
    t[0, :5] = np.nan
    assert np.isfinite(an.ecart_interne(t))


def test_uniforme_sous_le_seuil(modele):
    r = an.classer([module(graine=g) for g in range(5)], modele)
    assert all(x["classe"] == "no_anomaly" and x["motif"].startswith("écart") for x in r)
    assert all(x["confiance"] is None and x["classe_ia"] in an.CLASSES for x in r)


def test_point_chaud_consulte_le_classifieur(modele):
    r = an.classer([module(chaud=15)], modele)[0]
    assert r["ecart_K"] >= an.SEUIL_K and r["motif"] == "classifieur"
    assert r["classe"] == r["classe_ia"] and 0 < r["confiance"] <= 1


def test_seuil_reglable(modele):
    t = module(chaud=4)
    assert an.classer([t], modele)[0]["motif"] == "classifieur"
    assert an.classer([t], modele, seuil=10)[0]["classe"] == "no_anomaly"


def test_vignette_paysage_et_vide(modele):
    assert an.vignette(module(forme=(72, 120))).shape == (an.HAUTEUR, an.LARGEUR)
    assert an.vignette(module()).shape == (an.HAUTEUR, an.LARGEUR)
    assert an.classer([], modele) == []


# ------------------------------------------------------------------ forme (option A)

def test_formes_synthetiques():
    assert an.decrire(module())["forme"] == "sain"
    assert an.decrire(module(chaud=10))["forme"] == "point_chaud"
    t = module()
    t[:, 48:] += 6                                                    # tiers droit entier chaud
    assert an.decrire(t)["forme"] == "sous_chaine_chaude"
    t = module()
    for y, x in ((10, 0), (60, 12), (90, 0)):                         # trois cellules, même tiers
        t[y:y + 12, x:x + 12] += 10
    r = an.decrire(t)
    assert r["forme"] == "diode_possible" and max(r["tiers"]) >= 0.9 and r["zones"] == 3
    t = module()
    for y, x in ((10, 0), (60, 60), (90, 30)):                        # trois cellules, trois tiers
        t[y:y + 12, x:x + 12] += 10
    assert an.decrire(t)["forme"] == "cellules_chaudes"


def test_forme_paysage():
    t = module()
    t[:, 48:] += 6
    assert an.decrire(np.rot90(t))["forme"] == "sous_chaine_chaude"


def test_modules_chauds():
    assert an.modules_chauds([30, 30.5, 36, 29.8]) == [2]
    assert an.modules_chauds([30, 30.5, 31, 29.8]) == []
    assert an.modules_chauds([30, 40]) == []                          # trop peu de voisins
    assert set(an.FORMES) >= {"sain", "point_chaud", "diode_possible", "module_chaud"}
