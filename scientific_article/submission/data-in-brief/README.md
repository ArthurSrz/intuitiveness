# Data Science Journal Submission Package

**Journal:** Data Science (Sage Publishing)
**Article Type:** Research Paper
**Submission Portal:** [Data Science Hub](https://mc.manuscriptcentral.com/datascience)

---

## File Manifest

### Main Article
- **manuscript.tex** - Main LaTeX article formatted for Data Science journal
  - Document class: `sagej` (Sage journal template)
  - Bibliography style: SageH (Sage Harvard)
  - All sections complete and compliant with journal guidelines

### Template Files
- **sagej.cls** - Sage journal document class (v1.2, 2017-01-14)
- **SageH.bst** - Sage Harvard bibliography style
- **SageV.bst** - Sage Vancouver bibliography style (alternative)
- **Sage_LaTeX_Guidelines.pdf** - Official Sage LaTeX documentation
- **Sage_LaTeX_Guidelines.tex** - Example LaTeX file

### Figures
All figures located in `figures/` subdirectory:
- **0.png** - Level 0 data visualization (Table view of Level 0 data)
- **1.png** - Level 1 data visualization (Table view of two Level 1 data)
- **2.png** - Level 2 data visualization (Table view of Level 2 dataset)
- **3.png** - Level 3 data visualization (Table view of Level 3 linkable datasets)

---

## ⚠️ Action Required Before Submission

### CRITICAL: Figure Resolution
**Current Status:** All figures are at 144 DPI
**Required:** 300 DPI minimum

**To fix:**
```bash
# Use sips to upscale images (macOS):
cd figures/
sips -s dpiHeight 300 -s dpiWidth 300 0.png
sips -s dpiHeight 300 -s dpiWidth 300 1.png
sips -s dpiHeight 300 -s dpiWidth 300 2.png
sips -s dpiHeight 300 -s dpiWidth 300 3.png
```

**Alternative:** Regenerate figures from source at higher resolution.

### Repository URL Needed
The Data Availability statement currently contains a placeholder:
```
[REPOSITORY-URL-NEEDED]
```

**Update line 533** in `manuscript.tex` with the actual GitHub/GitLab URL where the `intuitiveness` package is hosted.

---

## Compilation Instructions

### Required Software
- LaTeX distribution (TeX Live, MiKTeX, or MacTeX)
- BibTeX for bibliography processing

### Compile Commands
```bash
cd /Users/arthursarazin/Documents/data_redesign_method/scientific_article/submission/data-in-brief/

# First compilation
pdflatex manuscript.tex

# Process bibliography
bibtex manuscript

# Final compilations (to resolve references)
pdflatex manuscript.tex
pdflatex manuscript.tex
```

### Expected Output
- **manuscript.pdf** - Final submission-ready PDF

---

## Pre-Submission Checklist

### Document Structure
- [x] Abstract: Structured, within 300 words
- [x] Keywords: Minimum 4 keywords provided
- [x] Figures: All 4 figures numbered consecutively with complete captions
- [ ] **Figure Resolution: 300 DPI** (ACTION REQUIRED)
- [x] Figure Labels: Unique labels (fig:level0-datum, fig:level1-single, fig:level2-dataset, fig:level3-linkable)
- [x] References: Sage Harvard style (SageH.bst)

### Required Sections
- [x] Introduction
- [x] Related Work
- [x] Methodology (Conceptual Framework)
- [x] Results (Case Study)
- [x] Discussion
- [x] Conclusion
- [x] Acknowledgements
- [x] Author Contributions (CRediT taxonomy)
- [x] Statements and Declarations
  - [x] Ethical considerations
  - [x] Consent to participate
  - [x] Consent for publication
  - [x] Declaration of conflicting interest
  - [x] Funding statement
  - [x] Data availability
- [x] References

### Metadata
- [x] Title: Descriptive and accurate
- [x] Authors: Arthur Sarazin, Mathis Mourey
- [x] Affiliations: Complete
- [x] Corresponding author: asarazin@veltys.com
- [ ] **ORCID IDs: Ensure all authors add their ORCID IDs in the submission system**

### Financial
- **Article Processing Charge (APC):** $900 USD (discounted from $1,800)
- **Open Access License:** Creative Commons BY-NC (standard)
- **Payment:** Due after acceptance, before publication

---

## Submission Process

### Step 1: Final Verification
1. Fix figure resolution to 300 DPI
2. Update repository URL in Data Availability statement (line 533)
3. Compile LaTeX to verify no errors
4. Review PDF for completeness and formatting

### Step 2: Prepare Submission Files
Required files for upload:
- `manuscript.tex` (main LaTeX source)
- `manuscript.pdf` (compiled PDF)
- All figure files (`figures/0.png`, `figures/1.png`, `figures/2.png`, `figures/3.png`)
- `sagej.cls` (document class)
- `SageH.bst` (bibliography style)

### Step 3: Submit via Portal
1. Go to [Data Science Hub](https://mc.manuscriptcentral.com/datascience)
2. Create account or log in
3. Start new submission
4. Fill in metadata:
   - Article Type: Research Paper
   - Title: Intuitiveness as the Next Stage of Open Data: dataset design and complexity
   - Authors: Arthur Sarazin, Mathis Mourey (with affiliations)
   - Keywords: open data; meta-design; data literacy; framework
5. Upload files (manuscript.tex, figures, template files)
6. Confirm author contributions and declarations
7. Add ORCID IDs for all authors
8. Submit for review

### Step 4: Post-Submission
- **Peer Review:** Open peer review (all identities visible)
- **Timeline:** Varies (typically 4-12 weeks for initial decision)
- **Revisions:** Respond to reviewer comments via the portal
- **Acceptance:** Pay APC ($900) when notified
- **Publication:** Online within ~30 days after payment

---

## Journal Information

**Journal Name:** Data Science
**Publisher:** Sage Publishing (in association with IOS Press)
**ISSN:** 2451-8484 (Print), 2451-8492 (Online)
**Scope:** Original research in data science, including algorithms, systems, applications, and societal impacts

**Submission Guidelines:** [Official Guidelines](https://journals.sagepub.com/author-instructions/DSC)

**Editors-in-Chief:**
- Michel Dumontier (Maastricht University, The Netherlands)
- Tobias Kuhn (VU University Amsterdam, The Netherlands)

---

## Support Resources

### LaTeX Template
- Official template source: https://uk.sagepub.com/sites/default/files/sage_latex_template_4.zip
- Overleaf template: https://www.overleaf.com/latex/templates/a-demonstration-of-the-latex2e-class-file-for-sage-publications/jcdyknyjrkzb

### Author Guidelines
- Manuscript submission guidelines: https://journals.sagepub.com/author-instructions/DSC
- Sage Author Gateway: https://uk.sagepub.com/en-gb/eur/journal-author-gateway

### Contact
For questions about the submission:
- **Editorial Office:** Contact via Data Science Hub portal
- **Technical Support:** Sage Journals Solutions Portal

---

## Notes

### Changes from Original Article
This manuscript has been adapted from `v2_intuitive_datasets_revised_v2.tex` with the following modifications:

1. **Document Class:** Changed from generic `article` to Sage-specific `sagej` class
2. **Figures:** Updated all figure paths to use `figures/` subdirectory, assigned unique labels
3. **Figure 4 Caption:** Completed previously incomplete caption
4. **End Matter:** Added comprehensive Author Contributions and Statements and Declarations sections
5. **Bibliography:** Updated style from `apalike` to `SageH` (Sage Harvard)
6. **Package Cleanup:** Removed `geometry` and `authblk` packages (handled by Sage class)

### Version Control
- **Original Article:** `/Users/arthursarazin/Documents/data_redesign_method/scientific_article/v2_intuitive_datasets_revised_v2.tex`
- **Submission Version:** `manuscript.tex` (this directory)
- **Date Prepared:** 2026-01-07

---

## Quick Start

```bash
# Navigate to submission directory
cd /Users/arthursarazin/Documents/data_redesign_method/scientific_article/submission/data-in-brief/

# Fix figure resolution (REQUIRED)
cd figures/
for f in *.png; do sips -s dpiHeight 300 -s dpiWidth 300 "$f"; done
cd ..

# Update repository URL in manuscript.tex (line 533)
# Edit: https://github.com/[REPOSITORY-URL-NEEDED] → actual URL

# Compile
pdflatex manuscript.tex
bibtex manuscript
pdflatex manuscript.tex
pdflatex manuscript.tex

# Verify output
open manuscript.pdf

# Submit at: https://mc.manuscriptcentral.com/datascience
```

---

**Last Updated:** 2026-01-07
**Prepared By:** Claude Code (AI Assistant)
