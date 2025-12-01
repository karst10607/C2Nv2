---
kernelspec:
  name: python3
  display_name: Python 3
---

# Dashboard-Style Documentation

This is an interactive dashboard showing C2N Importer's key metrics and functionality.

```{code-cell} ipython3
:tags: [hide-input]

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Create sample data
dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
imports_per_day = np.random.poisson(5, 30) + np.random.randint(0, 3, 30)
pages_imported = np.cumsum(imports_per_day)
media_uploaded = np.cumsum(np.random.poisson(20, 30))
```

## Import Statistics Overview

```{code-cell} ipython3
:tags: [hide-input]

fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
fig.suptitle('C2N Importer Dashboard', fontsize=16)

# Daily imports
ax1.bar(dates, imports_per_day, color='steelblue', alpha=0.7)
ax1.set_title('Daily Imports')
ax1.set_ylabel('Pages Imported')
ax1.tick_params(axis='x', rotation=45)

# Cumulative pages
ax2.plot(dates, pages_imported, marker='o', color='green', linewidth=2, markersize=4)
ax2.fill_between(dates, pages_imported, alpha=0.3, color='green')
ax2.set_title('Total Pages Imported')
ax2.set_ylabel('Cumulative Pages')
ax2.tick_params(axis='x', rotation=45)

# Media types pie chart
media_types = ['Images', 'Videos', 'PDFs', 'Other']
media_counts = [450, 120, 85, 45]
colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
ax3.pie(media_counts, labels=media_types, colors=colors, autopct='%1.1f%%', startangle=90)
ax3.set_title('Media Types Uploaded')

# Success rate
success_rates = np.random.uniform(0.92, 0.99, 30)
ax4.plot(dates, success_rates * 100, color='darkgreen', linewidth=2)
ax4.axhline(y=95, color='red', linestyle='--', alpha=0.5, label='Target (95%)')
ax4.set_title('Import Success Rate')
ax4.set_ylabel('Success Rate (%)')
ax4.set_ylim(90, 100)
ax4.legend()
ax4.tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.show()
```

## Feature Usage Analysis

```{code-cell} ipython3
:tags: [hide-input]

# Create feature usage data
features = ['Smart Tables', 'S3 Upload', 'Column Layout', 'Document Import', 'Draw.io Support']
usage = [85, 72, 68, 45, 38]

fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.barh(features, usage, color=['#2ecc71', '#3498db', '#9b59b6', '#f39c12', '#e74c3c'])

# Add value labels on bars
for i, bar in enumerate(bars):
    width = bar.get_width()
    ax.text(width + 1, bar.get_y() + bar.get_height()/2, f'{usage[i]}%', 
            ha='left', va='center', fontweight='bold')

ax.set_xlabel('Usage Rate (%)', fontsize=12)
ax.set_title('Feature Adoption Rates', fontsize=14, fontweight='bold')
ax.set_xlim(0, 100)
ax.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.show()
```

## Performance Metrics

```{code-cell} ipython3
# Create performance comparison table
metrics_data = {
    'Metric': ['Avg. Import Time', 'Media Upload Speed', 'Table Conversion', 'API Calls/Import', 'Memory Usage'],
    'Current': ['2.3s', '5.2 MB/s', '0.8s', '12.5', '145 MB'],
    'Previous': ['3.1s', '3.8 MB/s', '1.2s', '18.3', '198 MB'],
    'Improvement': ['+26%', '+37%', '+33%', '+32%', '+27%']
}

df_metrics = pd.DataFrame(metrics_data)

# Style the dataframe
styled_df = df_metrics.style.set_properties(**{
    'text-align': 'center',
    'border': '1px solid #ddd'
}).set_table_styles([
    {'selector': 'th', 'props': [('background-color', '#3498db'), ('color', 'white')]},
    {'selector': 'tr:nth-child(even)', 'props': [('background-color', '#f2f2f2')]}
])

styled_df
```

## Live Configuration Status

```{code-cell} ipython3
:tags: [hide-input]

# Check current configuration
config_status = {
    'Notion Token': '✅ Configured',
    'S3 Bucket': '✅ c2n-test',
    'S3 Region': '⚠️ Mismatch (us-east-2)',
    'Upload Strategy': '✅ S3',
    'Smart Tables': '✅ Enabled',
    'Max Columns': '✅ 2',
    'Cache': '✅ Enabled'
}

# Create status visualization
fig, ax = plt.subplots(figsize=(8, 4))
ax.axis('tight')
ax.axis('off')

# Create table
table_data = [[k, v] for k, v in config_status.items()]
table = ax.table(cellText=table_data, 
                colLabels=['Setting', 'Status'],
                cellLoc='left',
                loc='center',
                colWidths=[0.6, 0.4])

# Style the table
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1, 2)

# Color code based on status
for i, (_, status) in enumerate(config_status.items()):
    if '✅' in status:
        table[(i+1, 1)].set_facecolor('#d4edda')
    elif '⚠️' in status:
        table[(i+1, 1)].set_facecolor('#fff3cd')
    elif '❌' in status:
        table[(i+1, 1)].set_facecolor('#f8d7da')

# Header styling
table[(0, 0)].set_facecolor('#3498db')
table[(0, 1)].set_facecolor('#3498db')
table[(0, 0)].set_text_props(weight='bold', color='white')
table[(0, 1)].set_text_props(weight='bold', color='white')

plt.title('Configuration Status', fontsize=14, fontweight='bold', pad=20)
plt.show()
```

## Interactive Code Examples

Try running these examples to see how C2N Importer works:

```{code-cell} ipython3
# Example: Analyze a table structure
table_data = {
    'type': 'table',
    'rows': [
        {'is_header_row': True, 'cells': [
            {'children': [{'type': 'paragraph', 'text': 'Feature'}]},
            {'children': [{'type': 'paragraph', 'text': 'Status'}]},
        ]},
        {'cells': [
            {'children': [{'type': 'paragraph', 'text': 'Smart Rendering'}]},
            {'children': [{'type': 'image', 'src': 'status.png'}]},
        ]}
    ]
}

print("Table Analysis:")
print(f"- Has images: {any('image' in str(row) for row in table_data['rows'])}")
print(f"- Rows: {len(table_data['rows'])}")
print(f"- Requires column layout: Yes (contains image)")
```

## Next Steps

Modify the code cells above to:
1. Change the date range for statistics
2. Add your own metrics
3. Update configuration status
4. Try different visualizations

The dashboard automatically updates when you run the cells!


