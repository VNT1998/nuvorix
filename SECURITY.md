# Security Policy

Nuvorix is engineered for production workloads where data segregation, model governance, and runtime authorization are paramount. We take vulnerabilities and potential security regressions seriously.

---

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

---

## Reporting a Vulnerability

If you discover a security vulnerability or believe you have found a sensitive invariant flaw (e.g., cross-tenant data exposure, unauthorized tool execution, or release gate bypasses):

1. **Do not create a public GitHub issue.**
2. Send an email to the security response team at **security@nuvorix.local** (or repository maintainer).
3. Include:
   - Type of vulnerability (e.g., cross-tenant idempotency collision, auth header bypass, LLM prompt injection).
   - Detailed step-by-step reproduction instructions or proof-of-concept payload.
   - Potential impact and recommended remediation.
4. You will receive an acknowledgment within **48 hours**, followed by regular progress updates until resolved.

---

## Security Invariants Enforced in Nuvorix

- **Zero Dev-Auth Leakage in Production**: Headers such as `X-User-Role` and `X-User-Id` are rejected when `ENVIRONMENT=production`. Only cryptographically signed JWT tokens or hashed API keys are accepted.
- **Fail-Closed Provider Gateways**: In production mode, failing LLM providers raise an explicit exception rather than silently falling back to insecure deterministic mock generators.
- **Circuit Breaker Specificity**: Destructive actions (e.g., tripping emergency circuit breakers) require explicit target resource IDs, operator reason logging, and explicit confirmation flags (`confirmed=True`).
- **Secret Hygiene**: Pre-commit hooks (`gitleaks`) and CI scans run automatically on every pull request to detect accidental secret leaks.
