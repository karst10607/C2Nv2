---
kernelspec:
  name: python3
  display_name: Python 3
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
---

# Example: Processing Complex Tables

This tutorial shows how C2N Importer handles complex table transformations using live code examples.

## Introduction

When importing from Confluence to Notion, tables present unique challenges. Let's explore how our system handles them.

```{code-cell} ipython3
:tags: [hide-output]

# Setup - this cell is hidden in the output
import sys
sys.path.append('../..')
from pathlib import Path
import json
from src.transform import analyze_table_content, to_notion_blocks
```

## Creating a Complex Table

Let's create a table that contains mixed content:

```{code-cell} ipython3
# Define a complex table structure
complex_table = {
    'type': 'table',
    'rows': [
        {
            'is_header_row': True,
            'cells': [
                {'children': [{'type': 'paragraph', 'text': 'Feature'}]},
                {'children': [{'type': 'paragraph', 'text': 'Screenshot'}]},
                {'children': [{'type': 'paragraph', 'text': 'Status'}]}
            ]
        },
        {
            'cells': [
                {'children': [
                    {'type': 'paragraph', 'text': 'Dark Mode'},
                    {'type': 'paragraph', 'text': 'Toggle between light and dark themes'}
                ]},
                {'children': [{'type': 'image', 'src': 'darkmode.png'}]},
                {'children': [{'type': 'paragraph', 'text': '✅ Completed'}]}
            ]
        },
        {
            'cells': [
                {'children': [{'type': 'paragraph', 'text': 'Multi-language'}]},
                {'children': [
                    {'type': 'image', 'src': 'languages.png'},
                    {'type': 'paragraph', 'text': 'Supports 10+ languages'}
                ]},
                {'children': [{'type': 'paragraph', 'text': '🚧 In Progress'}]}
            ]
        }
    ]
}

print("Table structure created with:")
print(f"- {len(complex_table['rows'])} rows")
print(f"- Mixed content (text + images)")
print(f"- Header row: {complex_table['rows'][0]['is_header_row']}")
```

## Analyzing Table Complexity

C2N Importer analyzes each table to determine the best rendering method:

```{code-cell} ipython3
# Analyze the table
analysis = analyze_table_content(complex_table)

# Display analysis results
import pandas as pd

df = pd.DataFrame([analysis])
df = df.T
df.columns = ['Value']
df
```

```{note}
Notice how the analyzer detected:
- **has_images**: True (table contains images)
- **has_mixed_content**: True (cells with both text and images)
- **cell_complexity**: 'complex' (requires column layout)
```

## Transformation to Notion Blocks

Based on the analysis, the table will be converted to a column layout:

```{code-cell} ipython3
# Create a simple AST with our table
ast = {
    'title': 'Feature Comparison',
    'blocks': [complex_table]
}

# Transform to Notion blocks
notion_blocks = to_notion_blocks(
    ast,
    image_base_url='https://cdn.example.com',
    smart_table_rendering=True
)

# Show the structure
print(f"Generated {len(notion_blocks)} Notion blocks")
print(f"Block types: {[b['type'] for b in notion_blocks]}")
```

## Visualizing the Transformation

Let's visualize what happens during transformation:

```{code-cell} ipython3
:tags: [hide-input]

import matplotlib.pyplot as plt
import matplotlib.patches as patches

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

# Original table visualization
ax1.set_title('Original HTML Table', fontsize=14, fontweight='bold')
ax1.set_xlim(0, 3)
ax1.set_ylim(0, 3)

# Draw table grid
for i in range(4):
    ax1.axhline(i, color='black', linewidth=1)
for i in range(4):
    ax1.axvline(i, color='black', linewidth=1)

# Add content labels
ax1.text(0.5, 2.5, 'Feature', ha='center', va='center', fontweight='bold')
ax1.text(1.5, 2.5, 'Screenshot', ha='center', va='center', fontweight='bold')
ax1.text(2.5, 2.5, 'Status', ha='center', va='center', fontweight='bold')

ax1.text(0.5, 1.5, 'Dark Mode\n+ text', ha='center', va='center')
ax1.text(1.5, 1.5, '🖼️', ha='center', va='center', fontsize=20)
ax1.text(2.5, 1.5, '✅', ha='center', va='center')

ax1.text(0.5, 0.5, 'Multi-lang', ha='center', va='center')
ax1.text(1.5, 0.5, '🖼️ + text', ha='center', va='center')
ax1.text(2.5, 0.5, '🚧', ha='center', va='center')

ax1.axis('off')

# Notion column layout visualization
ax2.set_title('Notion Column Layout', fontsize=14, fontweight='bold')
ax2.set_xlim(0, 3)
ax2.set_ylim(0, 3)

# Header with emoji
rect = patches.FancyBboxPatch((0.1, 2.3), 2.8, 0.4, 
                              boxstyle="round,pad=0.05",
                              facecolor='lightgray', edgecolor='black')
ax2.add_patch(rect)
ax2.text(1.5, 2.5, '📊 Feature | Screenshot | Status', 
         ha='center', va='center', fontweight='bold')

# Divider
ax2.axhline(2.2, color='gray', linewidth=2, linestyle='--')

# Row 1 as columns
for i, (x, content) in enumerate([(0.5, 'Dark Mode\n+ text'), 
                                   (1.5, '🖼️'), 
                                   (2.5, '✅')]):
    rect = patches.FancyBboxPatch((i + 0.1, 1.1), 0.8, 0.8,
                                  boxstyle="round,pad=0.02",
                                  facecolor='white', edgecolor='lightgray')
    ax2.add_patch(rect)
    ax2.text(x, 1.5, content, ha='center', va='center')

# Row 2 as columns
for i, (x, content) in enumerate([(0.5, 'Multi-lang'), 
                                   (1.5, '🖼️\n+ text'), 
                                   (2.5, '🚧')]):
    rect = patches.FancyBboxPatch((i + 0.1, 0.1), 0.8, 0.8,
                                  boxstyle="round,pad=0.02",
                                  facecolor='white', edgecolor='lightgray')
    ax2.add_patch(rect)
    ax2.text(x, 0.5, content, ha='center', va='center')

ax2.axis('off')

plt.tight_layout()
plt.show()
```

## Key Takeaways

```{important}
When tables contain images, videos, or files:
1. **Native tables** cannot be used (Notion limitation)
2. **Column layouts** preserve the visual structure
3. **Headers** become styled callout blocks
4. **Each cell** becomes a column with proper content blocks
```

## Try It Yourself

Modify the code above to:
1. Add a video to the table
2. Create a simple text-only table
3. Add more rows with different content types

Then run the analysis to see how the transformation strategy changes!

## Next Steps

- {doc}`media_handling` - Learn about media upload strategies
- {doc}`../user_guide/troubleshooting` - Common issues and solutions
- {doc}`../api/modules` - Detailed API reference




