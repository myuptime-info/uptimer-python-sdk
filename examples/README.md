# Uptimer Python SDK Examples

This directory contains minimal examples demonstrating how to use the Uptimer Python SDK.

## Quick Start

1. **Setup**: `01_client_setup.py` - Basic client initialization
2. **List Resources**:
   - `02_list_workspaces.py` - List all workspaces
   - `03_list_regions.py` - List all regions
   - `04_list_rules.py` - List rules for a workspace
3. **Rule Operations**:
   - `05_get_rule.py` - Get a specific rule by ID
   - `06_create_rule.py` - Create a new rule
   - `07_update_rule.py` - Update an existing rule
   - `08_delete_rule.py` - Delete a rule

## Usage

Replace the placeholder values in each example:

- `your-api-key-here` - Your Uptimer API key
- `your-workspace-id-here` - Your workspace ID
- `your-rule-id-here` - Your rule ID

## Running Examples

```bash
# Run a specific example
uv run python examples/01_client_setup.py

# Or run all examples in sequence
uv run python examples/01_client_setup.py
uv run python examples/02_list_workspaces.py
# ... etc
```

## Example Structure

Each example is focused on a single operation and is as minimal as possible for quick reference and documentation purposes.
