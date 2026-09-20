# Contributing to JioPC Session Keeper

Thank you for your interest in improving JioPC Session Keeper!

## Development Guidelines

1. **Rootless by Design**:
   All solutions must operate completely within unprivileged user space (`~/.local`, `systemd --user`). Never require `sudo` or root permissions.

2. **Vendor Neutrality**:
   Keep discussions, documentation, and code comments focused on technical architecture, Linux desktop standards (XRDP, Xorg, systemd), and user utility. Avoid referencing proprietary vendor internal details.

3. **Privacy First**:
   Ensure all logs, screenshots, and test outputs have personal names, numeric user IDs, private IP subnets, and hostnames redacted.

## Submitting Pull Requests

1. Fork the repository and create your branch from `main`.
2. Ensure your code passes standard syntax checks (`python -m py_compile`, `bash -n`).
3. Fill out the Pull Request checklist.
4. All pull requests are automatically scanned by our CI audit guard before review.
