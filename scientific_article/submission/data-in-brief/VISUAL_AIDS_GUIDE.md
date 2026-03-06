# Visual Aids Guide for Data in Brief Submission

## Generated Files

All visual aids have been created in the `/scientific_article/submission/data-in-brief/` directory:

### Tables (Markdown format - ready to convert to Word tables)

1. **table1_summary_statistics.md** (1.9 KB)
   - Complete summary of all datasets across abstraction levels
   - Includes: rows, columns, file sizes for each level
   - Shows L0 values and complexity reduction percentages
   - Location in article: After "Data Description" section

2. **table2_complexity_metrics.md** (3.6 KB)
   - Detailed complexity analysis across levels
   - Includes: theoretical bounds, actual metrics, observations
   - Shows descent and ascent patterns
   - Location in article: In "Methods" section or as supplementary material

### Figures (PNG format - ready to insert)

3. **figure1_descent_ascent_workflow.png** (425 KB, 300 DPI)
   - Visual diagram of the complete L4→L0→L3 transformation cycle
   - Shows descent phase (left) and ascent phase (right)
   - Includes complexity indicators and examples from test0_schools
   - Colors: Blue gradient for descent, orange for ascent
   - Location in article: Early in "Data Description" or "Background" section

4. **figure2_sample_data_levels.png** (837 KB, 300 DPI)
   - Sample data visualization for test0_schools at each level
   - Shows actual data excerpts from L4, L3, L2, L1, L0, and Ascent L3
   - Includes row/column counts and complexity metrics
   - Monospace font for data samples
   - Location in article: In "Data Description" section, referenced when explaining test0_schools

### Generation Scripts (for reproducibility)

5. **generate_figure1.py** (9.3 KB)
   - Python script to regenerate Figure 1
   - Uses matplotlib for diagram creation
   - Can be customized if needed

6. **generate_figure2.py** (7.8 KB)
   - Python script to regenerate Figure 2
   - Reads actual dataset files and displays samples
   - Can be adapted for test1_ademe or test2_energy

## How to Insert into Word Document

### For Tables:

1. Open the markdown files in a text editor
2. Copy the table content (between the header lines `|---|---|`)
3. In Word, use "Insert > Table > Convert Text to Table"
4. Or manually create a table and copy cell by cell
5. Format with Data in Brief table style (no borders, header row in bold)

**Recommended formatting:**
- Header row: Bold, light gray background (#F5F5F5)
- First column: Bold (dataset names)
- Merge cells for dataset names that span multiple rows
- Right-align numeric columns (rows, columns, file sizes)
- Add table caption above: "Table 1. Summary statistics..." or "Table 2. Complexity metrics..."

### For Figures:

1. In Word, place cursor where you want the figure
2. Use "Insert > Pictures > Picture from File..."
3. Select the PNG file
4. Resize if needed (maintain aspect ratio)
5. Add figure caption below: "Figure 1. Descent-ascent workflow..." or "Figure 2. Sample data..."

**Recommended size:**
- Figure 1: Full page width (about 6.5 inches)
- Figure 2: Full page width (about 6.5 inches)
- Both are 300 DPI, suitable for publication quality

### Figure Captions (suggested text):

**Figure 1 Caption:**
"Figure 1. Five-level data abstraction workflow showing the descent phase (L4→L0, blue gradient) for complexity reduction and the ascent phase (L0→L3, orange) for intentional reconstruction. The descent progressively reduces dataset complexity through semantic matching, domain categorization, feature extraction, and aggregation. The ascent reconstructs the atomic datum with analytical dimensions. Example from test0_schools dataset shows reduction from 70,217 rows to a single value (88.25) and subsequent reconstruction to 410 enriched rows."

**Figure 2 Caption:**
"Figure 2. Sample data from test0_schools dataset at each abstraction level. L4 shows two disconnected CSV files (50,164 and 20,053 rows). L3 demonstrates semantic joining using multilingual-e5-small embeddings, resulting in 410 matched schools. L2 adds categorical segmentation, L1 extracts success rate vectors, and L0 aggregates to a single datum (88.25). Ascent L3 shows the reconstructed multi-level table with analytical dimensions added back."

**Table 1 Caption:**
"Table 1. Summary statistics for all datasets across abstraction levels. Each dataset undergoes transformation from L4 (unlinkable) to L0 (atomic) during descent, followed by reconstruction to Ascent L3. File sizes and row counts show progressive complexity reduction. The test2_energy dataset shows 0 rows after L3 due to strict semantic matching criteria."

**Table 2 Caption:**
"Table 2. Complexity metrics and transformation patterns across abstraction levels. Theoretical bounds represent expected complexity reduction at each level (75-100% for L3, 50-75% for L2, etc.). Actual datasets show varying patterns: test0_schools demonstrates classic progressive reduction, test1_ademe shows initial expansion due to relationship discovery, and test2_energy shows aggressive filtering. Column evolution and aggregation methods are specified for each dataset."

## Article Structure Recommendations

### Where to Place Visual Aids:

1. **Introduction/Background section:**
   - Insert Figure 1 early to help readers understand the framework
   - Reference: "The five-level abstraction framework (Figure 1) structures data transformations..."

2. **Data Description section:**
   - Insert Table 1 to summarize all datasets
   - Insert Figure 2 when describing test0_schools in detail
   - Reference: "Table 1 summarizes the characteristics of all datasets at each level..."
   - Reference: "Figure 2 shows sample data from the test0_schools transformation cycle..."

3. **Methods section:**
   - Insert Table 2 to show complexity analysis
   - Reference: "Complexity metrics (Table 2) demonstrate the progressive reduction..."

4. **Alternative placement:**
   - If the article becomes too long, Table 2 can be moved to supplementary materials
   - Figures 1 and 2 + Table 1 are essential and should remain in main text

## File Locations

All files are in: `/Users/arthursarazin/Documents/data_redesign_method/scientific_article/submission/data-in-brief/`

- `table1_summary_statistics.md`
- `table2_complexity_metrics.md`
- `figure1_descent_ascent_workflow.png`
- `figure2_sample_data_levels.png`
- `generate_figure1.py` (reproducibility script)
- `generate_figure2.py` (reproducibility script)

## Regenerating Figures (if needed)

If you need to modify or regenerate the figures:

```bash
cd /Users/arthursarazin/Documents/data_redesign_method
source myenv311/bin/activate
python3 scientific_article/submission/data-in-brief/generate_figure1.py
python3 scientific_article/submission/data-in-brief/generate_figure2.py
```

Both scripts will overwrite the existing PNG files.

## Data in Brief Requirements

- **Figures**: High resolution (300 DPI minimum) ✓
- **Format**: PNG, TIFF, or EPS ✓
- **File size**: Keep under 10 MB per figure ✓
- **Captions**: Detailed, standalone descriptions ✓
- **Tables**: Clear headers, units specified where applicable ✓
- **Numbering**: Sequential (Figure 1, Figure 2, Table 1, Table 2) ✓

All visual aids meet Data in Brief submission requirements.

## Next Steps

1. **Copy article content** from `data_article_content.md` into the Data in Brief Word template
2. **Insert figures and tables** at appropriate locations using this guide
3. **Add captions** using the suggested text above (edit as needed)
4. **Format tables** according to journal style
5. **Proofread** entire document
6. **Check references** (max 20 references)
7. **Delete instructional text** from template (blue text and comment boxes)
8. **Save final version** as `data_article_final.docx`
9. **Submit** to Data in Brief with:
   - Completed Word document
   - Confirmation of Zenodo dataset URL (https://zenodo.org/records/18174814)
   - Optional cover letter

## Contact

If you need to regenerate or modify any visual aids, the Python scripts are fully documented and can be edited with standard matplotlib/pandas knowledge.
