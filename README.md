# 🌱 SEMILLERO 🌱

**Y.A.D.S.**
*Yet Another Domain Seeder.*

*The name **Semillero** comes from a loose Spanish adaptation of the term **"seeder."** It reflects the project's purpose of generating the initial seeds for later reconnaissance workflows.*

Semillero is a tool that centralizes, automates, and simplifies the collection of subdomains from multiple public sources.

Its main goal is to generate normalized URL lists that can be used in subsequent analysis workflows.

Currently, it uses public sources such as:

* crt.sh
* CertSpotter
* Common Crawl

**Semillero is not a scanner. It is a seed generator for reconnaissance workflows.**

---

## Features

- Collects subdomains from multiple public sources.
- Produces a single deduplicated result list.
- Generates normalized HTTP and HTTPS URL variants.
- Accepts domains or URLs as input.
- Normalizes the input automatically.
- Simple command-line interface.
- Designed to easily support additional data sources.

---

## Requirements

* Python 3.11 or later
* Git (optional, for cloning the repository)

---

## Installation

Clone the repository:

```bash
git clone https://github.com/EmanuelJRod/semillero.git
cd semillero
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the virtual environment.

**Linux / macOS**

```bash
source .venv/bin/activate
```

**Windows (PowerShell)**

```powershell
.venv\Scripts\Activate.ps1
```

Install the project:

```bash
pip install -e .
```

---

## Verify the Installation

Run:

```bash
semillero version
```

If the installation was successful, the application will display its current version.

## Disclaimer

This project is intended for educational, research, and authorized security assessment purposes only.

The author is not responsible for any misuse or damage caused by this software. Users are solely responsible for ensuring they have permission to test the systems they target.