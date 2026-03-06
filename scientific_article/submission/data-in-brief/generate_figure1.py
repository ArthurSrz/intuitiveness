#!/usr/bin/env python3
"""
Generate Figure 1: Descent-Ascent Workflow Diagram
Shows the complete L4→L0→L3 transformation cycle
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Create figure
fig, ax = plt.subplots(1, 1, figsize=(14, 10))
ax.set_xlim(0, 14)
ax.set_ylim(0, 10)
ax.axis('off')

# Define colors
color_l4 = '#E8F4F8'  # Light blue
color_l3 = '#B8E6F0'  # Medium blue
color_l2 = '#7DD3E8'  # Darker blue
color_l1 = '#4AB8D4'  # Dark blue
color_l0 = '#2196F3'  # Deepest blue
color_ascent = '#FFF4E6'  # Light orange for ascent

# Title
ax.text(7, 9.5, 'Five-Level Data Abstraction: Descent and Ascent Workflow',
        ha='center', va='top', fontsize=18, fontweight='bold')

# ============ DESCENT PHASE (Left side) ============
ax.text(3.5, 8.8, 'DESCENT PHASE', ha='center', va='top',
        fontsize=14, fontweight='bold', color='#1565C0')
ax.text(3.5, 8.5, '(Complexity Reduction)', ha='center', va='top',
        fontsize=10, style='italic', color='#666')

# L4: Unlinkable Datasets
box_l4 = FancyBboxPatch((1.5, 7.2), 4, 0.8, boxstyle="round,pad=0.1",
                        facecolor=color_l4, edgecolor='#1976D2', linewidth=2)
ax.add_patch(box_l4)
ax.text(3.5, 7.6, 'L4: Unlinkable Datasets', ha='center', va='center',
        fontsize=11, fontweight='bold')
ax.text(3.5, 7.1, 'Multiple disconnected CSVs', ha='center', va='bottom',
        fontsize=8, color='#555')

# Arrow L4 → L3
arrow1 = FancyArrowPatch((3.5, 7.2), (3.5, 6.3),
                        arrowstyle='->', mutation_scale=20, linewidth=2,
                        color='#1565C0', zorder=1)
ax.add_patch(arrow1)
ax.text(4.2, 6.75, 'Semantic\nMatching', ha='left', va='center',
        fontsize=8, style='italic', color='#1565C0')

# L3: Linkable Datasets
box_l3 = FancyBboxPatch((1.5, 5.5), 4, 0.8, boxstyle="round,pad=0.1",
                        facecolor=color_l3, edgecolor='#1976D2', linewidth=2)
ax.add_patch(box_l3)
ax.text(3.5, 5.9, 'L3: Linkable Datasets', ha='center', va='center',
        fontsize=11, fontweight='bold')
ax.text(3.5, 5.4, 'Joined table with relationships', ha='center', va='bottom',
        fontsize=8, color='#555')

# Arrow L3 → L2
arrow2 = FancyArrowPatch((3.5, 5.5), (3.5, 4.6),
                        arrowstyle='->', mutation_scale=20, linewidth=2,
                        color='#1565C0', zorder=1)
ax.add_patch(arrow2)
ax.text(4.2, 5.05, 'Domain\nCategorization', ha='left', va='center',
        fontsize=8, style='italic', color='#1565C0')

# L2: Categorized Table
box_l2 = FancyBboxPatch((1.5, 3.8), 4, 0.8, boxstyle="round,pad=0.1",
                        facecolor=color_l2, edgecolor='#1976D2', linewidth=2)
ax.add_patch(box_l2)
ax.text(3.5, 4.2, 'L2: Categorized Table', ha='center', va='center',
        fontsize=11, fontweight='bold')
ax.text(3.5, 3.7, 'Segmented by domain categories', ha='center', va='bottom',
        fontsize=8, color='#555')

# Arrow L2 → L1
arrow3 = FancyArrowPatch((3.5, 3.8), (3.5, 2.9),
                        arrowstyle='->', mutation_scale=20, linewidth=2,
                        color='#1565C0', zorder=1)
ax.add_patch(arrow3)
ax.text(4.2, 3.35, 'Feature\nExtraction', ha='left', va='center',
        fontsize=8, style='italic', color='#1565C0')

# L1: Feature Vector
box_l1 = FancyBboxPatch((1.5, 2.1), 4, 0.8, boxstyle="round,pad=0.1",
                        facecolor=color_l1, edgecolor='#1976D2', linewidth=2)
ax.add_patch(box_l1)
ax.text(3.5, 2.5, 'L1: Feature Vector', ha='center', va='center',
        fontsize=11, fontweight='bold')
ax.text(3.5, 2.0, 'Single analytical dimension', ha='center', va='bottom',
        fontsize=8, color='#555')

# Arrow L1 → L0
arrow4 = FancyArrowPatch((3.5, 2.1), (3.5, 1.2),
                        arrowstyle='->', mutation_scale=20, linewidth=2,
                        color='#1565C0', zorder=1)
ax.add_patch(arrow4)
ax.text(4.2, 1.65, 'Aggregation\n(mean/sum)', ha='left', va='center',
        fontsize=8, style='italic', color='#1565C0')

# L0: Atomic Datum
box_l0 = FancyBboxPatch((1.5, 0.4), 4, 0.8, boxstyle="round,pad=0.1",
                        facecolor=color_l0, edgecolor='#0D47A1', linewidth=3)
ax.add_patch(box_l0)
ax.text(3.5, 0.8, 'L0: Atomic Datum', ha='center', va='center',
        fontsize=11, fontweight='bold', color='white')
ax.text(3.5, 0.3, 'Single metric (e.g., 88.25)', ha='center', va='bottom',
        fontsize=8, color='white')

# ============ ASCENT PHASE (Right side) ============
ax.text(10.5, 8.8, 'ASCENT PHASE', ha='center', va='top',
        fontsize=14, fontweight='bold', color='#E65100')
ax.text(10.5, 8.5, '(Intentional Reconstruction)', ha='center', va='top',
        fontsize=10, style='italic', color='#666')

# L0 to Ascent arrow (horizontal connector)
arrow_connect = FancyArrowPatch((5.5, 0.8), (7.5, 0.8),
                               arrowstyle='->', mutation_scale=20, linewidth=3,
                               color='#E65100', zorder=1)
ax.add_patch(arrow_connect)
ax.text(6.5, 1.2, 'START ASCENT', ha='center', va='bottom',
        fontsize=9, fontweight='bold', color='#E65100')

# L0 (Ascent start)
box_l0_ascent = FancyBboxPatch((8.5, 0.4), 4, 0.8, boxstyle="round,pad=0.1",
                               facecolor=color_l0, edgecolor='#0D47A1', linewidth=3)
ax.add_patch(box_l0_ascent)
ax.text(10.5, 0.8, 'L0: Atomic Datum', ha='center', va='center',
        fontsize=11, fontweight='bold', color='white')
ax.text(10.5, 0.3, 'Starting point (e.g., 88.25)', ha='center', va='bottom',
        fontsize=8, color='white')

# Arrow L0 → Ascent L1
arrow_a1 = FancyArrowPatch((10.5, 1.2), (10.5, 2.1),
                          arrowstyle='->', mutation_scale=20, linewidth=2,
                          color='#E65100', zorder=1)
ax.add_patch(arrow_a1)
ax.text(9.3, 1.65, 'Add\nDimension', ha='right', va='center',
        fontsize=8, style='italic', color='#E65100')

# Ascent L1
box_a1 = FancyBboxPatch((8.5, 2.1), 4, 0.8, boxstyle="round,pad=0.1",
                        facecolor=color_ascent, edgecolor='#F57C00', linewidth=2)
ax.add_patch(box_a1)
ax.text(10.5, 2.5, 'Ascent L1: Vector', ha='center', va='center',
        fontsize=11, fontweight='bold')
ax.text(10.5, 2.0, 'Expand to multiple values', ha='center', va='bottom',
        fontsize=8, color='#555')

# Arrow Ascent L1 → L2
arrow_a2 = FancyArrowPatch((10.5, 2.9), (10.5, 3.8),
                          arrowstyle='->', mutation_scale=20, linewidth=2,
                          color='#E65100', zorder=1)
ax.add_patch(arrow_a2)
ax.text(9.3, 3.35, 'Add\nCategories', ha='right', va='center',
        fontsize=8, style='italic', color='#E65100')

# Ascent L2
box_a2 = FancyBboxPatch((8.5, 3.8), 4, 0.8, boxstyle="round,pad=0.1",
                        facecolor=color_ascent, edgecolor='#F57C00', linewidth=2)
ax.add_patch(box_a2)
ax.text(10.5, 4.2, 'Ascent L2: Categorized', ha='center', va='center',
        fontsize=11, fontweight='bold')
ax.text(10.5, 3.7, 'Add analytical segmentation', ha='center', va='bottom',
        fontsize=8, color='#555')

# Arrow Ascent L2 → L3
arrow_a3 = FancyArrowPatch((10.5, 4.6), (10.5, 5.5),
                          arrowstyle='->', mutation_scale=20, linewidth=2,
                          color='#E65100', zorder=1)
ax.add_patch(arrow_a3)
ax.text(9.3, 5.05, 'Add\nRelationships', ha='right', va='center',
        fontsize=8, style='italic', color='#E65100')

# Ascent L3: Final Reconstructed Table
box_a3 = FancyBboxPatch((8.5, 5.5), 4, 0.8, boxstyle="round,pad=0.1",
                        facecolor=color_ascent, edgecolor='#F57C00', linewidth=3)
ax.add_patch(box_a3)
ax.text(10.5, 5.9, 'Ascent L3: Multi-Level Table', ha='center', va='center',
        fontsize=11, fontweight='bold')
ax.text(10.5, 5.4, 'Enriched with dimensions', ha='center', va='bottom',
        fontsize=8, color='#555')

# ============ COMPLEXITY INDICATORS ============
# Descent complexity arrow
ax.annotate('', xy=(0.8, 1), xytext=(0.8, 7.5),
           arrowprops=dict(arrowstyle='->', lw=3, color='#B0BEC5'))
ax.text(0.3, 4.25, 'COMPLEXITY', rotation=90, ha='center', va='center',
       fontsize=10, fontweight='bold', color='#546E7A')

# Ascent complexity arrow
ax.annotate('', xy=(13.2, 5.9), xytext=(13.2, 0.8),
           arrowprops=dict(arrowstyle='->', lw=3, color='#FFAB91'))
ax.text(13.7, 3.35, 'RICHNESS', rotation=90, ha='center', va='center',
       fontsize=10, fontweight='bold', color='#E64A19')

# ============ EXAMPLES BOX ============
example_box = FancyBboxPatch((1, 6.8), 12, 1.8, boxstyle="round,pad=0.15",
                            facecolor='#FAFAFA', edgecolor='#999',
                            linewidth=1, linestyle='--', alpha=0.3, zorder=-1)
ax.add_patch(example_box)

# Add examples text
ax.text(7, 7.5, 'Examples from test0_schools dataset:', ha='center', va='top',
       fontsize=9, fontweight='bold', color='#333')
ax.text(7, 7.2, 'L4: 50,164 enrollment + 20,053 performance rows  →  L3: 410 joined rows  →  ' +
        'L2: 410 categorized  →  L1: 410 scores  →  L0: 88.25 (mean)  →  Ascent L3: 410 enriched rows',
       ha='center', va='top', fontsize=7, color='#555')

plt.tight_layout()
plt.savefig('/Users/arthursarazin/Documents/data_redesign_method/scientific_article/submission/data-in-brief/figure1_descent_ascent_workflow.png',
           dpi=300, bbox_inches='tight', facecolor='white')
print("Figure 1 saved successfully!")
plt.close()
