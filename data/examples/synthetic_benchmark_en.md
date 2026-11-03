---
document_id: example-benchmark-en-v1
title: "Synthetic inference benchmark"
version: "1.0"
language: en
created_date: 2026-11-03
fictional: true
---

# Synthetic inference benchmark

> 🧪 이 프로젝트를 위해 직접 작성한 가상 예제입니다. 제품명·수치·운영 정책은 테스트용이며 실제 기업의 제품, 실험 결과 또는 권장 설정을 나타내지 않습니다.

## Scope

All numbers in this document are invented test fixtures. No benchmark was executed. The labels baseline and tiered-cache describe fictional configurations; they do not identify a real vendor, device, implementation, or measured system.

## Scenario

The fictional scenario uses one GPU, batch size 8, an input length of 2,048 tokens per request, and an output length of 128 tokens per request. These scenario fields are labels for retrieval tests, not evidence of reproducible measurements. The GPU model, software stack, concurrency, warm-up procedure, and trial count are unspecified.

## Result table

| Configuration | Throughput (tokens/s) | p95 TTFT (ms) |
| --- | ---: | ---: |
| baseline | 145 | 1200 |
| tiered-cache | 172 | 900 |

The fictional throughput increase is (172 - 145) / 145 × 100, approximately 18.6%. The fictional p95 TTFT reduction is (1200 - 900) / 1200 × 100, or 25%.

## Limitations

This table supports example questions about units, arithmetic, and conditions. It provides no evidence that caching, CXL, or any actual product improves performance. Do not combine these values with the separate synthetic memory specification to infer a causal relationship.
