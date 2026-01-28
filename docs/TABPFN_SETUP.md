# TabPFN API Setup Guide

## Overview

The Quality Data Platform (Specs 009 & 010) uses TabPFN for dataset quality assessment. You need to configure your TabPFN API credentials for it to work.

## Quick Setup

### 1. Get Your TabPFN Token

Visit [https://tabpfn.ai](https://tabpfn.ai) and sign up for an account. You'll receive an access token.

### 2. Configure Credentials

**For Streamlit Apps (Recommended):**

Create `.streamlit/secrets.toml`:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` and add your token:

```toml
TABPFN_ACCESS_TOKEN = "your_actual_token_here"
```

**For Python Scripts (Alternative):**

Create `.env` file:

```bash
cp .env.example .env
echo "TABPFN_ACCESS_TOKEN=your_actual_token_here" >> .env
```

### 3. Verify Installation

```bash
python -c "from intuitiveness.quality import assess_dataset; print('TabPFN configured!')"
```

## Configuration Methods

The application checks for TabPFN credentials in this order:

1. **Streamlit secrets** (recommended for apps) - `.streamlit/secrets.toml`
2. **`.env` file** (recommended for scripts) - Set `TABPFN_ACCESS_TOKEN`
3. **Environment variable** - Export `TABPFN_ACCESS_TOKEN` in your shell
4. **Token file** - Store token in `~/.tabpfn/token`

### Method 1: Streamlit Secrets (Recommended for Apps)

**Pros:** Secure, works on Streamlit Cloud, separate from code

```toml
# .streamlit/secrets.toml
TABPFN_ACCESS_TOKEN = "your_token"
```

**For Streamlit Cloud:** Use the Streamlit Cloud UI to add secrets (Settings > Secrets)

### Method 2: .env File (Recommended for Scripts)

**Pros:** Project-specific, version-controlled (example only), easy to update

```bash
# In project root
echo "TABPFN_ACCESS_TOKEN=your_token" > .env
```

### Method 3: Environment Variable

**Pros:** Works across projects, good for CI/CD

```bash
# Add to ~/.bashrc or ~/.zshrc
export TABPFN_ACCESS_TOKEN="your_token"
```

### Method 4: Token File

**Pros:** Used by TabPFN client library by default

```bash
# Run interactive authentication (opens browser)
python -c "from intuitiveness.quality.tabpfn_auth import authenticate_interactive; authenticate_interactive()"
```

This stores the token in `~/.tabpfn/token`.

## Troubleshooting

### "No TabPFN token found" Warning

**Cause:** No credentials configured

**Fix:** Follow setup steps above to add your token

### "Failed to load TabPFN token" Warning

**Cause:** Invalid token format or file permissions

**Fix:** 
1. Check token format (should be alphanumeric string)
2. Verify `.env` file is in project root
3. Check file permissions: `chmod 600 ~/.tabpfn/token`

### Import Error: "tabpfn-client not installed"

**Cause:** Missing dependency

**Fix:**
```bash
pip install tabpfn-client>=0.1.0
```

### Token Loaded but API Calls Fail

**Cause:** Token expired or invalid

**Fix:**
1. Verify token at [https://tabpfn.ai](https://tabpfn.ai)
2. Generate new token if needed
3. Update `.env` file with new token

## Security Best Practices

1. **Never commit `.env` file** - Already in `.gitignore`
2. **Use `.env.example`** - Commit example file without real tokens
3. **Rotate tokens regularly** - Generate new tokens periodically
4. **Restrict file permissions** - `chmod 600 .env`

## Example Usage

```python
from intuitiveness.quality import assess_dataset
import pandas as pd

# Load your dataset
df = pd.read_csv("data.csv")

# Assess quality (TabPFN token loaded automatically)
report = assess_dataset(
    df=df,
    target_column="target",
    task_type="classification"
)

print(f"Usability Score: {report.usability_score:.1f}/100")
```

## CI/CD Configuration

### GitHub Actions

```yaml
- name: Run Quality Assessment
  env:
    TABPFN_ACCESS_TOKEN: ${{ secrets.TABPFN_TOKEN }}
  run: pytest tests/test_quality.py
```

### Docker

```dockerfile
# Pass token as build arg
ARG TABPFN_TOKEN
ENV TABPFN_ACCESS_TOKEN=${TABPFN_TOKEN}
```

## Related Documentation

- Quality Data Platform: `specs/009-quality-data-platform/spec.md`
- 60-Second Workflow: `specs/010-quality-ds-workflow/spec.md`
- TabPFN Official Docs: [https://tabpfn.ai/docs](https://tabpfn.ai/docs)
