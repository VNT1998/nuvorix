# Contributing to Nuvorix

Thank you for your interest in contributing to Nuvorix! This project follows production-grade engineering practices, strict architectural invariants, and automated quality gates.

---

## Code of Conduct

All contributors are expected to uphold respectful, inclusive, and professional communication across issues, pull requests, and discussions.

---

## Development Setup

### Prerequisites
- **Python**: 3.12+ (managed with [`uv`](https://docs.astral.sh/uv/))
- **Node.js**: 20+ with `npm`
- **Docker & Docker Compose** (for multi-service local testing)
- **Terraform 1.9+** & **Helm v3** (for infrastructure changes)

### 1. Clone & Bootstrap
```bash
git clone https://github.com/VNT1998/nuvorix.git
cd nuvorix

# Install all backend and frontend dependencies
make install
```

### 2. Configure Environment
```bash
cp .env.example .env
```

---

## Engineering Workflow & Quality Gate

Before submitting a pull request, your branch must satisfy the repository quality gate:

```bash
# 1. Format and Lint
make format
make lint

# 2. Static Typing Verification
make typecheck

# 3. Automated Tests & Coverage
make test-cov

# 4. Production Build
make build

# 5. One-Command Quality Gate
make check
```

---

## Architectural Principles & Invariants

1. **Layered Architecture**: Routers handle HTTP transport only; business logic resides strictly in `app/services/`.
2. **Multi-Tenancy & Authorization**: Every service method requires explicit `organization_id` and caller execution context. Never infer or fallback to default organizations in production.
3. **Automated Quality Gates**: Production deployments strictly enforce automated evaluation criteria (`status == "completed"` and `decision == "ALLOW"`). Break-glass bypasses require explicit permissions, operator reasons, and emit structured audit events.
4. **No Dead Code**: Remove unused imports, dead functions, and obsolete files.
5. **No Committed Secrets**: Never commit real API keys, passwords, or production tokens.

---

## Git & Commit Conventions

Commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
- `feat:` A new user-facing or platform capability
- `fix:` A bug fix or invariant correction
- `docs:` Documentation improvements
- `refactor:` Code reorganization without behavioral changes
- `test:` Adding or refining automated tests
- `chore:` Dependency updates, tooling, or CI configurations
