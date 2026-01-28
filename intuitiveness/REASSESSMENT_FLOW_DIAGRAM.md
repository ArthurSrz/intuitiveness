# Re-Assessment Flow Diagram

## Visual Flow: Before vs After Fix

### BEFORE (Broken UX)

```
┌─────────────────────────────────────────────────────────┐
│ 1. User uploads CSV, runs initial assessment            │
│    Result: Score = 65/100                                │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 2. User applies 3 suggestions                            │
│    - Remove redundant feature                            │
│    - Transform skewed distribution                       │
│    - Combine correlated features                         │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 3. User clicks "Re-assess with Changes"                 │
│    Code: st.session_state.pop(QUALITY_REPORT)            │
│    Code: st.rerun()                                      │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 4. ❌ PROBLEM: Lands on upload screen                   │
│    "📤 Upload a CSV file to begin"                      │
│                                                          │
│    WHY? Dashboard checks:                                │
│    - report = None ✓ (was cleared)                       │
│    - No flag set to auto-assess                          │
│    - Shows upload form by default                        │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 5. 😕 User confused - has to re-upload everything       │
│    - Re-upload CSV file                                  │
│    - Re-select target column                             │
│    - Manually click "Assess"                             │
│    - Cannot compare before/after                         │
└─────────────────────────────────────────────────────────┘
```

### AFTER (Fixed UX - A/B Testing Flow)

```
┌─────────────────────────────────────────────────────────┐
│ 1. User uploads CSV, runs initial assessment            │
│    Result: Score = 65/100                                │
│    Session: QUALITY_REPORT = Report(score=65)            │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 2. User applies 3 suggestions                            │
│    - Remove redundant feature                            │
│    - Transform skewed distribution                       │
│    - Combine correlated features                         │
│    Session: QUALITY_DF = modified_data                   │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 3. User clicks "Re-assess with Changes"                 │
│    NEW LOGIC:                                            │
│    1. save_report_to_history(original_report)            │
│    2. target = original_report.target_column             │
│    3. st.session_state.pop(QUALITY_REPORT)               │
│    4. st.session_state['auto_reassess_target'] = target  │
│    5. st.rerun()                                         │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 4. ✅ Dashboard detects flag & auto-assesses            │
│    NEW CHECK:                                            │
│    if auto_target = st.session_state.get('auto_reassess_target'): │
│        new_report = assess_dataset(df, target=auto_target) │
│        save_report_to_history(new_report)                │
│        st.rerun()                                        │
│                                                          │
│    ⏳ Shows: "Re-assessing with applied changes..."     │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 5. 😊 NEW: Before/After comparison displayed            │
│                                                          │
│    ┌─────────────────────────────────────────────────┐ │
│    │ 📊 Before vs. After Comparison                   │ │
│    │                                                  │ │
│    │  Initial      Delta        Current              │ │
│    │   65.0       +13.5         78.5                 │ │
│    │              points                             │ │
│    └─────────────────────────────────────────────────┘ │
│                                                          │
│    User can immediately:                                 │
│    - See exact improvement                               │
│    - Apply more suggestions                              │
│    - Re-assess again (iterative workflow)                │
│    - No manual steps required!                           │
└─────────────────────────────────────────────────────────┘
```

## State Management Flow

```
    INITIAL STATE
    ┌─────────────────────────────────────┐
    │ QUALITY_DF: original_data.csv       │
    │ QUALITY_REPORT: Report(score=65)    │
    │ TRANSFORMED_DF: None                │
    │ HISTORY: []                         │
    └──────────────────┬──────────────────┘
                       │
        [Apply suggestions]
                       │
                       ▼
    SUGGESTIONS APPLIED
    ┌─────────────────────────────────────┐
    │ QUALITY_DF: modified_data           │◄── Changed!
    │ QUALITY_REPORT: Report(score=65)    │◄── Unchanged
    │ APPLIED_SUGGESTIONS: {keys}         │◄── New!
    └──────────────────┬──────────────────┘
                       │
      [Click "Re-assess with Changes"]
                       │
                       ▼
    BUTTON CLICKED
    ┌─────────────────────────────────────┐
    │ Save Report(65) to HISTORY          │
    │ Clear QUALITY_REPORT                │
    │ Set auto_reassess_target = "target" │
    └──────────────────┬──────────────────┘
                       │
      [Dashboard detects flag]
                       │
                       ▼
    AUTO-ASSESSMENT
    ┌─────────────────────────────────────┐
    │ Run assess_dataset(modified_data)   │
    │ new_report = Report(score=78)       │
    │ Save to HISTORY                     │
    │ Set as QUALITY_REPORT               │
    └──────────────────┬──────────────────┘
                       │
        [Display results]
                       │
                       ▼
    FINAL STATE
    ┌─────────────────────────────────────┐
    │ QUALITY_DF: modified_data           │
    │ QUALITY_REPORT: Report(score=78)    │
    │ HISTORY: [Report(65), Report(78)]   │
    │ auto_reassess_target: None          │
    └─────────────────────────────────────┘
                       │
            Show Before/After!
                       ▼
    ┌─────────────────────────────────────┐
    │ Before: 65 → After: 78 (+13 pts)    │
    │ User can iterate more! ↻            │
    └─────────────────────────────────────┘
```

## Code Coordination Pattern

The fix uses a **flag-based coordination pattern** across three files:

```
┌────────────────────────────────────────────────────────────────┐
│ FILE 1: ui/quality/suggestions.py                              │
│                                                                 │
│ if st.button("Re-assess with Changes"):                        │
│     save_report_to_history(original_report)  ◄─┐               │
│     target = original_report.target_column     │               │
│     st.session_state.pop(QUALITY_REPORT)       │               │
│     st.session_state['auto_reassess_target'] = target ◄─ FLAG! │
│     st.rerun()                                  │               │
└──────────────────────────────────────────────┬──────────────────┘
                                               │
                                               │ Rerun triggers
                                               │
                                               ▼
┌────────────────────────────────────────────────────────────────┐
│ FILE 2: ui/quality_dashboard.py                                │
│                                                                 │
│ auto_target = st.session_state.get('auto_reassess_target') ◄─ DETECT FLAG │
│ if auto_target:                                                 │
│     st.session_state.pop('auto_reassess_target')  ◄─ Clear flag │
│     new_report = assess_dataset(df, target=auto_target)         │
│     save_report_to_history(new_report)        ◄─┐               │
│     st.rerun()                                  │               │
└──────────────────────────────────────────────┬──────────────────┘
                                               │
                                               │ Rerun triggers
                                               │
                                               ▼
┌────────────────────────────────────────────────────────────────┐
│ FILE 2: ui/quality_dashboard._render_report_view()             │
│                                                                 │
│ initial = get_initial_report()              ◄─ From HISTORY    │
│ current = get_current_report()              ◄─ From session    │
│                                                                 │
│ if initial.id != current.id:                                    │
│     render before/after comparison          ◄─ SHOW RESULTS!   │
│     - Initial: {initial.usability_score}                        │
│     - Delta: +{delta}                                           │
│     - Current: {current.usability_score}                        │
└─────────────────────────────────────────────────────────────────┘
```

## Key Insights

1. **Flag Pattern**: `auto_reassess_target` acts as a coordination signal between button click and dashboard render
2. **History Preservation**: Original report saved BEFORE clearing, enabling comparison
3. **Target Preservation**: Target column passed through flag, avoiding user re-selection
4. **Error Handling**: If auto-assessment fails, flag is cleared and flow falls through gracefully
5. **Visual Feedback**: Spinner shows "Re-assessing..." during auto-assessment
6. **A/B Display**: Before/after comparison only shows when history exists (initial != current)

## Benefits

✅ **Zero Manual Steps**: After suggestions, one click → see results
✅ **Context Preservation**: No data re-upload, no target re-selection
✅ **Clear Improvement Metrics**: See exact score delta immediately
✅ **Iterative Workflow**: Apply → assess → apply → assess (repeat!)
✅ **Error Resilience**: Graceful degradation if assessment fails
✅ **Fresh Start Still Works**: "New Assessment" button clears everything for clean slate
