# Classifieur de modules — évaluation sur le jeu de test

Modèle : `models/classifier.pt` · 2002 vignettes de test (proportions réelles, jamais vues à l'entraînement)

- 6 classes du projet : exactitude 82.6%, F1 macro 75.2%
- 12 classes d'origine : exactitude 80.6%, F1 macro 67.6%
- Anomalies classées saines : 69 (6.9%) · modules sains signalés : 100 (10.0%)

| Classe du projet | n | Précision | Rappel | F1 |
|---|---:|---:|---:|---:|
| bypass_diode | 168 | 96.9% | 93.5% | 95.2% |
| cracking | 94 | 67.8% | 64.9% | 66.3% |
| hotspot | 367 | 71.3% | 77.1% | 74.1% |
| no_anomaly | 1000 | 92.9% | 90.0% | 91.4% |
| obstruction | 290 | 70.8% | 70.3% | 70.6% |
| offline_module | 83 | 50.0% | 57.8% | 53.6% |

| Classe d'origine | n | Précision | Rappel | F1 |
|---|---:|---:|---:|---:|
| Cell | 188 | 66.3% | 71.3% | 68.7% |
| Cell-Multi | 129 | 62.2% | 47.3% | 53.7% |
| Cracking | 94 | 67.3% | 70.2% | 68.8% |
| Diode | 150 | 97.3% | 95.3% | 96.3% |
| Diode-Multi | 18 | 93.3% | 77.8% | 84.8% |
| Hot-Spot | 25 | 46.2% | 72.0% | 56.2% |
| Hot-Spot-Multi | 25 | 46.7% | 56.0% | 50.9% |
| No-Anomaly | 1000 | 92.4% | 91.7% | 92.1% |
| Offline-Module | 83 | 50.0% | 59.0% | 54.1% |
| Shadowing | 106 | 68.5% | 59.4% | 63.6% |
| Soiling | 20 | 61.5% | 40.0% | 48.5% |
| Vegetation | 164 | 70.8% | 76.8% | 73.7% |

Matrice de confusion (lignes = vrai, colonnes = prédit)

| | bypass_diode | cracking | hotspot | no_anomaly | obstruction | offline_module |
|---|---|---|---|---|---|---|
| bypass_diode | 157 | 0 | 4 | 2 | 1 | 4 |
| cracking | 0 | 61 | 25 | 1 | 7 | 0 |
| hotspot | 1 | 21 | 283 | 16 | 44 | 2 |
| no_anomaly | 2 | 0 | 30 | 900 | 30 | 38 |
| obstruction | 1 | 7 | 47 | 27 | 204 | 4 |
| offline_module | 1 | 1 | 8 | 23 | 2 | 48 |
