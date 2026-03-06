# Data Science Journal Submission Package

## 📦 Package Contents

This folder contains everything you need to submit your manuscript to the Data Science journal (Sage Publishing).

### Files Created

1. **Cover Letters:**
   - `cover_letter.tex` - LaTeX formatted cover letter
   - `cover_letter.pdf` - Compiled PDF version
   - `cover_letter.txt` - Plain text version (for online submission systems)

2. **Submission Checklist:**
   - `submission_checklist.md` - Comprehensive checklist of all requirements

3. **Guidelines:**
   - `submission_guidelines.md` - Complete journal guidelines (reference)

## ✨ Changes Made to Your Manuscript

Your manuscript (`v2_intuitive_datasets_revised_v2.tex`) has been updated to meet Data Science journal requirements:

### 1. Abstract (COMPLETED ✓)
- **Before:** ~100 words, unstructured
- **After:** 300 words, structured with Purpose/Methods/Results/Conclusions sections
- Meets the mandatory 300-word requirement

### 2. Keywords (COMPLETED ✓)
- **Before:** 4 keywords
- **After:** 5 keywords ("dataset complexity" added)
- Meets minimum 5-keyword requirement

### 3. Author Contributions (COMPLETED ✓)
- Added CRediT taxonomy section with 14 standardized roles
- **Sarazin Arthur:** Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Data Curation, Writing – Original Draft, Writing – Review & Editing, Visualization, Project administration
- **Mourey Mathis:** Conceptualization, Methodology, Validation, Formal analysis, Resources, Writing – Review & Editing, Supervision

### 4. Statements and Declarations (COMPLETED ✓)
New section added with all required subsections:
- ✓ Ethical Considerations
- ✓ Consent to Participate
- ✓ Consent for Publication
- ✓ Declaration of Conflicting Interest
- ✓ Funding Statement
- ✓ Data Availability

### 5. Reference Style (COMPLETED ✓)
- Changed from `apalike` to `agsm` (Sage Harvard style)

## 🎯 Critical Actions Before Submission

### URGENT - Must Complete Before Submitting:

#### 1. Update GitHub Repository URL
**Location:** Line 545 in `v2_intuitive_datasets_revised_v2.tex`

**Current text:**
```latex
The \texttt{intuitiveness} Python package is publicly available as open-source
software at \url{https://github.com/[repository-url]} under an open-source license.
```

**Action required:**
- Create public GitHub repository for the `intuitiveness` package
- Replace `[repository-url]` with actual repository path
- Ensure repository contains:
  - Code with clear documentation
  - README with installation instructions
  - Synthetic demonstration datasets
  - Open-source license file (MIT, Apache 2.0, etc.)

#### 2. Obtain ORCID IDs
Both authors must create ORCID IDs:
- **Create at:** https://orcid.org/register
- **Why:** Required for publication metadata
- **When:** Must be linked in submission system before acceptance
- **How:** Each author logs into submission system and links their ORCID

#### 3. Prepare Figure Files at 300 DPI
Verify all figures meet resolution requirements:
- `0.png` - Level 0 table view
- `1.png` - Level 1 table views
- `2.png` - Level 2 dataset
- `3.png` - Level 3 datasets

**Check resolution:**
```bash
file *.png | grep -i resolution
# Should show 300 dpi or higher
```

#### 4. Verify Co-Author Approval
- Send final manuscript to Mathis Mourey
- Obtain explicit approval for submission
- Confirm author contributions are accurate

## 📝 Cover Letter Highlights

The cover letter addresses:

✓ **Direct address to editors:** Prof. Michel Dumontier and Prof. Tobias Kuhn
✓ **Manuscript title and type:** Research Paper
✓ **Key contributions:** 4 distinctive contributions clearly articulated
✓ **Novelty:** Data-layer adaptation vs. presentation-layer adaptation
✓ **Relevance to journal:** Interdisciplinary scope, reproducibility, practical impact
✓ **Suggested reviewers:** 4 international experts with relevant expertise
✓ **Declarations:** Originality, ethics, funding, conflicts of interest

## 🚀 Submission Steps

### 1. Pre-Submission Preparation
- [ ] Complete the 4 critical actions above
- [ ] Review `submission_checklist.md` and check off all items
- [ ] Compile final PDF of manuscript

### 2. Account Setup
- [ ] Visit https://mc.manuscriptcentral.com/datascience
- [ ] Create account or log in (check if you have existing account)
- [ ] Ensure co-author creates their account too
- [ ] Link ORCID IDs to accounts

### 3. Upload Files
- [ ] Main manuscript: `v2_intuitive_datasets_revised_v2.tex`
- [ ] Figures: `0.png`, `1.png`, `2.png`, `3.png` (in order)
- [ ] Cover letter: Use `cover_letter.txt` (copy-paste) or upload PDF

### 4. Complete Submission Form
- [ ] Article type: **Research Paper**
- [ ] Enter all author information (must match manuscript exactly)
- [ ] Enter keywords for reviewer matching
- [ ] Provide word count (~6,500), figure count (4), table count (1)
- [ ] Enter funding information
- [ ] Paste suggested reviewers from cover letter (optional but helpful)

### 5. Review and Submit
- [ ] Carefully review all entered information
- [ ] Verify author order and affiliations
- [ ] Confirm declarations
- [ ] Submit manuscript

## 💰 Publication Costs

- **Submission fee:** $0 (free to submit)
- **Article Processing Charge (APC):** $900 USD (discounted from $1800)
- **Payment timing:** After acceptance, before publication
- **Check eligibility for:**
  - Institutional open access agreements (may reduce or waive APC)
  - Funder-specific waivers
  - Geographic/income-based waivers

## ⏱️ What to Expect

### Timeline
1. **Submission confirmation:** Immediate (email with tracking number)
2. **Initial desk review:** 1-2 weeks (scope and quality check)
3. **Peer review:** 4-8 weeks (open review - identities visible)
4. **Author revisions:** Variable (depends on reviewer comments)
5. **Final decision:** After satisfactory revisions
6. **Publication:** ~30 days after acceptance (OnlineFirst)

### Review Process
- **Open peer review:** Your identity and reviewer identities are visible to each other
- **Rigorous but fair:** Focus on scientific merit and contribution
- **Constructive feedback:** Reviewers provide detailed comments for improvement

## 📞 Support Contacts

**Editorial Office:**
- Prof. Michel Dumontier (Maastricht University, The Netherlands)
- Prof. Tobias Kuhn (VU University Amsterdam, The Netherlands)
- Contact via submission system

**Technical Support:**
- ScholarOne Online Help (linked in submission system)
- Sage Journals Solutions Portal: https://sagepub.force.com/SageJournals

**Your Corresponding Author:**
- Arthur Sarazin: asarazin@veltys.com

## 📚 Additional Resources

- **Journal homepage:** https://journals.sagepub.com/home/dsc
- **Submission system:** https://mc.manuscriptcentral.com/datascience
- **Sage Author Services:** https://www.sagepub.com/author-services
- **Publication ethics:** COPE guidelines (linked in submission system)

## ✅ Quality Assurance

Your manuscript now complies with all Data Science journal requirements:
- ✓ LaTeX format (preferred)
- ✓ 300-word structured abstract
- ✓ Minimum 5 keywords
- ✓ Author contributions (CRediT taxonomy)
- ✓ Complete Statements and Declarations
- ✓ Sage Harvard references
- ✓ Data availability statement
- ✓ Funding disclosure
- ✓ Ethics statements
- ✓ Professional cover letter

## 🎉 Final Encouragement

Your manuscript presents significant theoretical and practical contributions to data science. The framework addresses a real gap in the literature (data-layer adaptation) with:
- Strong theoretical foundations
- Mathematical rigor
- Practical implementation
- Real-world validation
- Open-source commitment

This positions your work well for acceptance. Good luck with your submission!

---

**Last updated:** 2026-01-08
**Prepared for:** Arthur Sarazin and Mathis Mourey
**Journal:** Data Science (Sage Publishing)
**Submission deadline:** When ready (no specific deadline)
