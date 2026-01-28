# Credentials Management Guide

## Overview

The application uses two API credentials:
1. **HF_TOKEN** - HuggingFace API for semantic operations and NL queries
2. **TABPFN_ACCESS_TOKEN** - TabPFN API for dataset quality assessment

## ✅ Current Setup (Deployed App)

Your credentials are properly configured in **Streamlit Cloud** (App Settings > Secrets):
- `HF_TOKEN` - For semantic joins, NL queries, data.gouv search
- `TABPFN_ACCESS_TOKEN` - For quality assessment platform

## 🔒 Security Best Practices

### For Deployed Apps (Production)
- ✅ **Use Streamlit Cloud secrets UI** (Settings > Secrets)
- ✅ Credentials are encrypted and never appear in code
- ✅ Changes take ~1 minute to propagate

### For Local Development
- Use `.streamlit/secrets.toml` with your personal tokens
- **NEVER commit `.streamlit/secrets.toml`** (already in `.gitignore`)
- Keep credentials local to your machine only

### Token Rotation
Since the HuggingFace token was briefly exposed in the local file, consider rotating it:
1. Go to https://huggingface.co/settings/tokens
2. Revoke the old token (check your current tokens in HuggingFace settings)
3. Create a new token with the same permissions
4. Update the token in Streamlit Cloud secrets UI

## 📁 Credential Files Status

### `.streamlit/secrets.toml` (Local Development)
- **Status**: Template with commented placeholders
- **Purpose**: Local development reference only
- **Security**: Ignored by git (`.gitignore`)
- **Action**: Add your personal tokens when developing locally

### Streamlit Cloud Secrets UI (Production)
- **Status**: ✅ Configured with both tokens
- **Purpose**: Production app credentials
- **Security**: Encrypted by Streamlit Cloud
- **Action**: No action needed - already configured

## 🚀 Local Development Setup

If you need to run the app locally:

1. Copy the example template:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

2. Add your personal tokens to `.streamlit/secrets.toml`:
   ```toml
   HF_TOKEN = "your_personal_hf_token"
   TABPFN_ACCESS_TOKEN = "your_personal_tabpfn_token"
   ```

3. Run the app locally:
   ```bash
   streamlit run streamlit_app.py
   ```

## ❌ What NOT to Do

- ❌ Don't commit `.streamlit/secrets.toml` with actual credentials
- ❌ Don't share tokens in chat, email, or screenshots
- ❌ Don't reuse the same token across multiple projects
- ❌ Don't commit `.env` files with credentials

## ✅ What TO Do

- ✅ Use Streamlit Cloud secrets for deployed apps
- ✅ Use local `.streamlit/secrets.toml` for development (git-ignored)
- ✅ Rotate tokens if they're ever exposed
- ✅ Use separate tokens for development and production

## 📚 Related Documentation

- [TabPFN Setup Guide](./TABPFN_SETUP.md)
- [Streamlit Secrets Documentation](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management)
- [HuggingFace Tokens](https://huggingface.co/settings/tokens)
- [TabPFN Account](https://tabpfn.ai)
