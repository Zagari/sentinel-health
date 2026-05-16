# Academic Use Notice

> **This notice is informational. It does not modify the terms of the MIT
> License under which this software is distributed — see [`LICENSE`](./LICENSE).**

## Nature of the project

**Sentinel Health** is an **academic prototype** developed as part of the
**Tech Challenge — Phase 4** of the postgraduate program in
**Artificial Intelligence for Developers** at **FIAP** — Faculdade de
Informática e Administração Paulista, Brazil.

## Not a medical device

Sentinel Health is **NOT a medical device**. It **MUST NOT** be used for:

- Clinical decisions
- Diagnosis
- Triage
- Surgical guidance in real procedures
- Victim support in real-world abuse / domestic violence cases
- Any other safety-critical or life-affecting application

## Known limitations

- The underlying machine learning models were trained on **research datasets
  with known biases and limitations** (CholecSeg8k for cholecystectomy,
  GynSurg for gynecological laparoscopy, FER2013 for facial emotion).
- The validation set for the YOLOv8m bleeding detector is small (20 clips,
  ~1,800 frames) — generalization beyond similar gynecological laparoscopy
  is not characterized.
- False positive rate of ~13% on the bleeding detector means roughly 1 in 7
  non-bleeding clips raises an alert. A **human-in-the-loop** is always
  required.
- Voice / face emotion analysis is **not validated** against any clinical
  reference standard.
- LLM-based summarization may hallucinate, miss context, or reflect biases
  present in its training corpus.

## Responsible interpretation

Any interpretation of system outputs requires **qualified medical
professionals**. The platform's outputs should be treated as **research-grade
signals**, not as clinical evidence.

## Authors / Team — Grupo Sala 14

- Adriana Martins de Souza — RM 368050
- Diego Oliveira da Silva — RM 367964
- Eduardo Nicola F. Zagari — RM 368021
- Renan de Assis Torres — RM 368513

## Submission

FIAP Tech Challenge — Phase 4 · 2026-05
