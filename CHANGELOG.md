# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Safe Power Control**:
    - New Webhook endpoints: `/plugins/mode_switch/shutdown` and `/plugins/mode_switch/reboot`.
    - New Filesystem triggers: `/tmp/pwn_shutdown` and `/tmp/pwn_reboot`.
    - New helper scripts: `pwn-toggle`, `pwn-shutdown`, `pwn-reboot`, `pwn-cancel`, and `pwn-test`.
    - Improved helper scripts with CLI feedback messages.
- **Installation Script (`install.sh`)**: Automates downloading the plugin and creating helper scripts.
- Documentation for easy installation in `README.md`.

## [0.1.1-alpha] - 2026-01-19
- Initial migration to new CLI environment.
- Created `README.md`.
- Implemented hybrid trigger system (Webhooks + Filesystem).
- Implemented UI snapshot/restore logic for safety cancellation.