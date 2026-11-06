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
