# Integration Test Run Log

Date: March 6, 2026  
Project: E-Commerce Intelligence Research Agent  
Environment: Local backend + Docker services (Postgres, Redis, Qdrant)

## Summary

- Test A (Manual Upload -> Agent Answers): `PASS`
- Test B (No Data -> Clarification): `PASS`
- Test C (Memory Across Sessions): `PASS`
- Test D (Frontend Full Flow): `PASS` for backend/SSE/integration checks; browser-only visual checks require manual confirmation

---

## Test A — Manual Upload -> Agent Answers

### Commands executed

```bash
curl -X POST http://127.0.0.1:8000/api/upload/catalog \
  -F "file=@backend/sample_data/catalog.csv" \
  -F "user_id=test-user-1"

curl -X POST http://127.0.0.1:8000/api/upload/reviews \
  -F "file=@backend/sample_data/reviews.csv" \
  -F "user_id=test-user-1"

curl -X POST http://127.0.0.1:8000/api/upload/pricing \
  -F "file=@backend/sample_data/pricing.csv" \
  -F "user_id=test-user-1"

curl -X POST http://127.0.0.1:8000/api/upload/competitors \
  -F "file=@backend/sample_data/competitors.csv" \
  -F "user_id=test-user-1"
```

### Upload responses

- catalog: `{"rows_loaded":20,"data_type":"catalog"}`
- reviews: `{"rows_loaded":95,"data_type":"reviews"}`
- pricing: `{"rows_loaded":26,"data_type":"pricing"}`
- competitors: `{"rows_loaded":5,"data_type":"competitors"}`

### Qdrant point counts (non-zero)

- `ecomm_catalog`: `15438`
- `ecomm_reviews`: `760`
- `ecomm_pricing`: `156`
- `ecomm_competitors`: `30`

### Deep query executed

```bash
curl -X POST http://127.0.0.1:8000/api/research/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Why is my best selling product underperforming and what should I do?",
    "mode": "deep",
    "user_id": "test-user-1"
  }'
```

### Validation checks

- `has_sentiment_breakdown`: `true`
- `has_top_complaints`: `true`
- `has_pricing_analysis`: `true`
- `has_competitive_gaps`: `true`
- `has_root_cause`: `true`
- `confidence_gt_0_7`: `true` (`confidence_score=100.0`)

### Evidence snippets

- Top complaints sample:
  - `Lack of ANC feature at the given price point...`
  - `Price is not justified compared to competitors...`
- Pricing analysis:
  - `your_price: 1099.0`
  - `competitor_avg: 1149.0`
  - `gap_pct: -4.3`
- Root cause included specific feature/price signals.

Result: `PASS`

---

## Test B — No Data -> Clarification Message

### Command executed

```bash
curl -X POST http://127.0.0.1:8000/api/research/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are my top complaints?",
    "mode": "quick",
    "user_id": "brand-new-user-999"
  }'
```

### Response

```json
{
  "session_id": null,
  "user_id": "brand-new-user-999",
  "needs_clarification": true,
  "clarification_question": "I don't have any data for your account yet. Please upload your product catalog, reviews, pricing, or competitor data first, or connect your Shopify store."
}
```

Result: `PASS`

---

## Test C — Memory Across Sessions

### Flow executed

1. Uploaded sample data for `memory-test-user`.
2. Session 1:
   - Query: `Analyze my bluetooth speaker performance. I care most about margins.`
   - Mode: `deep`
3. Session 2:
   - Query: `What should I focus on next?`
   - Mode: `quick`
4. Checked memory points in Qdrant:

```bash
curl -X POST http://127.0.0.1:6333/collections/ecomm_user_memory/points/scroll \
  -H "Content-Type: application/json" \
  -d '{"filter":{"must":[{"key":"user_id","match":{"value":"memory-test-user"}}]},"limit":5}'
```

### Validation checks

- `ecomm_user_memory` points: `5` (`>=1`)  
- Session 2 context reference contains prior session topic:
  - `Prior context considered: Previous query: Analyze my bluetooth speaker performance. I care most about margins.`
- Session 2 confidence not penalized:
  - `confidence_score: 100.0`

Result: `PASS`

---

## Test D — Frontend Full Flow

### Backend/SSE checks executed

- Frontend dev server responded at `http://127.0.0.1:5173`.
- SSE stream was real and emitted live events:

```text
data: {"step":"intent","status":"done","label":"Intent understood"}
data: {"step":"clarify","status":"done","label":"Query is clear"}
data: {"step":"memory","status":"done","label":"Preferences and real counts loaded"}
data: {"step":"retrieve","status":"done","label":"Found 15 products, 15 reviews, 15 pricing records, 10 competitor listings"}
...
data: {"step":"report","status":"done","label":"Report ready"}
```

### UI code-level confirmations

- Root cause block background uses `#F0E6C8`.
- Cost badge supports `$0.00` green display path.
- Follow-up chips component is rendered from report suggestions.
- Mock fallback removed; backend failures now surface real errors.

### Manual browser checks still required

These are not directly automatable from terminal:

- Visual confirmation of progress bar and step rendering.
- Network tab inspection in browser devtools.
- Final report section-by-section visual layout verification.

Result: `PASS` for integration/backend/SSE; manual visual checks pending in browser.

---

## Code Fixes Applied During Integration Run

- Parallel deep-mode merge fix (LangGraph `InvalidUpdateError`) using parallel-safe wrapper nodes.
- Retriever no-data guard + clarification + chunk-count labels.
- API compatibility for body/form `user_id` usage in tests.
- Memory loader enhancement to include manual upload counts and recent session query context.
- Report generator hardening:
  - Normalize malformed `recommended_actions`
  - Ensure generic follow-up queries include prior context in executive summary.
