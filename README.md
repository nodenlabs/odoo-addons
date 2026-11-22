<div align="center">

<a href="https://sentilis.me/noden">
  <img src="https://cdn.do.sentilis.me/production/noden/profile/logo-95964873-1b19-467b-9e00-2bd1ed313f05.png" alt="Noden Labs" width="120">
</a>

# Noden Labs · Odoo Addons

**Open-source Odoo modules from Noden Labs.**
<br>
<sub>Odoo engineering for complex operations: we build what Odoo doesn't ship out of the box.</sub>

<br>

[![License: LGPL-3](https://img.shields.io/badge/license-LGPL--3-blue.svg)](LICENSE)
[![Odoo Apps](https://img.shields.io/badge/Odoo%20Apps-Noden%20Labs-875A7B.svg)](https://apps.odoo.com/apps/modules/browse?author=Noden%20Labs)
[![Website](https://img.shields.io/badge/web-sentilis.me%2Fnoden-0A0A0A.svg)](https://sentilis.me/noden)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#-contributing)

[**Modules**](#-modules) ·
[**Installation**](#-installation) ·
[**Branches**](#-branches) ·
[**Contributing**](#-contributing)

</div>

---

## 🌿 Branches

Each Odoo major version has its own branch. **`main` contains no modules**; it holds only
this landing page. Pick the branch that matches your Odoo server.

| Branch | Odoo version | Status | Browse |
| :----: | :----------: | :----: | :----: |
| [`20.0`](https://github.com/nodenlabs/odoo-addons/tree/20.0) | Odoo 20 | 🟢 Active | [Open →](https://github.com/nodenlabs/odoo-addons/tree/20.0) |
| [`19.0`](https://github.com/nodenlabs/odoo-addons/tree/19.0) | Odoo 19 | 🟢 Active | [Open →](https://github.com/nodenlabs/odoo-addons/tree/19.0) |
| [`18.0`](https://github.com/nodenlabs/odoo-addons/tree/18.0) | Odoo 18 | 🟢 Active | [Open →](https://github.com/nodenlabs/odoo-addons/tree/18.0) |

> [!IMPORTANT]
> Never mix branches. A module from `19.0` will not install on an Odoo 18 server, and vice versa.

---

## 📦 Modules

| Module | Summary | License | 18.0 | 19.0 | 20.0 |
| :----- | :------ | :-----: | :--: | :--: | :--: |
| **AutoInvoice MX**<br>[`sen_selfbilling`](https://github.com/nodenlabs/odoo-addons/tree/19.0/sen_selfbilling) | CFDI 4.0 self-billing for marketplaces. Your Mercado Libre, Amazon and web-store customers invoice themselves: they enter the order number and RFC and get a stamped CFDI 4.0 right away, with no data entry on your side. | OPL-1 | [✅ 1.5.0](https://github.com/nodenlabs/odoo-addons/tree/18.0/sen_selfbilling) | [✅ 1.5.0](https://github.com/nodenlabs/odoo-addons/tree/19.0/sen_selfbilling) | [✅ 1.5.0](https://github.com/nodenlabs/odoo-addons/tree/20.0/sen_selfbilling) |

<!--
  Add one row per module, for example:
  | **Display Name**<br>[`module_name`](https://github.com/nodenlabs/odoo-addons/tree/19.0/module_name) | One-line description | LGPL-3 | [✅ 1.0.0](https://github.com/nodenlabs/odoo-addons/tree/18.0/module_name) | [✅ 1.0.0](https://github.com/nodenlabs/odoo-addons/tree/19.0/module_name) | 🚧 |
  Legend: ✅ available · 🚧 in progress · — not planned
-->

<sub>Legend: ✅ available · 🚧 in progress · — not planned. Click a version to open the module on that branch.</sub>

### 🛒 Commercial connectors

Noden Labs also sells **commercial connectors** (SkydropX, Aplin and others) on the
Noden Market and the official Odoo Apps Store. Each one includes implementation support.

<p>
  <a href="https://sentilis.me/noden/market">
    <img src="https://img.shields.io/badge/Browse%20on-Noden%20Market-0A0A0A?style=for-the-badge" alt="Browse the Noden Market">
  </a>
  <a href="https://apps.odoo.com/apps/modules/browse?author=Noden%20Labs">
    <img src="https://img.shields.io/badge/Browse%20on-apps.odoo.com-714B67?style=for-the-badge&logo=odoo&logoColor=white" alt="Browse Noden Labs on the Odoo Apps Store">
  </a>
</p>

---

## 🚀 Installation

### 1. Clone the branch for your Odoo version

```bash
# Replace 19.0 with 18.0 or 20.0 to match your Odoo server
git clone --branch 19.0 --single-branch --depth 1 \
  https://github.com/nodenlabs/odoo-addons.git noden-addons
```

### 2. Add it to your `addons_path`

```ini
# odoo.conf
[options]
addons_path = /opt/odoo/odoo/addons,/opt/odoo/addons,/path/to/noden-addons
```

### 3. Install the module

Restart Odoo, then:

1. Turn on **Developer Mode** (_Settings → Activate the developer mode_).
2. Go to **Apps → Update Apps List**.
3. Search for the module and click **Activate**.

Or from the command line:

```bash
odoo -c odoo.conf -d <your_database> -i <module_name> --stop-after-init
```

<details>
<summary><b>🐳 Docker</b></summary>

<br>

Mount the repo as an extra addons directory in the official Odoo image:

```yaml
# docker-compose.yml
services:
  odoo:
    image: odoo:19.0
    volumes:
      - ./noden-addons:/mnt/extra-addons
```

`/mnt/extra-addons` is already in the image's default `addons_path`.

</details>

<details>
<summary><b>☁️ Odoo.sh</b></summary>

<br>

Add the repo as a Git submodule on the branch that matches your project:

```bash
git submodule add -b 19.0 https://github.com/nodenlabs/odoo-addons.git noden-addons
git commit -m "[ADD] noden-addons submodule"
git push
```

Odoo.sh detects the submodule and adds it to the `addons_path` for you.

</details>

<details>
<summary><b>🔄 Updating</b></summary>

<br>

```bash
cd noden-addons && git pull
odoo -c odoo.conf -d <your_database> -u <module_name> --stop-after-init
```

</details>

---

## 🤝 Contributing

Contributions are welcome: bug reports, fixes, translations, ports and new features.

- 📘 Read the **[Contributing Guide](CONTRIBUTING.md)** for the branch workflow, coding guidelines, commit style and PR checklist.
- 🐞 Found a bug or have an idea? **[Open an issue](https://github.com/nodenlabs/odoo-addons/issues/new/choose)** using one of the templates.

> [!NOTE]
> Pull Requests go to the matching version branch (`18.0`, `19.0` or `20.0`), never to `main`.

---

## 📄 License

Unless a module's `__manifest__.py` says otherwise, every module in this repository is released under the
**GNU Lesser General Public License v3.0**. See [`LICENSE`](LICENSE) for the full text.

Odoo is a trademark of [Odoo S.A.](https://www.odoo.com) This project is not affiliated with or endorsed by Odoo S.A.

---

<div align="center">

<sub>If these modules save you time, consider giving the repo a ⭐</sub>

</div>
