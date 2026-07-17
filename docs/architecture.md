# Architecture

## Purpose

Semillero collects domain names from multiple public sources and produces reusable datasets for reconnaissance workflows.

The project does not perform vulnerability scanning, technology fingerprinting or exploitation.

## Design Principles

- Keep components independent.
- One responsibility per component.
- Separate CLI from business logic.
- Prefer simplicity over abstraction.
- Avoid premature optimization.
- Introduce dependencies only when justified.

## Components

- CLI
- Sources
- Filters
- Output
- Models
- Configuration

Each component has a single, well-defined responsibility and evolves independently.
