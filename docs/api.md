# API documentation

Swagger/OpenAPI is served by the running application at `/docs` and `/openapi.json`.
All paths are versioned under `/api/v1` and return structured validation or business-rule errors:

```json
{"error": {"code": "business_rule_violation", "message": "Insufficient withdrawable balance"}}
```

| Method and path | Request highlights | Result |
| --- | --- | --- |
| `POST /users` | `username` | Creates user and account-balance projection. |
| `POST /brands` | `name` | Creates unique brand. |
| `POST /sales` | `user_id`, `brand_id`, decimal `earning` | Creates a `pending` sale only. |
| `POST /jobs/advance-payouts/run` | Internal key | Runs idempotent 10% advance settlement. |
| `PATCH /sales/{id}/reconciliation` | `status`: `approved` or `rejected`; internal key | Performs final financial adjustment once. |
| `GET /users/{id}/balance` | none | Current signed withdrawable balance. |
| `POST /withdrawals` | `user_id`, decimal `amount`, optional `retry_of_id`; `Idempotency-Key` | Debits available balance and creates initiated withdrawal. |
| `POST /withdrawals/{id}/provider-status` | unique event ID and terminal status; internal key | Finalizes payout and reverses money on failure states. |

Internal endpoints require `X-Internal-API-Key`. `Idempotency-Key` is required for every new
withdrawal and must be stable across a caller retry.
