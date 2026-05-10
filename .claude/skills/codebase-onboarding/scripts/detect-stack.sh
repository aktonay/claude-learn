#!/bin/bash
echo "=== Tech Stack Detection ==="

if [ -f "package.json" ]; then
    echo "Runtime: Node.js"
    if grep -q '"next"' package.json 2>/dev/null; then
        echo "Framework: Next.js"
    elif grep -q '"react"' package.json 2>/dev/null; then
        echo "Framework: React"
    elif grep -q '"express"' package.json 2>/dev/null; then
        echo "Framework: Express"
    fi
elif [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
    echo "Runtime: Python"
    if [ -f "manage.py" ]; then
        echo "Framework: Django"
    elif grep -q "flask" requirements.txt 2>/dev/null; then
        echo "Framework: Flask"
    elif grep -q "fastapi" requirements.txt 2>/dev/null; then
        echo "Framework: FastAPI"
    fi
elif [ -f "Cargo.toml" ]; then
    echo "Runtime: Rust"
elif [ -f "go.mod" ]; then
    echo "Runtime: Go"
fi

if [ -f "docker-compose.yml" ]; then
    echo "Docker: Yes (docker-compose)"
elif [ -f "Dockerfile" ]; then
    echo "Docker: Yes (Dockerfile)"
fi

if [ -d ".github/workflows" ]; then
    echo "CI/CD: GitHub Actions"
elif [ -d ".gitlab-ci.yml" ]; then
    echo "CI/CD: GitLab CI"
fi

echo "=== Done ==="
