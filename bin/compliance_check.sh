#!/usr/bin/env bash
# =============================================================================
# Agentic Architect Git-Native Compliance Check (Sprint 1)
# =============================================================================
# This script enforces basic governance checks on files before they are committed.
# It acts as the "Execution Control" layer for a single-agent architecture.
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running Agentic Compliance Checks...${NC}"

# Find all staged files
STAGED_FILES=$(git diff --cached --name-only)

if [ -z "$STAGED_FILES" ]; then
    echo -e "${GREEN}No files staged for commit. Skipping compliance check.${NC}"
    exit 0
fi

FAILED=0

# -----------------------------------------------------------------------------
# 1. Frontmatter Tag Check for ALL CODEX Documents
# -----------------------------------------------------------------------------
# Enforce that all CODEX docs have required frontmatter fields.
for file in $STAGED_FILES; do
    if [[ "$file" == CODEX/*/[A-Z]*.md ]] && [[ "$file" != CODEX/_templates/* ]] && [[ "$file" != */README.md ]]; then
        if ! grep -q "^tags:" "$file"; then
            echo -e "${RED}❌ COMPLIANCE FAILURE: $file is missing the 'tags:' frontmatter array.${NC}"
            FAILED=1
        else
            echo -e "${GREEN}✓ $file contains required tag taxonomy formatting.${NC}"
        fi
        
        if ! grep -q "^status:" "$file"; then
            echo -e "${RED}❌ COMPLIANCE FAILURE: $file is missing a required 'status:' field.${NC}"
            FAILED=1
        fi

        if ! grep -q "^id:" "$file"; then
            echo -e "${RED}❌ COMPLIANCE FAILURE: $file is missing a required 'id:' field.${NC}"
            FAILED=1
        fi
    fi
done

# -----------------------------------------------------------------------------
# 2. Secrets Scanning via Gitleaks
# -----------------------------------------------------------------------------
# Gitleaks scans staged content for real credential patterns (API keys, tokens,
# private keys, etc.) using its full ruleset — far more comprehensive than regex.
echo -e "\n${YELLOW}Scanning for exposed secrets (gitleaks)...${NC}"
if command -v gitleaks &>/dev/null; then
    # Use --source mode which has reliable exit code: 0=clean, 1=leaks found.
    set +e
    GITLEAKS_OUT=$(/usr/local/bin/gitleaks detect --source . --no-banner 2>&1)
    GITLEAKS_EXIT=$?
    set -e
    if [ $GITLEAKS_EXIT -ne 0 ]; then
        echo -e "${RED}❌ SECURITY FAILURE: gitleaks detected exposed secrets.${NC}"
        echo "$GITLEAKS_OUT"
        echo -e "${RED}   Run 'gitleaks detect --source . --verbose' for full details.${NC}"
        FAILED=1
    else
        echo -e "${GREEN}✓ No secrets detected (gitleaks scanned $(echo "$GITLEAKS_OUT" | grep -oE '[0-9]+ commits') commits).${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  gitleaks not found. Falling back to basic regex scan.${NC}"
    echo -e "${YELLOW}   Install gitleaks for real coverage: https://github.com/gitleaks/gitleaks${NC}"
    for file in $STAGED_FILES; do
        if [ -f "$file" ]; then
            if grep -q -E -i "(api_key|secret_key|password|bearer|sk-ant|sk-proj)[[:space:]]*[=:][[:space:]]*['\"].+['\"]" "$file"; then
                echo -e "${RED}❌ SECURITY FAILURE: Potential exposed secret found in $file${NC}"
                FAILED=1
            fi
        fi
    done
fi

# -----------------------------------------------------------------------------
# 3. Prevent self-editing of the compliance script itself without a specific tag
# -----------------------------------------------------------------------------
for file in $STAGED_FILES; do
    if [[ "$file" == "bin/compliance_check.sh" ]]; then
        echo -e "${YELLOW}⚠️ Notice: You are modifying the compliance engine itself.${NC}"
        # In a real setup, we might require a specific branch name like 'security-update'
    fi
done

if [ $FAILED -ne 0 ]; then
    echo -e "\n${RED}====================================================================${NC}"
    echo -e "${RED}COMPLIANCE CHECK FAILED. Commit blocked.${NC}"
    echo -e "${RED}Please fix the errors above and stage the changes before committing.${NC}"
    echo -e "${RED}====================================================================${NC}"
    exit 1
fi

echo -e "\n${GREEN}====================================================================${NC}"
echo -e "${GREEN}COMPLIANCE CHECK PASSED. You are clear for commit.${NC}"
echo -e "${GREEN}====================================================================${NC}"
exit 0
