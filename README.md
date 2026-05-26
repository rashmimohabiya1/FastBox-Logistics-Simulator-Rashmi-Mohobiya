# FastBox-Logistics-Simulator

A high-reliability discrete simulation engine built from scratch in Python to parse logistical datasets, normalize variable data schemas, and calculate optimized multi-hop courier routes using Euclidean metric standards.

## Engineering & Architectural Decisions

### 1. Custom Structural JSON Parser (No Serializer Imports)
To comply with the zero-external-dependency constraint, this project implements a custom character-by-character tokenization parser (`CustomStructuralJSONParser`). It maps structural boundary markers (`{`, `}`, `[`, `]`, `"`) using a pointer cursor tracking system. This avoids using python's native `json` module while remaining fully robust against nested formats.

### 2. Schema Sanitization Layer
Input datasets contained intentional formatting anomalies (e.g., variation between dictionary structures and array lists for objects, dynamic string formatting like `$"WI"$`). A dedicated sanitization pipeline filters, cleans, and normalizes these inputs before sending them to the math calculation matrices.

### 3. Core Routing Mechanics & Tie-Breaking
* **Distance Metric:** Calculated using straight-line Euclidean distance formulas.
* **State Preservation:** Couriers do not reset to base coordinates after a pickup; their coordinate states dynamically update to the delivery drop point location.
* **Deterministic Tie-Breaking:** If multiple drivers are equidistant to a warehouse hub, the agent with the lowest alphabetical string index (e.g., `A1` over `A2`) takes operational priority.

## Included Bonus Features
* **ASCII Route Map Grid Visualizer:** Generates plain-text route orientation visualizations in the terminal interface.
* **Manually Compiled CSV Export Layer:** Generates a structured `top_performer.csv` document logging peak agent performance stats without third-party libraries.
