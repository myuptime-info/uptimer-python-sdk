#!/bin/bash

uv run mypy $(git diff --name-only HEAD | grep '\.py$' | xargs -r ls 2>/dev/null)
