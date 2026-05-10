# Architecture Guide

## System Overview

This document describes the overall architecture of the project.

## Layers

### Presentation Layer
Handles UI, routing, and user interactions.

### Business Logic Layer
Contains core domain logic, validation rules, and orchestration.

### Data Layer
Manages data access, external API calls, and persistence.

## Key Decisions

- Each layer communicates only with its immediate neighbors
- Shared utilities live in a common module
- Configuration is environment-based

## Diagrams

See `assets/` for architecture diagrams if available.
