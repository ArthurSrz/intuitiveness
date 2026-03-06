# Data in Brief Submission Checklist

## Status: Ready for Final Formatting ✓

All content has been prepared and is ready for insertion into the Data in Brief Word template.

---

## ✓ Completed Tasks

### 1. Dataset Preparation ✓
- **Location**: `/Users/arthursarazin/Documents/data_redesign_method/datasets_for_zenodo/`
- **Status**: Uploaded to Zenodo
- **URL**: https://zenodo.org/records/18174814
- **DOI**: 10.5281/zenodo.18174814
- **Contents**:
  - test0_schools/ (17 MB total)
  - test1_ademe/ (428 KB total)
  - test2_energy/ (260 KB total)
  - Complete READMEs and metadata
  - CC-BY-4.0 license

### 2. Article Content ✓
- **File**: `data_article_content.md` (450+ lines)
- **Status**: Complete, ready to copy into Word template
- **Contents**:
  - Title, authors, affiliations
  - Abstract (500 words)
  - Specifications Table (with Zenodo DOI)
  - Value of the Data (5 detailed bullets)
  - Background (200 words)
  - Data Description (comprehensive, all 3 datasets)
  - Methods (with code snippets)
  - Limitations (200 words)
  - All boilerplate sections (Ethics, CRediT, Acknowledgements, etc.)
  - 8 references (within 20-reference limit)

### 3. Visual Aids ✓
- **Table 1**: `table1_summary_statistics.md` - Summary of all datasets
- **Table 2**: `table2_complexity_metrics.md` - Complexity analysis
- **Figure 1**: `figure1_descent_ascent_workflow.png` (425 KB, 300 DPI) - Workflow diagram
- **Figure 2**: `figure2_sample_data_levels.png` (837 KB, 300 DPI) - Sample data visualization
- **Guide**: `VISUAL_AIDS_GUIDE.md` - Detailed insertion instructions

---

## 📋 Next Steps (Your Work)

### Step 1: Open Word Template
1. Open: `data-in-brief-article-template.docx`
2. Save a copy as: `data_article_sarazin_mourey.docx`

### Step 2: Fill in Article Content
1. Open: `data_article_content.md`
2. Copy each section into the corresponding yellow-highlighted area in Word
3. Sections to fill:
   - Article Information (title, authors, keywords, abstract)
   - Specifications Table
   - Value of the Data
   - Background
   - Data Description
   - Experimental Design, Materials and Methods
   - Limitations
   - Ethics Statement
   - CRediT Author Statement
   - Acknowledgements
   - Declaration of Competing Interests
   - References

### Step 3: Insert Visual Aids
1. Refer to: `VISUAL_AIDS_GUIDE.md`
2. Insert Figure 1 in Background or early Data Description
3. Insert Table 1 after introducing datasets
4. Insert Figure 2 when describing test0_schools
5. Insert Table 2 in Methods section (or supplementary)
6. Add captions (suggested text in guide)

### Step 4: Format and Clean Up
1. Delete all blue instructional text from template
2. Delete all comment boxes
3. Delete the instruction page
4. Format tables according to journal style
5. Check figure sizing and quality
6. Ensure references are formatted correctly
7. Proofread entire document

### Step 5: Final Review
- [ ] All yellow-highlighted sections filled
- [ ] All blue instructional text deleted
- [ ] All figures inserted with captions
- [ ] All tables inserted with captions
- [ ] Zenodo DOI and URL verified (10.5281/zenodo.18174814)
- [ ] Author information complete
- [ ] References formatted (max 20)
- [ ] Spell check passed
- [ ] Grammar check passed

### Step 6: Prepare Submission Package
1. Final Word document: `data_article_sarazin_mourey.docx`
2. Figure files (if journal requires separate files):
   - `figure1_descent_ascent_workflow.png`
   - `figure2_sample_data_levels.png`
3. Verify Zenodo URL is accessible
4. Optional: Write cover letter (template below)

---

## 📄 Cover Letter Template (Optional)

```
Dear Editor,

We are pleased to submit our data article titled "Five-level data abstraction transformations for intuitive open data design" for consideration in Data in Brief.

This article presents three open datasets demonstrating systematic transformations across five abstraction levels (L4 unlinkable datasets → L0 atomic datum, followed by L0 → L3 ascent reconstruction). These datasets, sourced from the French national open data platform (data.gouv.fr), showcase:

1. **test0_schools**: School enrollment and performance data (17 MB)
2. **test1_ademe**: ADEME environmental funding data (428 KB)
3. **test2_energy**: Energy price and trade data (260 KB)

Each dataset includes:
- Original raw data (L4)
- Complete transformation artifacts (L3, L2, L1, L0)
- Reconstructed multi-level tables (Ascent L3)
- Comprehensive metadata and session exports

All datasets are publicly accessible via Zenodo (DOI: 10.5281/zenodo.18174814) under CC-BY-4.0 license.

**Novelty and Reuse Potential:**
This is the first public dataset demonstrating systematic five-level data abstraction transformations. Researchers can use these datasets to:
- Study complexity reduction patterns in open data
- Test data transformation algorithms
- Benchmark data navigation interfaces
- Teach data literacy concepts
- Validate semantic matching approaches

The transformation methodology uses the intuitiveness Python package (available on GitHub), ensuring reproducibility. Detailed documentation and session exports enable researchers to understand every transformation step.

All data is from public sources (data.gouv.fr) with appropriate licensing for redistribution. The article complies with Data in Brief requirements and ethical standards.

We confirm that this work has not been published elsewhere and is not under consideration by another journal.

Thank you for considering our submission.

Sincerely,
Arthur Sarazin
Mathis Mourey
```

---

## 📊 Dataset Statistics (Quick Reference)

| Dataset | L4 Rows | L4 Size | L0 Value | Complexity Reduction |
|---------|---------|---------|----------|---------------------|
| test0_schools | 70,217 | 17 MB | 88.25 | 99.4% |
| test1_ademe | 428 | 55 KB | €69,586,180.93 | -16.8% (expansion) |
| test2_energy | 9,763 | 249 KB | 0.0 | 100% |

---

## 🔗 Important Links

- **Zenodo Dataset**: https://zenodo.org/records/18174814
- **DOI**: https://doi.org/10.5281/zenodo.18174814
- **Data in Brief Journal**: https://www.journals.elsevier.com/data-in-brief
- **Submission Portal**: https://www.editorialmanager.com/dib/default.aspx

---

## 📁 File Locations

All submission materials are in:
`/Users/arthursarazin/Documents/data_redesign_method/scientific_article/submission/data-in-brief/`

**Main files:**
- `data_article_content.md` - Article text ready to copy
- `table1_summary_statistics.md` - Table 1 content
- `table2_complexity_metrics.md` - Table 2 content
- `figure1_descent_ascent_workflow.png` - Figure 1 image
- `figure2_sample_data_levels.png` - Figure 2 image
- `VISUAL_AIDS_GUIDE.md` - Insertion instructions
- `SUBMISSION_CHECKLIST.md` - This file

**Supporting files:**
- `generate_figure1.py` - Reproducibility script for Figure 1
- `generate_figure2.py` - Reproducibility script for Figure 2
- `data-in-brief-article-template.docx` - Original template

---

## ⚠️ Important Notes

1. **Reference Limit**: Maximum 20 references. Current count: 8 ✓
2. **Dataset Accessibility**: Zenodo URL must be publicly accessible before submission ✓
3. **File Formats**: Figures are 300 DPI PNG (suitable for publication) ✓
4. **Article Type**: This is a DATA ARTICLE, not a research article. Focus on describing datasets, not theory.
5. **Template Compliance**: Use only the Data in Brief Word template. Do not create custom formatting.

---

## 🎯 Success Criteria

Your submission is ready when:
- [x] Datasets uploaded to public repository
- [x] DOI obtained and verified
- [x] Article content written and reviewed
- [x] Visual aids created (2 figures, 2 tables)
- [ ] Content inserted into Word template
- [ ] Figures and tables inserted with captions
- [ ] Template cleaned (no blue text)
- [ ] Final proofread completed
- [ ] Submission package prepared

**Current Status**: 5/9 complete (55%) - Ready for Word formatting

---

## 📞 Support

If you encounter issues:
1. Regenerate figures: Run `generate_figure1.py` or `generate_figure2.py`
2. Check dataset: Visit https://zenodo.org/records/18174814
3. Review guide: See `VISUAL_AIDS_GUIDE.md` for detailed instructions
4. Contact journal: dib@elsevier.com

---

## ✨ Summary

You have successfully completed:
1. ✓ Dataset preparation and Zenodo upload
2. ✓ Complete article content writing
3. ✓ Visual aids generation (2 figures, 2 tables)
4. ✓ Documentation and guides

**Remaining work**: Copy content into Word template, insert visual aids, proofread, and submit.

**Estimated time to complete**: 2-3 hours for formatting and final review.

Good luck with your submission! 🚀
