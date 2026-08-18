# 🌱 Semillero

**Yet Another Domain Seeder**

Semillero is a lightweight Python CLI tool for collecting domains and subdomains from multiple public sources.

It was created to simplify the first stage of reconnaissance workflows by gathering potential targets from different sources, normalizing the results, and producing a single deduplicated list that can be passed to other tools.

The name **Semillero** comes from the concept of a *seeder*: its purpose is to generate a useful initial seed of information for further reconnaissance.

## Features

* Collect domains and subdomains from multiple public sources.
* Run individual sources or all available sources at once.
* Process multiple targets from an input file.
* Normalize collected domains.
* Deduplicate results automatically.
* Limit the number of results returned by each source.
* Continue collecting when an external source fails.
* Simple command-line interface.
* No API keys required for the currently supported sources.

## Sources

Semillero currently supports:

* **crt.sh** — Certificate Transparency logs.
* **Cert Spotter** — Certificate Transparency data.
* **Common Crawl** — URLs and domains found in Common Crawl indexes.
* **AlienVault OTX** — Passive DNS information exposed by AlienVault Open Threat Exchange.

External sources may occasionally return errors, rate limits, or become temporarily unavailable. Semillero handles source failures independently so that one unavailable source does not interrupt collection from the others.

## Requirements

* Python 3
* `pip`
* Git

Using a Python virtual environment is recommended.

## Installation

Clone the repository:

```bash
git clone https://github.com/EmanuelJRod/semillero.git
cd semillero
```

### Linux

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

Install Semillero:

```bash
python -m pip install -e .
```

Verify the installation:

```bash
semillero --help
```

When you return to the project later, activate the environment again with:

```bash
source .venv/bin/activate
```

### Windows

Open PowerShell inside the cloned repository.

Create a virtual environment:

```powershell
py -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Upgrade pip:

```powershell
python -m pip install --upgrade pip
```

Install Semillero:

```powershell
python -m pip install -e .
```

Verify the installation:

```powershell
semillero --help
```

When you return to the project later, activate the environment again with:

```powershell
.\.venv\Scripts\Activate.ps1
```

> If PowerShell prevents the activation script from running because of the execution policy, you can allow scripts for the current PowerShell session with:
>
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```
>
> Then run the activation command again.

## Usage

### Generate URL variants

Generate common HTTP/HTTPS and `www` variants for a domain:

```bash
semillero generate example.com
```

Example output:

```text
http://example.com
https://example.com
http://www.example.com
https://www.example.com
```

### Collect from a specific source

Use:

```bash
semillero collect <source> <domain>
```

For example:

```bash
semillero collect crtsh example.com
```

Available sources:

```text
crtsh
certspotter
commoncrawl
alienvault
```

Examples:

```bash
semillero collect certspotter example.com
semillero collect commoncrawl example.com
semillero collect alienvault example.com
```

### Collect from all sources

Run every available source against the same target:

```bash
semillero collect all example.com
```

Semillero combines the results and removes duplicates.

Sources are treated independently. If one source is temporarily unavailable or rate-limited, Semillero reports the error and continues collecting from the remaining sources.

For example:

```text
Error [crtsh]: crt.sh returned HTTP 502.
Error [certspotter]: Cert Spotter returned HTTP 429.
```

These errors do not prevent other available sources from completing.

### Limit results

Use `--limit` to restrict the number of results collected from a source:

```bash
semillero collect crtsh example.com --limit 100
```

The option can also be used with `all`:

```bash
semillero collect all example.com --limit 100
```

### Process multiple domains

Semillero can read targets from a file instead of processing them individually.

For example, create:

```text
targets.txt
```

with:

```text
example.com
example.org
example.net
```

Then run:

```bash
semillero collect all --input targets.txt
```

Semillero processes each target using the available collection sources.

## Development

Install the project in editable mode:

```bash
python -m pip install -e .
```

Install the development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run the test suite:

```bash
python -m pytest
```

## Project Philosophy

Semillero is intentionally small.

The project focuses on doing one job well: generating a useful seed of domains and subdomains for reconnaissance workflows.

New sources and features should keep the CLI simple, preserve predictable output, and avoid unnecessary complexity.

## Disclaimer

Semillero is intended for legitimate security research, reconnaissance, educational purposes, and authorized security testing.

Only use this tool against systems and organizations you are authorized to assess.

The author is not responsible for misuse or damage caused by this software.

## License

This project is licensed under the MIT License.

See the `LICENSE` file for details.