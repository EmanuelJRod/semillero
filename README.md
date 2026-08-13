# 🌱 Semillero

**Yet Another Domain Seeder**

Semillero is a lightweight command-line tool for collecting domains and subdomains from multiple public sources.

It was created to simplify the repetitive discovery phase of reconnaissance workflows by providing a single interface for querying different sources and producing normalized, deduplicated results.

## Sources

Semillero currently collects data from:

* **crt.sh** — Certificate Transparency logs
* **Cert Spotter** — Certificate Transparency data
* **Common Crawl** — Web crawl data

Sources can be queried individually or all together using `collect all`.

## Features

* Collect domains and subdomains from multiple public sources.
* Query a specific source or all available sources at once.
* Process a single domain or multiple domains from a text file.
* Normalize and deduplicate collected results.
* Continue collecting when an individual source fails.
* Simple CLI designed to work as part of reconnaissance workflows and command-line pipelines.

## Basic usage

Collect from a specific source:

```bash
semillero collect crtsh example.com
```

Collect from all available sources:

```bash
semillero collect all example.com
```

Collect multiple domains from a text file:

```bash
semillero collect all --input domains.txt
```

The input file should contain one domain per line:

```text
example.com
example.org
example.net
```

The same file-based workflow can also be used with an individual source:

```bash
semillero collect crtsh --input domains.txt
```

## Why "Semillero"?

The name comes from the concept of a **seeder**.

Semillero does not attempt to perform the entire reconnaissance process. Its purpose is to generate a useful initial set of domains and subdomains that can serve as input for other tools and further analysis.

For example:

```bash
semillero collect all --input domains.txt | httpx
```

## Disclaimer

Semillero is intended for legitimate security research, authorized testing, and educational purposes.

Users are responsible for ensuring that their use of the tool complies with applicable laws and that they have proper authorization when testing systems they do not own.
