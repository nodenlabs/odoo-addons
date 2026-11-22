# Contributing to Noden Labs · Odoo Addons

Thanks for taking the time to contribute! 🎉
Bug reports, fixes, translations, ports and new features are all welcome.

- [Ground rules](#ground-rules)
- [Branches](#branches)
- [Workflow](#workflow)
- [Coding guidelines](#coding-guidelines)
- [Commit messages](#commit-messages)
- [Tests](#tests)
- [Pull requests](#pull-requests)
- [Reporting bugs and requesting features](#reporting-bugs-and-requesting-features)
- [License](#license)

---

## Ground rules

- Be respectful and constructive in issues, reviews and discussions.
- Keep each pull request focused: **one module, one topic**.
- Never commit secrets, API keys, customer data or database dumps.

## Branches

Each Odoo major version has its own branch. `main` holds only the repository landing page.

| Branch | Odoo version |
| :----: | :----------: |
| `20.0` | Odoo 20 |
| `19.0` | Odoo 19 |
| `18.0` | Odoo 18 |

Always target the branch that matches the Odoo version you are working on, **never `main`**.

If a fix applies to several versions, open the PR on the **oldest affected branch** and say so
in the description. Maintainers will forward-port it.

## Workflow

1. **Fork** the repository and clone your fork.
2. **Create a branch** from the target version, using a descriptive name:

   ```bash
   git checkout 19.0
   git checkout -b 19.0-fix-module_name-short-description
   ```

   Suggested prefixes after the version: `fix-`, `imp-`, `add-`, `mig-`.
3. **Make your changes** following the guidelines below.
4. **Run the tests** of the module you touched.
5. **Push** your branch and **open a Pull Request** against the matching version branch.

## Coding guidelines

We follow the [OCA coding guidelines](https://github.com/OCA/odoo-community.org/blob/master/website/Contribution/CONTRIBUTING.rst).
In short:

- **Module structure:** standard Odoo layout (`models/`, `views/`, `security/`, `data/`, `tests/`, `i18n/`, `readme/`).
- **Manifest:** keep `__manifest__.py` complete: `name`, `summary`, `version` (`<odoo>.<x>.<y>.<z>`, e.g. `19.0.1.0.0`),
  `author` (include `Noden Labs`), `website`, `license`, `depends`, `data`.
- **Versioning:** bump the module version whenever you change data, views or models.
  Provide migration scripts in `migrations/<version>/` when stored data must change.
- **Security:** every new model needs access rules in `security/ir.model.access.csv`.
- **Translations:** user-facing strings must be translatable (`_()` / `self.env._()` in Python, plain text in XML).
  Update the `.pot` file when you add or change strings.
- **Python:** PEP 8, no unused imports, no `print()`; use `_logger` for logging.
- **Dependencies:** declare external Python libraries in `external_dependencies` and avoid them when the standard library is enough.

## Commit messages

Use the OCA commit style: a tag, the module name, and a short imperative description.

```
[TAG] module_name: short description (max ~72 chars)

Optional longer explanation of what changed and why.
```

| Tag | Use it for |
| :-- | :--------- |
| `[ADD]` | A new module |
| `[FIX]` | A bug fix |
| `[IMP]` | An improvement or new feature in an existing module |
| `[REF]` | Refactoring without functional changes |
| `[MIG]` | Migrating a module to a new Odoo version |
| `[I18N]` | Translation updates |
| `[REM]` | Removing code, files or a module |

## Tests

- Add or update tests in the module's `tests/` folder for any behaviour you change.
- Run them locally before opening a PR:

  ```bash
  odoo -c odoo.conf -d test_db -i <module_name> --test-enable --stop-after-init
  ```

- Mock calls to external services (carriers, marketplaces, tax authorities). Tests must never hit real APIs.

## Pull requests

Before opening a PR, make sure that:

- [ ] It targets the correct version branch (`18.0`, `19.0` or `20.0`).
- [ ] The module installs and upgrades cleanly on a fresh database.
- [ ] Tests pass, and new behaviour is covered.
- [ ] The manifest version is bumped if needed.
- [ ] Commits follow the OCA style.

In the description, explain **what** changed, **why**, and **how to test it**.
Screenshots are very welcome for UI changes.

## Reporting bugs and requesting features

Use [GitHub Issues](https://github.com/nodenlabs/odoo-addons/issues/new/choose) and pick the right template.
Please search existing issues first to avoid duplicates.

For implementation, custom development or commercial support, contact us at
[sentilis.me/noden](https://sentilis.me/noden).

## License

By contributing, you agree that your contributions will be released under the license
declared in the module's `__manifest__.py`. Unless stated otherwise, that is
[LGPL-3](LICENSE).
