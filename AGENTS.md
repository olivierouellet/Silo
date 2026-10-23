# Agent instructions

For AI coding assistants (Claude Code, GitHub Copilot, Codex, Cursor and others) working in this repository.
People should start with [CONTRIBUTING.md](CONTRIBUTING.md).

## What this is

A Home Assistant custom integration (`custom_components/silo`, distributed through HACS) that turns a
distance sensor at the top of a grain silo into its fill level, grain height, volume, weight and room left.
The companion card is [Silo Card](https://github.com/olivierouellet/Silo-Card): it draws the silo from the
fill sensor's `silo` attribute, so the silo is described only once, here.

## Before you finish

```bash
uv venv --python 3.13 && uv pip install -r requirements_test.txt   # once
ruff check && ruff format --check
pytest
```

All must pass; CI runs the same, plus HACS and hassfest validation.

## Conventions

* **English first.** Every document is bilingual, English section first; a change users see goes in both.
* `strings.json` is English and is copied unchanged to `translations/en.json`; `translations/fr.json` has
  the same keys. A test enforces both.
* `geometry.py` is mirrored in Silo Card's `src/geometry.ts`, `src/silo.ts` and `src/units.ts`, and the tests
  in `tests/test_geometry.py` hold the same numbers as the card's: change one, change the other.
* The options use Silo Card's option names (`diameter`, `ring_height`, `top`…): the fill sensor's `silo`
  attribute is read by the card as is. Renaming one breaks the card.
* The integration never smooths or corrects the sensor: filtering belongs in the sensor (see the ESPHome
  example in Silo Card).
* The manifest has no `requirements`; keep it that way. Python 3.13.
* A release bumps `version` in `manifest.json` in a commit titled `[Integration] Version X.Y.Z`, then a
  GitHub release tagged `vX.Y.Z`.
* The icon's source is `assets/icon.svg`; `brand/icon.png` (256 px) and `brand/icon@2x.png` (512 px) are
  exported from it.

## Commits and publishing

* Commit titles read `[Topic] What changed`, one topic per commit. Topics in use: `[Integration]`, `[Tests]`, `[Tooling]`, `[Docs]`.
* **Never commit, push, tag, publish a release, or open an issue or pull request unless asked.** Approval for
  one of these is not approval for the next.
* `main` is protected against force-pushes and deletion: never rewrite history that is already pushed.
* Never post comments on issues or pull requests on the user's behalf without their review.

## AI policy

This project follows its [AI policy](AI_POLICY.md): a person reviews and understands every change, no
autonomous contributions, and nothing is posted on someone's behalf without their review.
