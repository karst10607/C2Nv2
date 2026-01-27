# Working with Complex Tables

This tutorial covers how C2N Importer handles complex tables containing images, videos, and documents.

## Understanding Table Limitations in Notion

Notion's native tables have several limitations:
- Cannot contain images or videos
- Cannot contain file attachments
- Limited formatting options
- No merged cells support

## Smart Table Rendering

C2N Importer automatically detects table complexity and chooses the best rendering method.

### Simple Tables → Native Notion Tables

Tables containing only text are rendered as native Notion tables:

```{mermaid}
graph LR
    A[HTML Table] --> B{Contains Media?}
    B -->|No| C[Native Notion Table]
    B -->|Yes| D[Column Layout]
```

### Complex Tables → Column Layouts

Tables with media are converted to column-based layouts:

````{tab-set}
```{tab-item} Before (HTML)
```html
<table>
  <tr>
    <th>Product</th>
    <th>Screenshot</th>
    <th>Demo Video</th>
  </tr>
  <tr>
    <td>Feature A</td>
    <td><img src="screenshot1.png"></td>
    <td><video src="demo1.mp4"></video></td>
  </tr>
</table>
```
```

```{tab-item} After (Notion)
The table becomes a column layout where:
- Header row becomes bold text with emoji 📊
- Each row becomes a set of columns
- Images and videos are properly embedded
- Visual separator between header and data
```
````

## Example: Product Comparison Table

Let's import a complex product comparison table:

### 1. Original Confluence Table

Your Confluence page might have a table like:

| Product | Features | Screenshot | Documentation |
|---------|----------|------------|---------------|
| App A   | - Feature 1<br>- Feature 2 | ![](app-a.png) | [Manual.pdf](manual-a.pdf) |
| App B   | - Feature X<br>- Feature Y | ![](app-b.png) | [Guide.pdf](guide-b.pdf) |

### 2. Import Process

When you import this:

1. **Parser detects**: Table contains images and PDF links
2. **Transform decides**: Use column layout (not native table)
3. **Media upload**: Images and PDFs uploaded to S3
4. **Result**: Beautiful column-based layout in Notion

### 3. Result in Notion

The imported content will have:

```{admonition} Header Row
:class: note

📊 **Product** | **Features** | **Screenshot** | **Documentation**
```

---

Then for each product row:
- Column 1: Product name
- Column 2: Feature list
- Column 3: Embedded image
- Column 4: Downloadable PDF

## Advanced Table Features

### Mixed Content Cells

C2N Importer handles cells with mixed content:

```python
# Example: Cell with text and image
<td>
  <p>Product description here</p>
  <img src="product.png">
  <p>Additional notes</p>
</td>
```

This becomes a column with:
1. Paragraph block (description)
2. Image block
3. Paragraph block (notes)

### Nested Tables

While Notion doesn't support nested tables, C2N converts them intelligently:

```{warning}
Deeply nested tables may need manual adjustment after import.
```

### Video Handling

Videos in tables are converted to Notion video blocks:

```python
# Supported formats
- MP4 (H.264 codec recommended)
- MOV
- WebM

# Upload location
- S3: Videos uploaded and served via HTTPS
- Must be accessible publicly
```

## Tips for Best Results

1. **Keep tables organized**: Well-structured HTML tables convert better
2. **Use S3 for media**: More reliable than local tunneling
3. **Check video formats**: Ensure MP4 files use compatible codecs
4. **Preview first**: Do a test import with one page before bulk importing

## Troubleshooting

### Table appears as text
- Check if smart table rendering is enabled in settings
- Verify the table has proper HTML structure

### Media not showing
- Ensure S3 bucket has public read permissions
- Check that media files exist in the source
- Verify upload completed successfully

### Layout issues
- Adjust column width settings
- Consider breaking very wide tables into sections

## Next Steps

- [Media Handling Tutorial](media_handling.md)
- [S3 Setup Guide](s3_setup.md)
- [API Reference for Table Transformation](../api/modules.html#module-transform)




