---
document_id: eval-sensor-queue
title: "Synthetic sensor queue dispatch"
version: "1.0"
language: en
fictional: true
---

# Synthetic sensor queue dispatch

## Dispatch rules
| Lane | Dispatch interval (ms) | Buffer limit (frames) |
| --- | ---: | ---: |
| Aurora | 45 | 120 |
| Brisk | 75 | 180 |

## Overflow policy
When the queue is full, discard only the oldest untagged frame. If every frame is tagged, pause intake and retain them all.
