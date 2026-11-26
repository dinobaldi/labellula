# Licenze di terze parti

Labellula è distribuito con licenza **GNU AGPL-3.0** (vedi [LICENSE](../LICENSE)). Usa programmi, modelli e dati di altri, ognuno con la sua licenza. Labellula **non include** né ridistribuisce i modelli: li scarica Ollama sul tuo computer, dalla libreria di Ollama.

## Modelli di intelligenza artificiale

| Modello | A cosa serve | Licenza |
|---|---|---|
| `qwen3-vl:8b-instruct`, `qwen3-vl:4b-instruct` (Alibaba, Qwen) | descrizione delle foto | Apache-2.0 |
| `bge-m3` (BAAI) | ricerca per significato | MIT |

La licenza esatta di ogni modello si legge con `ollama show <modello> --license`.

## Programmi e librerie

| Componente | A cosa serve | Licenza |
|---|---|---|
| [Ollama](https://ollama.com) | esegue i modelli sul computer | MIT |
| Python | linguaggio | PSF |
| Pillow | immagini | MIT-CMU (HPND) |
| pillow-heif (con libheif) | foto HEIC | BSD-3-Clause (libheif: LGPL-3.0) |
| NumPy, SciPy | calcoli | BSD-3-Clause |
| ImageHash | impronta per i doppioni | BSD-2-Clause |
| PyYAML | configurazione | MIT |
| requests | collegamento a Ollama | Apache-2.0 |
| reverse_geocoder | luogo dalle coordinate GPS, senza internet | LGPL-2.1 |
| exiftool (facoltativo) | lettura dei dati EXIF | Artistic / GPL |

## Dati

| Dati | Licenza | Attribuzione |
|---|---|---|
| Elenco delle località (`rg_cities1000.csv`, incluso in reverse_geocoder) | CC BY 4.0 | Dati da [GeoNames](https://www.geonames.org/), CC BY 4.0 |

## Modulo volti (facoltativo, non incluso in questa versione)

Alcuni modelli pre-addestrati per il riconoscimento dei volti sono rilasciati **solo per uso non commerciale** o di ricerca. Prima di usarli in un contesto commerciale, verificane la licenza.

## Loghi e foto di esempio

- I loghi di **ctrlalt.museum** e **comPVter** sono marchi dell'associazione culturale comPVter: non sono coperti dalla licenza del codice.
- Le foto in `examples/` sono di Dino Baldi, tranne `demo/…/Olivetti_Programma_101.jpg`, che è di ctrlalt.museum (associazione comPVter APS). Tutte con licenza [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.it): si possono riusare citando «Foto di Dino Baldi – Labellula» o, per la Programma 101, «Foto ctrlalt.museum – Labellula».
