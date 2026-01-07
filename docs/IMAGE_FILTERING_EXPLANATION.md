# Image Filtering Explanation - What Gets Skipped and Why

## Overview

The `should_skip_image()` function filters out UI elements and decorative images that aren't actual content. This document explains what gets filtered and why.

---

## What `should_skip_image()` Filters Out

### 1. **UI Icons** ❌
- **Pattern**: Class contains `'icon'` OR URL contains `'/icons/'`
- **Why**: JIRA/Confluence UI icons (like edit buttons, status icons) are not content
- **Example**: `<img class="icon" src="/icons/edit.png">`

### 2. **Emoticons** ⚠️ (Now Context-Aware)
- **Pattern**: Class contains `'emoticon'` OR URL contains `'emoticons/'`
- **Why**: Usually better as emoji characters than images
- **Behavior**:
  - **Table cells**: Converted to emoji (✅) - Notion tables don't support inline images well
  - **Regular content**: Can be images if `allow_emoticons=True` (new feature)
- **Example**: `<img class="emoticon" data-emoji-fallback="✅" src="images/icons/emoticons/72/2705.png">`

### 3. **Bullets** ❌
- **Pattern**: Class contains `'bullet'`
- **Why**: Decorative bullet points, not content
- **Example**: `<img class="bullet" src="images/icons/bullet_blue.gif">`

### 4. **Avatars** ❌
- **Pattern**: URL contains `'/universal_avatar/'`
- **Why**: User profile pictures, not page content
- **Example**: `src="/universal_avatar/12345.png"`

### 5. **Thumbnails** ❌
- **Pattern**: URL contains `'/icons/'` OR `'attachments/thumbnails/'`
- **Why**: Small preview images, not full content
- **Example**: `src="attachments/thumbnails/image.png"`

### 6. **Placeholders** ❌
- **Pattern**: URL contains `'placeholder'` OR `'unknown-attachment'`
- **Why**: Missing/broken image placeholders
- **Example**: `src="placeholder/unknown-attachment.png"`

### 7. **Temporary Files** ❌
- **Pattern**: File extension is `.tmp`
- **Why**: Draw.io auto-save backups, not content
- **Example**: `src="diagram.drawio.tmp"`

### 8. **GIF Files** ⚠️ (Now Context-Aware)
- **Pattern**: File extension is `.gif`
- **Why**: Usually UI animations (loading spinners, etc.)
- **Exception**: Emoticon GIFs are allowed if `allow_emoticons=True`
- **Example**: `src="loading.gif"` (skipped) vs `src="emoticons/smile.gif"` (allowed if emoticon)

---

## New Behavior: Context-Aware Emoticon Handling

### Before (Old Behavior):
- **All emoticons**: Skipped everywhere
- **Result**: Emoticons disappeared from content

### After (New Behavior):
- **Table cells**: Emoticons converted to emoji characters (✅)
  - Better UX: Inline emoji works better in Notion tables
  - Notion limitation: Tables don't support inline images well
- **Regular content**: Emoticons can be images if `allow_emoticons=True`
  - Default: Still converted to emoji (better for most cases)
  - Option: Can be images if explicitly requested

---

## Code Changes

### `should_skip_image()` Function
```python
def should_skip_image(img_element: Tag, src: str, allow_emoticons: bool = False) -> bool:
    """
    Args:
        allow_emoticons: If True, allow emoticons as images (default: False)
    """
```

### Usage Examples

**Regular Content (Allow Emoticons as Images):**
```python
# In paragraphs, headings, etc.
if src and not should_skip_image(img, src, allow_emoticons=True):
    blocks.append({'type': 'image', 'src': src})
```

**Table Cells (Convert to Emoji):**
```python
# In table cells - convert to emoji
if 'emoticon' in img.get('class', []):
    emoji = img.get('data-emoji-fallback') or img.get('alt', '')
    # Replace img with emoji text
```

---

## Summary Table

| Image Type | Skipped? | Context | Reason |
|-----------|----------|---------|--------|
| UI Icons | ✅ Yes | All | Not content |
| Emoticons (table) | ⚠️ Converted | Table cells | Better as emoji |
| Emoticons (content) | ⚠️ Optional | Regular content | Can be images if requested |
| Bullets | ✅ Yes | All | Decorative |
| Avatars | ✅ Yes | All | Not page content |
| Thumbnails | ✅ Yes | All | Preview only |
| Placeholders | ✅ Yes | All | Broken/missing |
| .tmp files | ✅ Yes | All | Auto-save backups |
| GIFs (UI) | ✅ Yes | All | Usually animations |
| GIFs (emoticon) | ⚠️ Optional | If emoticon | Can be allowed |

---

## Rationale

### Why Filter UI Elements?
- **Performance**: Reduces unnecessary uploads
- **Clarity**: Focuses on actual content
- **Notion Limits**: Avoids hitting API limits with decorative images

### Why Convert Emoticons to Emoji?
- **Better UX**: Emoji characters are cleaner and more universal
- **Smaller Size**: No image upload needed
- **Notion Support**: Tables work better with text than inline images
- **Accessibility**: Screen readers handle emoji better

### Why Allow Emoticons as Images Sometimes?
- **User Preference**: Some users may want original images
- **Custom Emoticons**: Custom emoticons might not have emoji equivalents
- **Flexibility**: Context-aware handling gives more control

---

## Future Improvements

1. **Configurable Filtering**: Add config option to control what gets filtered
2. **Smart Detection**: Better detection of content vs. UI images
3. **Emoji Mapping**: Map custom emoticons to closest emoji equivalents
4. **GIF Handling**: Better detection of content GIFs vs. UI animations



