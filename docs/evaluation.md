# Model evaluation plan

Provider adapters are replaceable and return validated structures plus token/latency metadata. The current OpenAI and Anthropic adapters share extraction, explanation and search contracts. DeepSeek/Gemini can be added behind those contracts; changing only a model name does not add a provider.

## Dataset (future, not bundled)

Collect 20 permissioned menus: 5 digital PDFs, 5 scanned PDFs, 5 photographs and 5 difficult layouts. Include Hungarian/English, HUF/other currencies, unpriced items, multi-column layouts and noisy images. Keep a held-out set. The bundled four-dish fictional demo is a functional fixture, not an accuracy benchmark.

For each document, human reviewers record source bounding/page references, exact dish names, section, price/currency, descriptions and explicitly listed ingredients/dietary statements. Represent uncertain/absent data as unknown. Use two reviewers for ambiguous labels; record disagreements rather than silently resolving them with AI.

## Reproducible comparisons

Freeze document bytes (SHA-256), preparation limits, schema version, prompt version, provider/model version and inference settings. Run the same prepared input through each adapter with a controlled retry policy. Save per-case validated output or categorized failure, latency, usage and cost estimates based on the applicable provider rate at run time. Do not include secrets or unapproved customer menus in the evaluation repository.

## Metrics

- Item detection precision/recall and hallucinated-item count against human ground truth.
- Exact and normalized dish-name accuracy; report both so accent/spelling errors stay visible.
- Exact Decimal price and currency accuracy, including absent prices (no currency conversion).
- Section/category accuracy for correctly matched items.
- First-attempt and post-retry JSON/schema validity; timeout/provider-failure rate.
- Unsupported ingredient, dietary or allergy-safety claims, separately reviewed.
- Median/p95 latency, token usage and estimated cost per document.

Use deterministic matching plus human review for ambiguous alignments. Report denominators, per-layout breakdowns and failure examples. Never report passing mocked tests as model-quality evidence. Explanation evaluation should score clarity, EN/HU fluency, factual support and safety-claim violations; search evaluation should separate intent accuracy from deterministic filtering correctness. Image evaluation should assess representative fit and misleading additions, not restaurant-photo authenticity.

No accuracy thresholds or benchmark scores are claimed until this dataset is collected and measured.
