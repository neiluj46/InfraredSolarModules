"""Géométrie des modules (scripts/detecteur.py) et cibles du détecteur (scripts/train_detector.py)."""

import math
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
pytest.importorskip("torch")
import detecteur as de  # noqa: E402
import train_detector as td  # noqa: E402


def rectangle_image(deg, a=80, b=48, n=200, chaud=None):
    yy, xx = np.mgrid[0:n, 0:n] - n / 2
    th = math.radians(deg)
    u, v = xx * math.cos(th) + yy * math.sin(th), -xx * math.sin(th) + yy * math.cos(th)
    im = np.where((abs(u) < a / 2) & (abs(v) < b / 2), 40.0, 20.0)
    if chaud:
        im[(abs(u - a / 4) < 4) & (abs(v) < 4)] += chaud           # 8 × 8 px ≈ 1,7 % : une cellule
    return ndimage.gaussian_filter(im, 1), a * abs(math.cos(th)) + b * abs(math.sin(th)), \
        a * abs(math.sin(th)) + b * abs(math.cos(th))


@pytest.mark.parametrize("deg", [0, 10, 25, 60, 80, 100, 170])
def test_angle_et_rectangle(deg):
    im, w, h = rectangle_image(deg)
    th = de.angle_local(im, 100, 100, w, h)
    a, b, incertain = de.rectangle(w, h, th)
    assert not incertain
    assert sorted([a, b]) == pytest.approx([48, 80], abs=2)
    assert abs((math.degrees(th) - deg + 45) % 90 - 45) < 1.5


def test_proportions_vers_45():
    th = math.radians(45)
    w = h = 80 * math.cos(th) + 48 * math.sin(th)
    assert de.rectangle(w, h, th)[2]                                   # mal conditionné seul
    assert sorted(de.rectangle_proportions(w, h, th, 80 / 48)) == pytest.approx([48, 80], abs=0.5)


def test_decouper_et_decrire():
    im, w, h = rectangle_image(25, chaud=10)
    th = de.angle_local(im, 100, 100, w, h)
    a, b, _ = de.rectangle(w, h, th)
    if b > a:
        a, b, th = b, a, th + math.pi / 2
    m = {"cx": 100, "cy": 100, "angle_deg": math.degrees(th) % 180, "longueur": a, "largeur": b}
    z = de.decouper(im, m)
    assert z.shape[0] > z.shape[1]                                     # portrait
    assert np.median(z) == pytest.approx(40, abs=0.5)                 # sans le fond à 20 °C
    assert de.anomalies.decrire(z)["forme"] == "point_chaud"


def test_cibles():
    cadres = np.array([[64, 64, 40, 24], [300, 10, 40, 24]], np.float32)  # le second hors de l'image
    c, t, m = td.cibles(cadres, 128, 128)
    assert c.shape == (32, 32) and m.sum() == 1 and c[16, 16] == 1
    assert t[:, 16, 16] == pytest.approx([40 / 16, 24 / 16])


def test_iou_cadres():
    a = np.array([[10, 10, 10, 10]], float)
    assert td.iou_cadres(a, a)[0, 0] == pytest.approx(1)
    assert td.iou_cadres(a, np.array([[15, 10, 10, 10]], float))[0, 0] == pytest.approx(1 / 3)


@pytest.mark.skipif(not (RACINE / "models" / "detector.pt").is_file() or not (td.DONNEES / "test").is_dir(),
                    reason="détecteur non entraîné ou jeu Zenodo absent")
def test_analyser_image_reelle():
    """Image du jeu de test Zenodo en pseudo-températures (15-45 °C) : point chaud d'une cellule collé sur un
    module, un autre module chauffé de 8 K partout ; les autres modules entiers doivent rester sains."""
    from PIL import Image

    f = sorted((td.DONNEES / "test" / "images").glob("*.jpg"))[12]
    t = 15 + np.asarray(Image.open(f).convert("L"), dtype=np.float64) / 255 * 30
    modele = td.charger_modele()
    mods = [m for m in de.detecter(t, modele) if m["complet"]]
    assert len(mods) >= 20
    a, b = mods[len(mods) // 3], mods[2 * len(mods) // 3]
    r = int(0.06 * a["largeur"]) + 1
    t[int(a["cy"]) - r:int(a["cy"]) + r, int(a["cx"]) - r:int(a["cx"]) + r] += 15
    yy, xx = np.mgrid[0:t.shape[0], 0:t.shape[1]]
    th = math.radians(b["angle_deg"])
    u = (xx - b["cx"]) * math.cos(th) + (yy - b["cy"]) * math.sin(th)
    v = -(xx - b["cx"]) * math.sin(th) + (yy - b["cy"]) * math.cos(th)
    t[(abs(u) < b["longueur"] / 2) & (abs(v) < b["largeur"] / 2)] += 8
    res = de.analyser(t, modele)
    proche = lambda m: min(res, key=lambda q: math.hypot(q["cx"] - m["cx"], q["cy"] - m["cy"]))  # noqa: E731
    assert proche(a)["forme"] in ("point_chaud", "cellules_chaudes", "diode_possible")
    assert proche(b)["forme"] == "module_chaud"
    autres = [q for q in res if q is not proche(a) and q is not proche(b)]
    assert np.mean([q["forme"] == "sain" for q in autres]) >= 0.9


def test_entrainement_eclair_et_reprise(tmp_path, monkeypatch):
    """Cinq époques d'un pas sur deux images synthétiques, arrêt simulé après le point de reprise, puis reprise."""
    import torch

    rng = np.random.default_rng(0)
    jeu = []
    for _ in range(2):
        img = rng.normal(0, 0.1, (256, 256)).astype(np.float32)
        b = np.array([[64, 64, 40, 24], [180, 150, 40, 24]], np.float32)
        for cx, cy, w, h in b:
            img[int(cy - h / 2):int(cy + h / 2), int(cx - w / 2):int(cx + w / 2)] += 2
        jeu.append((td.standardiser(img), b))
    monkeypatch.setattr(td, "charger", lambda dossier, part: jeu)
    monkeypatch.setattr(td, "SORTIE", tmp_path / "sortie")
    monkeypatch.setattr(td, "MODELES", tmp_path / "modeles")
    torch.set_num_threads(2)
    vrai_save = torch.save

    def save_puis_arret(obj, chemin):                      # arrêt brutal juste après le point de reprise
        vrai_save(obj, chemin)
        if Path(chemin).name == "detector_reprise.pt":
            raise KeyboardInterrupt

    monkeypatch.setattr(td.torch, "save", save_puis_arret)
    with pytest.raises(KeyboardInterrupt):
        td.entrainer(None, epochs=6, lot=2, negatifs=None)
    assert (tmp_path / "sortie" / "detector_reprise.pt").is_file()
    monkeypatch.setattr(td.torch, "save", vrai_save)
    chemin = td.entrainer(None, epochs=6, lot=2, negatifs=None)
    ck = torch.load(chemin, weights_only=True)
    assert [h["epoch"] for h in ck["historique"]] == [1, 2, 3, 4, 5, 6]
    assert not (tmp_path / "sortie" / "detector_reprise.pt").exists()
    assert td.charger_modele(chemin) is not None
