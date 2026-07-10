# Security Policy

## Supported Use

This repository is intended for local research workflows. It is not an investment advisory service, stock recommendation service, or automated trading system.

## Secrets

Never commit secrets or local credentials. In particular, keep these out of Git:

- `.env`
- API keys and tokens
- StockDB passwords
- private service URLs
- local absolute paths that expose workstation structure

Use `.env.example` for placeholder configuration only.

## Data and Reports

Generated research reports, local cache files, and raw StockDB data may contain private research context or licensed data. They should not be published in the repository. Keep full outputs under ignored directories such as `reports/` and `data_cache/`, and publish only small sanitized examples under `examples/`.

## Reporting Issues

If you find a leaked credential, private path, or unsafe output boundary, rotate the affected credential first, then open a private issue or contact the maintainer. Do not paste live credentials into public issues.