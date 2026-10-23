# Contributing · Contribuer

**[English](#english) · [Français](#français)**

---

## English

Thanks for your interest! By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md). Using AI tools? Read the [AI policy](AI_POLICY.md).
Issues and pull requests are welcome in English or French.

### Setup

```bash
uv venv --python 3.13
uv pip install -r requirements_test.txt
pytest
ruff check && ruff format --check
```

### Conventions

* **Interface text**: `strings.json` (English), copied as is to `translations/en.json`, and
  `translations/fr.json`. A test checks that both have every key.
* **Geometry**: `geometry.py` is mirrored in Silo Card (`src/geometry.ts`, `src/silo.ts`, `src/units.ts`), and
  both have the same tests. A change to one goes in the other, in a pull request to each repository.
* **Documentation** is bilingual, English then French.
* **Commits**: `[Topic] What changed`, one topic each (for example `[Integration]`, `[Docs]`, `[Tooling]`).

---

## Français

Merci de votre intérêt! En participant, vous acceptez le [code de conduite](CODE_OF_CONDUCT.md). Vous utilisez l’IA? Lisez la [politique sur l’IA](AI_POLICY.md).
Les issues et les demandes de tirage sont bienvenues en anglais ou en français.

### Installation

```bash
uv venv --python 3.13
uv pip install -r requirements_test.txt
pytest
ruff check && ruff format --check
```

### Conventions

* **Textes de l’interface** : `strings.json` (anglais), copié tel quel dans `translations/en.json`, et
  `translations/fr.json`. Un test vérifie que les deux ont toutes les clés.
* **Géométrie** : `geometry.py` a son double dans Silo Card (`src/geometry.ts`, `src/silo.ts`, `src/units.ts`),
  et les deux ont les mêmes tests. Un changement à l’un va dans l’autre, par une demande de tirage dans chaque dépôt.
* **La documentation** est bilingue, l’anglais puis le français.
* **Commits** : `[Sujet] Ce qui a changé`, un sujet par commit (par exemple `[Integration]`, `[Docs]`, `[Tooling]`).
