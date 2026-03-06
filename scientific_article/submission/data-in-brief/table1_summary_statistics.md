# Table 1: summary statistics for all datasets across abstraction levels

| Dataset | Level | Description | Rows | Columns | File Size |
|---------|-------|-------------|------|---------|-----------|
| **test0_schools** | L4 | Raw enrollment data | 50,164 | 81 | 14 MB |
| | L4 | Raw performance indicators | 20,053 | 29 | 3.0 MB |
| | L3 | Joined enrollment-performance | 410 | 111 | 188 KB |
| | L2 | Categorized by performance | 410 | 112 | 192 KB |
| | L1 | Success rate vector | 410 | 2 | 3.5 KB |
| | L0 | Average success rate | 1 | 1 | - |
| | Ascent L3 | Reconstructed multi-level | 410 | 112 | 193 KB |
| **test1_ademe** | L4 | Raw ADEME funding data | 428 | 32 | 55 KB |
| | L3 | Joined beneficiary-project | 500 | 47 | 194 KB |
| | L2 | Categorized by funding level | 500 | 48 | 201 KB |
| | L1 | Funding amount vector | 450 | 2 | 15 KB |
| | L0 | Total funding amount | 1 | 1 | - |
| | Ascent L3 | Reconstructed with categories | 450 | 48 | 170 KB |

**L0 values:**
- test0_schools: 88.25 (average middle school success rate)
- test1_ademe: €69,586,180.93 (total ADEME funding)

**Complexity reduction:**
- test0_schools: L4 (70,217 total rows) → L3 (410 rows) = 99.4% reduction
- test1_ademe: L4 (428 rows) → L3 (500 rows) = -16.8% (expansion due to relationship discovery)
