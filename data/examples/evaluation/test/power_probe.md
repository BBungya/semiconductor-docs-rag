---
document_id: eval-power-probe
title: "Synthetic power probe schedule"
version: "1.0"
language: en
fictional: true
---

# Synthetic power probe schedule

## Sampling schedule
| Mode | Sampling interval (ms) | Hold duration (s) |
| --- | ---: | ---: |
| Ember | 36 | 18 |
| Frost | 84 | 27 |

## Exception handling
If the sync pulse is missing, freeze the reading and mark it stale. Resume live sampling only after two consecutive valid pulses.
