# Neo4j Graph Schema Documentation

## Overview

This document describes the Neo4j graph database schema for the AgriChain Harvest Optimizer's Biological Rules Engine.

## Schema Setup

The schema was created using the script: `scripts/setup_neo4j_schema.py`

To run the setup script:
```bash
python -m scripts.setup_neo4j_schema
```

## Loading ICAR Post-Harvest Rules

After setting up the schema, load comprehensive ICAR post-harvest rules using:
```bash
python -m scripts.load_icar_rules
```

This script loads detailed ICAR post-harvest management rules for tomatoes and onions, including:
- Temperature and humidity ranges for different storage conditions
- Spoilage time estimates for each condition
- Severity levels (critical, high, medium, low)
- Source references to ICAR Post-Harvest Manual 2020

## Node Types

### 1. Crop Node
Represents agricultural crops with AGROVOC ontology references.

**Properties:**
- `id`: Unique identifier (e.g., "crop_tomato")
- `name`: Common name (e.g., "Tomato")
- `scientific_name`: Scientific name (e.g., "Solanum lycopersicum")
- `category`: Crop category (e.g., "Vegetable")
- `agrovoc_uri`: AGROVOC ontology URI
- `description`: Crop description

**Current Data:**
- Tomato (Solanum lycopersicum)
- Onion (Allium cepa)

### 2. SpoilageRule Node
Represents post-harvest spoilage rules based on environmental conditions.

**Properties:**
- `id`: Unique identifier
- `condition`: Description of the condition
- `temp_min`: Minimum temperature (°C)
- `temp_max`: Maximum temperature (°C)
- `humidity_min`: Minimum humidity (%)
- `humidity_max`: Maximum humidity (%)
- `spoilage_time_hours`: Time until spoilage (hours)
- `severity`: Risk level ("critical", "high", "medium", "low")
- `source_reference`: Citation reference

**Current Data:**
- 11 tomato spoilage rules covering:
  - Extreme heat conditions (critical)
  - High temperature with high humidity (critical)
  - High temperature with moderate humidity (high)
  - Moderate temperature with high humidity (high)
  - Chilling injury from low temperatures (high)
  - Suboptimal storage conditions (medium)
  - Low humidity causing shriveling (medium)
  - Optimal storage conditions (low)
- 12 onion spoilage rules covering:
  - High temperature with high humidity (critical)
  - High humidity causing sprouting (critical)
  - Freezing damage (critical)
  - Warm temperature with moderate humidity (high)
  - High temperature with low humidity (high)
  - Moderate conditions (medium)
  - Very low humidity (medium)
  - Cool storage (low)
  - Optimal cold storage (low)

### 3. Condition Node
Represents environmental conditions for crop storage.

**Properties:**
- `id`: Unique identifier
- `name`: Condition name
- `type`: Condition type ("environmental", "temperature", "humidity")
- `optimal_min`: Optimal minimum value
- `optimal_max`: Optimal maximum value
- `description`: Condition description

**Current Data:**
- High Temperature and Humidity
- Moderate Temperature
- Low Humidity

### 4. Source Node
Represents authoritative sources for biological rules.

**Properties:**
- `id`: Unique identifier
- `name`: Source name
- `type`: Source type ("ICAR_Manual", "AGROVOC")
- `url`: Source URL
- `credibility`: Credibility score (0.0-1.0)
- `description`: Source description

**Current Data:**
- ICAR Post-Harvest Management Manual (credibility: 0.95)
- AGROVOC Multilingual Thesaurus (credibility: 0.90)

## Relationships

### HAS_RULE
Connects crops to their spoilage rules.
- **From:** Crop
- **To:** SpoilageRule
- **Properties:** `priority` (integer)

### REQUIRES
Connects crops to required environmental conditions.
- **From:** Crop
- **To:** Condition
- **Properties:** `importance` ("high", "medium", "low")

### CITES
Connects spoilage rules to their authoritative sources.
- **From:** SpoilageRule
- **To:** Source
- **Properties:** None

### RELATED_TO
Connects related crops (for future use).
- **From:** Crop
- **To:** Crop
- **Properties:** `relationship_type` (string)

### BELONGS_TO
Connects crops to categories (for future use).
- **From:** Crop
- **To:** Category
- **Properties:** None

## Indexes and Constraints

### Constraints (Uniqueness)
- `crop_id_unique`: Ensures unique Crop IDs
- `rule_id_unique`: Ensures unique SpoilageRule IDs
- `condition_id_unique`: Ensures unique Condition IDs
- `source_id_unique`: Ensures unique Source IDs

### Indexes (Performance)
- `crop_name_idx`: Index on Crop.name for fast lookups
- `rule_severity_idx`: Index on SpoilageRule.severity for filtering
- `source_type_idx`: Index on Source.type for filtering

## Example Queries

### Get all spoilage rules for a crop
```cypher
MATCH (c:Crop {name: 'Tomato'})-[:HAS_RULE]->(r:SpoilageRule)-[:CITES]->(s:Source)
RETURN r.condition, r.severity, r.spoilage_time_hours, s.name
ORDER BY r.severity DESC
```

### Find rules matching environmental conditions
```cypher
MATCH (c:Crop {name: 'Tomato'})-[:HAS_RULE]->(r:SpoilageRule)
WHERE $temp >= r.temp_min AND $temp <= r.temp_max
  AND $humidity >= r.humidity_min AND $humidity <= r.humidity_max
RETURN r.condition, r.spoilage_time_hours, r.severity
ORDER BY r.severity DESC
LIMIT 1
```

### Get required conditions for a crop
```cypher
MATCH (c:Crop {name: 'Onion'})-[req:REQUIRES]->(cond:Condition)
RETURN cond.name, cond.type, cond.optimal_min, cond.optimal_max, req.importance
```

## Schema Statistics

- **Total Nodes:** 30
  - Crops: 2
  - SpoilageRules: 23 (11 tomato + 12 onion)
  - Conditions: 3
  - Sources: 2

- **Total Relationships:** 29
  - HAS_RULE: 23
  - REQUIRES: 2
  - CITES: 23

## Future Enhancements

1. Add more crops (potatoes, wheat, rice, cotton, etc.)
2. Add more detailed AGROVOC relationships (RELATED_TO)
3. Add crop categories (BELONGS_TO)
4. Add storage method nodes and relationships
5. Add pest/disease nodes for comprehensive post-harvest management
6. Integrate ICAR research papers as additional sources

## Requirements Validation

This schema implementation validates the following requirements:
- **Requirement 5.1:** Neo4j graph database with biological rules
- **Requirement 5.2:** AGROVOC ontology integration for tomato and onion
- **Requirement 5.3:** Indexes for performance optimization (crop name, rule severity, source type)
- **Requirement 5.4:** ICAR post-harvest rules with temperature/humidity ranges for spoilage assessment
- **Requirement 5.5:** Comprehensive ICAR rules for both tomatoes (11 rules) and onions (12 rules)
