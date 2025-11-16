# FFSC Engine Dynamics

This repository contains a Python re-implementation of the key thermodynamic and component models from Zhou Chuang's dissertation (chapter 2).

## Branch layout
- The working branch in this repository snapshot is `work`. There is no Git remote configured inside the container, so the files you see here have **not** been pushed anywhere yet.
- If you want these commits to appear on your own remote `main` branch, run `git remote add origin <your-remote-url>` followed by `git push origin work:main` (or rename the branch locally with `git branch -M main` before pushing).

## Reference material
- Supplementary notes extracted from the dissertation are stored in `docs/paper_notes/` (e.g. `chapter2_pages71_80_notes.md`).
- Outstanding data requirements that still block end-to-end simulations can be listed with `python scripts/show_missing_system_gaps.py`.

## Getting started
```
conda activate ffsc_engine_dynamics
```
