# OAuth Scope Test Report

**Date:** 2026-05-26 18:58:41
**ACA-Py:** http://localhost:8031
**Keycloak realm:** http://localhost:8080/realms/acapy
**Wallet ID under test:** b3ea2232-f617-4f95-b90c-35409d2b8d44

## Summary

| Result | Count |
|--------|-------|
| Passed | 31 |
| Failed | 0 |
| Total  | 31 |

## Test Cases

| Group | Test | Expected | Actual | Result |
|-------|------|----------|--------|--------|
| Public | GET /status/ready — no token | 200 | 200 | PASS |
| Public | GET /status/live  — no token | 200 | 200 | PASS |
| No token | GET /multitenancy/wallets — no token | 401 | 401 | PASS |
| No token | GET /connections — no token | 401 | 401 | PASS |
| No token | GET /credentials — no token | 401 | 401 | PASS |
| Invalid token | GET /multitenancy/wallets — invalid token | 401 | 401 | PASS |
| Invalid token | GET /connections — invalid token | 401 | 401 | PASS |
| Admin GET | GET /status/ready — admin token | 200 | 200 | PASS |
| Admin GET | GET /status/config — admin token | 200 | 200 | PASS |
| Admin GET | GET /multitenancy/wallets — admin token | 200 | 200 | PASS |
| Admin GET | GET /connections — admin token | 200 | 200 | PASS |
| Admin GET | GET /credentials — admin token | 200 | 200 | PASS |
| Admin GET | GET /multitenancy/wallet/{id} — admin token | 200 | 200 | PASS |
| Admin POST | POST /wallet/did/create — admin token | 200 | 200 | PASS |
| Admin POST | POST /multitenancy/wallet/{id}/remove — admin token | 200 | 200 | PASS |
| Tenant GET | GET /connections — tenant token | 200 | 200 | PASS |
| Tenant GET | GET /credentials — tenant token | 200 | 200 | PASS |
| Tenant GET | GET /wallet/did — tenant token | 200 | 200 | PASS |
| Tenant POST | POST /wallet/did/create — tenant token | 200 | 200 | PASS |
| Tenant→Admin | GET /multitenancy/wallets — tenant token | 403 | 403 | PASS |
| Tenant→Admin | GET /multitenancy/wallet/{id} — tenant token | 403 | 403 | PASS |
| Tenant→Admin | GET /status/config — tenant token | 403 | 403 | PASS |
| Read-only | GET /connections — readonly token | 200 | 200 | PASS |
| Read-only | GET /credentials — readonly token | 200 | 200 | PASS |
| Read-only | GET /wallet/did — readonly token | 200 | 200 | PASS |
| Read-only | POST /wallet/did/create — readonly token | 403 | 403 | PASS |
| Read-only | GET /multitenancy/wallets — readonly token | 403 | 403 | PASS |
| wallet:create scope | GET /connections — limited token (acapy:tenant, no wallet:create) | 200 | 200 | PASS |
| wallet:create scope | POST /wallet/did/create — limited token (missing acapy:wallet:create) | 403 | 403 | PASS |
| wallet:create scope | POST /wallet/did/create — tenant token (has acapy:wallet:create) | 200 | 200 | PASS |
| wallet:create scope | POST /wallet/did/create — admin token (acapy:admin satisfies require_scope) | 200 | 200 | PASS |

## Scope Matrix

| Endpoint | No token | Invalid token | acapy:admin | acapy:tenant + acapy:wallet:create | acapy:tenant (no wallet:create) | acapy:tenant:read |
|----------|----------|---------------|-------------|-------------------------------------|----------------------------------|-------------------|
| `GET /status/ready` | 200 | 200 | 200 | 200 | 200 | 200 |
| `GET /status/config` | 401 | 401 | 200 | 403 | 403 | 403 |
| `GET /multitenancy/wallets` | 401 | 401 | 200 | 403 | 403 | 403 |
| `GET /multitenancy/wallet/{id}` | 401 | 401 | 200 | 403 | 403 | 403 |
| `GET /connections` | 401 | 401 | 200 | 200 | 200 | 200 |
| `GET /credentials` | 401 | 401 | 200 | 200 | 200 | 200 |
| `GET /wallet/did` | 401 | 401 | 200 | 200 | 200 | 200 |
| `POST /wallet/did/create` | 401 | 401 | 200 | 200 | **403** | 403 |
| `POST /multitenancy/wallet/{id}/remove` | 401 | 401 | 200 | 403 | 403 | 403 |
