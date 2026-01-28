# Re-Assessment UX Fix - Testing Guide

## Quick Verification (5 minutes)

### Test 1: Basic Re-Assessment Flow

**Steps:**
1. Start Streamlit app: `streamlit run intuitiveness/app.py`
2. Navigate to "Quality Dashboard"
3. Upload any test CSV (e.g., `test_data/test1_data.csv`)
4. Select a target column
5. Click "Assess Dataset Quality"
6. Note initial score (e.g., 65/100)
7. Go to "Suggestions" tab
8. Click "Apply" on 2-3 suggestions
9. Click "Re-assess with Changes" button

**Expected Result:**
- ✅ Spinner shows: "Re-assessing with applied changes..."
- ✅ NO upload screen appears
- ✅ Assessment completes automatically
- ✅ Before/After comparison displays:
  ```
  📊 Before vs. After Comparison

  Initial Quality    +XX.X points    Current Quality
       65.0                               7X.X
  ```

**FAIL Indicators:**
- ❌ Shows "Upload a CSV file to begin"
- ❌ Asks to select target column again
- ❌ No automatic assessment
- ❌ No before/after comparison

---

### Test 2: Multiple Iterations

**Steps:**
1. Complete Test 1 above
2. Note current score (e.g., 72/100)
3. Apply 2-3 MORE suggestions
4. Click "Re-assess with Changes" again
5. Note new score (e.g., 76/100)

**Expected Result:**
- ✅ Second re-assessment also seamless
- ✅ Before/After now shows: 65 → 76 (initial vs final)
- ✅ Can repeat iteratively without interruption

---

### Test 3: New Assessment Still Works

**Steps:**
1. Have a report with history (from Test 1/2)
2. Click "🔄 New Assessment" button (top-right)

**Expected Result:**
- ✅ Returns to upload screen
- ✅ All session state cleared
- ✅ History cleared (no before/after comparison)
- ✅ Fresh start workflow intact

---

## Detailed Test Scenarios

### Scenario A: No Suggestions Applied

**Setup:**
- Upload dataset
- Run initial assessment
- DON'T apply any suggestions

**Test:**
- Go to Suggestions tab
- Look for "Re-assess with Changes" button

**Expected:**
- ✅ Button should NOT appear (no suggestions applied)

**Why:** Button only appears when `applied` set has items

---

### Scenario B: Assessment Error Handling

**Setup:**
- Modify code to force assessment failure:
  ```python
  # In quality_dashboard.py, line ~124
  new_report = assess_dataset(df, target_column=auto_target)
  # Change to:
  raise Exception("Test error")
  ```

**Test:**
- Apply suggestions
- Click "Re-assess"

**Expected:**
- ✅ Error message shows: "Failed to re-assess dataset: Test error"
- ✅ App doesn't crash
- ✅ User can still navigate
- ✅ Falls through to upload/assessment flow

**Cleanup:** Remove test exception after testing

---

### Scenario C: Missing Target Column

**Setup:**
- Apply suggestion that removes the target column
- (This should be prevented by feature_engineer logic, but test edge case)

**Test:**
- Try to re-assess

**Expected:**
- ✅ Error handled gracefully
- ✅ User informed of issue
- ✅ Can start fresh with "New Assessment"

---

### Scenario D: Session State Corruption

**Setup:**
- Manually corrupt session state via browser console:
  ```javascript
  window.localStorage.clear()
  ```

**Test:**
- Try to re-assess

**Expected:**
- ✅ Graceful fallback
- ✅ Returns to upload screen
- ✅ No Python exceptions

---

## Visual Verification Checklist

### Before/After Comparison Display

Check that the comparison section includes:

- [ ] Header: "📊 Before vs. After Comparison"
- [ ] Three columns:
  - [ ] Left: Initial Quality card (with score)
  - [ ] Middle: Delta in large font (with + or - sign)
  - [ ] Right: Current Quality card (with score)
- [ ] Color coding:
  - [ ] Green (#22c55e) for positive delta
  - [ ] Red (#ef4444) for negative delta
- [ ] Cards use score-based colors:
  - [ ] Green (>80): Excellent
  - [ ] Blue (60-80): Good
  - [ ] Orange (40-60): Fair
  - [ ] Red (<40): Poor

### Spinner Text

- [ ] Shows exactly: "Re-assessing with applied changes..."
- [ ] Appears immediately after clicking button
- [ ] Disappears when results shown

---

## Performance Verification

### Timing Expectations

| Dataset Size | Expected Re-Assessment Time |
|--------------|----------------------------|
| <1,000 rows  | 1-3 seconds               |
| 1,000-5,000  | 3-8 seconds               |
| 5,000-10,000 | 8-15 seconds              |

**Test:**
- Use test datasets of different sizes
- Measure time from click to results display
- Verify spinner shows during entire process

---

## Edge Cases Matrix

| Condition | Expected Behavior |
|-----------|-------------------|
| No suggestions applied | Button doesn't appear |
| 1 suggestion applied | Button appears, re-assessment works |
| All suggestions applied | Button appears, re-assessment works |
| Assessment fails | Error shown, no crash |
| Target column missing | Error handled gracefully |
| Session state cleared | Falls back to upload screen |
| Multiple rapid clicks | Only one assessment triggered |

---

## Regression Tests

Ensure existing functionality still works:

### Upload & Initial Assessment
- [ ] Can upload CSV file
- [ ] Can select target column
- [ ] Can run initial assessment
- [ ] Report displays correctly

### Suggestions Tab
- [ ] Feature suggestions display
- [ ] Can apply individual suggestions
- [ ] "Apply All" button works
- [ ] Applied suggestions marked

### Other Tabs
- [ ] Overview tab shows metrics
- [ ] ML Diagnostics tab shows charts
- [ ] 60-Second Workflow tab works
- [ ] Anomaly Detection tab works
- [ ] Methodology tab shows content

### State Management
- [ ] Report history tracked
- [ ] Score evolution displays
- [ ] Can navigate between tabs
- [ ] Session persists across reruns

---

## Manual Testing Script

```bash
# Terminal 1: Start app
cd /Users/arthursarazin/Documents/data_redesign_method
streamlit run intuitiveness/app.py

# In browser: http://localhost:8501

# Test sequence:
# 1. Upload test_data/test1_data.csv
# 2. Select target: "score_global"
# 3. Click "Assess Dataset Quality"
# 4. Note score: __________
# 5. Go to "Suggestions" tab
# 6. Apply 3 suggestions
# 7. Click "Re-assess with Changes"
# 8. Verify: Automatic re-assessment? Y/N
# 9. Verify: Before/After shown? Y/N
# 10. New score: __________
# 11. Delta: +/- __________
# 12. Click "New Assessment"
# 13. Verify: Returns to upload? Y/N
```

---

## Automated Test Outline

**Future Work:** Create Playwright test

```python
# tests/test_reassessment_ux.py

def test_reassessment_seamless_flow(page):
    """Test that re-assessment doesn't require re-upload."""
    # Upload and assess
    page.upload_file("test_data/test1_data.csv")
    page.select_target("score_global")
    page.click("Assess Dataset Quality")
    initial_score = page.get_score()

    # Apply suggestions
    page.click("Suggestions")
    page.click_all_apply_buttons()

    # Re-assess
    page.click("Re-assess with Changes")

    # Verify no upload prompt
    assert not page.has_text("Upload a CSV file")

    # Verify before/after comparison
    assert page.has_text("Before vs. After Comparison")
    assert page.has_text(f"{initial_score}")

    # Verify new score different
    new_score = page.get_score()
    assert new_score != initial_score
```

---

## Success Criteria Summary

✅ **No Manual Steps**: One click from suggestions to results
✅ **No Upload Prompt**: After re-assess, no "upload CSV" message
✅ **No Target Re-Selection**: Target column preserved
✅ **Automatic Assessment**: Runs without user action
✅ **Before/After Display**: Shows initial, delta, and current scores
✅ **Iterative Workflow**: Can apply → assess repeatedly
✅ **Error Resilience**: Graceful handling of failures
✅ **Fresh Start Preserved**: "New Assessment" clears everything
✅ **Performance**: Re-assessment completes in <15 seconds
✅ **Visual Feedback**: Spinner shows during processing

---

## Bug Report Template

If you find an issue:

```markdown
## Bug: [Brief Description]

**Steps to Reproduce:**
1.
2.
3.

**Expected Behavior:**
-

**Actual Behavior:**
-

**Screenshots:**
[Attach screenshots]

**Environment:**
- OS:
- Python version:
- Streamlit version:
- Browser:

**Session State at Time of Error:**
[Copy from browser console or app logs]

**Error Messages:**
[Copy any error messages]
```

---

## Test Results Log

| Test | Date | Tester | Result | Notes |
|------|------|--------|--------|-------|
| Basic Flow | YYYY-MM-DD | | ✅/❌ | |
| Multiple Iterations | YYYY-MM-DD | | ✅/❌ | |
| New Assessment | YYYY-MM-DD | | ✅/❌ | |
| No Suggestions | YYYY-MM-DD | | ✅/❌ | |
| Error Handling | YYYY-MM-DD | | ✅/❌ | |

---

## Next Steps After Testing

1. **If all tests pass:**
   - Document in troubleshooting.md
   - Update CHANGELOG
   - Create git commit
   - Consider adding automated tests

2. **If tests fail:**
   - Document specific failure
   - Check session state values
   - Review code changes
   - Add debug logging
   - Re-test after fixes
