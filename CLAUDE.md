# data_redesign_method Development Guidelines

## Intermediary objective 

For the three datasets here (/Users/arthursarazin/Documents/data_redesign_method/test_data), which are L4 datasets, I need : 

### On descent 
- a L3 data table that links number of students to middle school scores (test 1) ; a table that links fundings from ADEME and people who got that funding (test 2) ; a table that links internal and external energy consumptions prices (test 3)
- a L2 table with a category "country side"/"down town" to catogerize middle school (test 1) ; a L2 table that categorizes people who got several ADEME fundings and those who got just one (test 2) ; a L2 table that categorizes energy consumptions prices into "high price"/"low price" (test 3). 
- a L1 table that lists one score for all middle shool (test 1) ; a L1 table that lists fundings amount per recipient (test 2) ; a L1 table that lists foreign country buying energy (test 3).
- a L0 datum that gives the average middle school score (test 1) ; a datum that gives the total amount of fundings given by ADEME (test 2) ; a datum that gives the total amount of energy bought from foreign countries (test 3).

### On ascent 
- a L1 table that lists one score for all middle shool (test 1) ; a L1 table that lists fundings amount per recipient (test 2) ; a L1 table that lists foreign country buying energy (test 3)
- a L2 table where catorizes high score (above median) and low score (below median) (test 1) ; a L2 table that distinguishes recipients with more than 10k euros funding and those with less than 10k euros funding (test 2) ; a L2 table that categorizes energy consumptions prices into "high price"/"low price" (test 3).
- a L3 data table that links high scores to the number of students per class (test 1) ; a L2 table that links 10k euro fundings with the types of projects funded (test 2) ; a L3 table that links high energy prices with the type of energy consumed (test 3). 

## Final objective

IMPORTANT : go through the scientific paper that is your **kernel theory**
Once the user has set up his intent and has a dataset he likes, intuitiveness will take care of generating high-quality dataset using [TO BE GENERATED] : 
- propose informative features (columns to create, combine, delete) by observing TabPFN scores
- validate key metrics : can they help predict what we want to predict
- propose differents apps : scoring, anomaly dectection through density, synthetic data generation 

## Testing requirements
- All tests results should be documented here (/Users/arthursarazin/Documents/data_redesign_method/tests)
- All datasets (/Users/arthursarazin/Documents/data_redesign_method/test_data) should be tested with unit tests to ensure the correctness of the data transformations.
- The ultimate test is a Chrome MCP dev tools (claude-in-chrome) walkthrough where the full ascent/descent cycle is conducted on all three datasets, with all intermediate artifacts exported from the interface. 

## Active Technologies
- The main technology here is the intuitiveness package and all its functionnalities. 
- All necessary libraries are in a virtual environment : /Users/arthursarazin/Documents/data_redesign_method/myenv311
- Python 3.11+ + pandas (DataFrames), networkx (graphs), typing (type hints), dataclasses (entities) (001-dataset-redesign-package)
- JSON files (session exports, test artifacts) (006-playwright-mcp-e2e)
- Python 3.11 (existing `myenv311` virtual environment) (006-playwright-mcp-e2e)
- JSON files (session graphs) + CSV files (test data) (006-playwright-mcp-e2e)
- Python 3.11 (existing `myenv311` virtual environment) + Streamlit >=1.28.0 (already installed), Google Fonts CDN (external) (007-streamlit-design-makeup)
- N/A (UI-only changes, no data layer modifications) (007-streamlit-design-makeup)
- Python 3.11 (existing `myenv311` virtual environment) + Streamlit >=1.28.0, pandas, requests (all already installed) (008-datagouv-search)
- Session state for search results; local file cache for downloaded CSVs (~/.cache/datagouv) (008-datagouv-search)
- Python 3.11 (existing `myenv311` virtual environment) + Streamlit >=1.28.0, requests, pandas (all installed); `mcp_client.py` already implements Streamable HTTP (014-datagouv-mcp-search)
- Session state for search results; local file cache `~/.cache/datagouv/` for downloaded CSVs (014-datagouv-mcp-search)
- Python 3.11.9 + pandas 2.3.3 (DataFrames/Series), networkx 3.6.1 (graphs), dataclasses + typing (entities/typed params), copy.deepcopy (lineage isolation). No new runtime dependencies. (015-adaptive-typed-levels)
- JSON for the session export record (cross-service contract); existing payload serializers (`serialize_dataframe` = zlib+base64, `serialize_graph` = node-link JSON, `serialize_value`); a durable file/blob backend for full payloads; the existing localStorage-style `StorageBackend` demoted to a lightweight session index. (015-adaptive-typed-levels)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

- I do spec-driven development, everything you code should comply with the constitution (/Users/arthursarazin/Documents/data_redesign_method/.specify/memory/constitution.md).
- UI tests/walkthroughs should be run with the Chrome MCP dev tools (claude-in-chrome) as I pay attention to interactions with the user interface. (pytest is still used for unit/integration tests.)
- I am a non-programmer and I like code that is easy to read and understand. Please use clear and descriptive names for variables, functions, and classes.
- When I meet a bug and find the solution, I like to have a troubleshooting.md with the problem and the solution documented for future reference.

## Lessons Learned

### PyPI Token Authentication (Feb 2024)

**Problem:** Getting `403 Forbidden` error when uploading to Test PyPI with "Invalid or non-existent authentication information"

**Root Cause:** Using a **production PyPI token** in the `[testpypi]` section of `~/.pypirc`

**Token Format Identification:**
- Production PyPI tokens: `pypi-AgEIcHlwaS5vcmcC...` (contains base64 for "pypi.org")
- Test PyPI tokens: `pypi-AgENdGVzdC5weXBp...` (contains base64 for "test.pypi")

**Solution:**
1. Test PyPI and production PyPI are **separate systems** with separate authentication
2. Generate tokens from the correct server:
   - Test PyPI: https://test.pypi.org/manage/account/token/
   - Production: https://pypi.org/manage/account/token/
3. Each `[testpypi]` and `[pypi]` section in `~/.pypirc` needs its corresponding token
4. Token scope must be "Entire account" for first upload

**Best Practice:**
- For well-tested packages (passing `twine check`, local tests, examples), **skip Test PyPI** and publish directly to production
- Test PyPI is mainly useful for experimental packages or testing upload mechanics
- Always verify token format matches the target server

**~/.pypirc structure:**
```ini
[testpypi]
username = __token__
password = pypi-AgENdGVzdC5weXBp...  # ← Must be from test.pypi.org

[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmcC...  # ← Must be from pypi.org
```


## Recent Changes
- 015-adaptive-typed-levels: Added Python 3.11.9 + pandas 2.3.3 (DataFrames/Series), networkx 3.6.1 (graphs), dataclasses + typing (entities/typed params), copy.deepcopy (lineage isolation). No new runtime dependencies.
- 014-datagouv-mcp-search: Added Python 3.11 (existing `myenv311` virtual environment) + Streamlit >=1.28.0, requests, pandas (all installed); `mcp_client.py` already implements Streamable HTTP
- 010-quality-ds-workflow: Added Python 3.11 (existing `myenv311` virtual environment)



<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
