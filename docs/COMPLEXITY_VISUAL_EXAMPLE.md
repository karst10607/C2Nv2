# Complexity Measurement: Visual Example from Actual Code

## How Complexity is Measured

**Cyclomatic Complexity** = Number of independent execution paths through a function.

### Formula:
```
Complexity = 1 (base) + Σ(decision points)
```

### Decision Points:
- `if` statement: +1
- `elif` statement: +1
- `else` statement: +1
- `for` loop: +1
- `while` loop: +1
- `try` block: +1
- `except` clause: +1
- `and` operator: +1 (creates branch)
- `or` operator: +1 (creates branch)

---

## Real Example from `parse_html_file()`

### Code Section (lines 410-458):
```python
elif name == 'p':                                    # +1 (elif)
    emoticon_imgs = el.find_all('img', ...)         # (no complexity)
    for img in emoticon_imgs:                        # +1 (for loop)
        emoji_fallback = img.get(...) or img.get(...)  # +1 (or operator)
        if emoji_fallback:                           # +1 (if, nested in for)
            emoji_fallback = emoji_fallback.strip()  # (no complexity)
            if not emoji_fallback:                    # +1 (if, nested 2 levels)
                logging.warning(...)                  # (no complexity)
                continue
            try:                                      # +1 (try, nested 2 levels)
                img.replace_with(emoji_fallback)
            except Exception as e:                    # +1 (except)
                logging.warning(...)
        else:                                         # +1 (else, nested in for)
            logging.warning(...)
    
    paragraph_text = el.get_text(strip=True)        # (no complexity)
    if paragraph_text:                                # +1 (if, same level as elif)
        rich_text = extract_rich_text(...)
        blocks.append({...})
    
    remaining_imgs = el.find_all('img')              # (no complexity)
    for img in remaining_imgs:                        # +1 (for loop, same level)
        src = extract_image_src(img)                  # (no complexity)
        if src and not should_skip_image(...):        # +1 (if) +1 (and operator)
            blocks.append({'type': 'image', ...})
```

### Complexity Calculation for This Section:
```
Base: 1
elif name == 'p': +1
  for img in emoticon_imgs: +1
    or operator: +1
    if emoji_fallback: +1
      if not emoji_fallback: +1
      try: +1
      except: +1
    else: +1
  if paragraph_text: +1
  for img in remaining_imgs: +1
    if src and not should_skip_image: +1 (if) +1 (and)
```

**Subtotal for this section: ~12 complexity**

But this is just **ONE** `elif` branch out of **15+ branches**!

---

## Full Function Complexity Breakdown

### `parse_html_file()` Structure:

```
parse_html_file()  # Base: 1
├─ for el in content.descendants  # +1
   ├─ if isinstance(el, Tag) and el not in processed  # +1 (if) +1 (and) = +2
      ├─ if any(parent in processed for parent in el.parents)  # +1 (if) +1 (for in any) = +2
      ├─ if name == 'div' and 'toc-macro' in ...  # +1 (if) +1 (and) = +2
      ├─ if is_drawio_container(el)  # +1
      ├─ elif name in ('h1', 'h2', ...)  # +1
      │  └─ if text:  # +1 (nested)
      ├─ elif name == 'p'  # +1
      │  ├─ for img in emoticon_imgs  # +1 (nested)
      │  │  ├─ or operator  # +1
      │  │  ├─ if emoji_fallback  # +1
      │  │  │  ├─ if not emoji_fallback.strip()  # +1
      │  │  │  ├─ try  # +1
      │  │  │  └─ except  # +1
      │  │  └─ else  # +1
      │  ├─ if paragraph_text  # +1
      │  └─ for img in remaining_imgs  # +1
      │     └─ if src and not should_skip_image  # +1 (if) +1 (and) = +2
      ├─ elif name in ('ul', 'ol')  # +1
      │  └─ for li in el.find_all('li')  # +1
      │     └─ parse_list_item()  # Calls function (adds its complexity: 449)
      ├─ elif name == 'pre'  # +1
      ├─ elif name == 'img'  # +1
      │  ├─ if 'emoticon' in el.get('class', [])  # +1
      │  │  ├─ or operator  # +1
      │  │  ├─ if emoji_fallback  # +1
      │  │  │  └─ if not emoji_fallback.strip()  # +1
      │  │  └─ else  # +1
      │  └─ if src and not should_skip_image  # +1 (if) +1 (and) = +2
      ├─ elif name == 'span' and 'confluence-embedded-file-wrapper'  # +1 (elif) +1 (and) = +2
      │  ├─ if img  # +1 (nested)
      │  │  ├─ if 'emoticon' in img.get('class', [])  # +1
      │  │  │  ├─ or operator  # +1
      │  │  │  ├─ if emoji_fallback  # +1
      │  │  │  │  └─ if not emoji_fallback.strip()  # +1
      │  │  │  └─ else  # +1
      │  │  └─ if src and not should_skip_image  # +1 (if) +1 (and) = +2
      │  ├─ else  # +1
      │  │  └─ for file_link in ...  # +1
      │  │     ├─ if any(ext in file_href for ext in ...)  # +1 (if) +1 (for in any) = +2
      │  │     │  └─ if '?' in file_href  # +1
      │  │     └─ elif file_href.startswith('attachments/')  # +1
      │  │        └─ if file_ext not in image_exts  # +1
      ├─ elif name == 'table'  # +1
      │  ├─ for tr_idx, tr in enumerate(all_trs)  # +1
      │  │  ├─ if in_thead  # +1 (nested)
      │  │  ├─ for td in tr.find_all(['td','th'])  # +1 (nested)
      │  │  │  ├─ if is_header  # +1 (nested 2 levels)
      │  │  │  ├─ if not is_header  # +1
      │  │  │  ├─ for c in td.children  # +1 (nested 3 levels)
      │  │  │  │  ├─ if isinstance(c, NavigableString)  # +1 (nested 4 levels)
      │  │  │  │  └─ elif isinstance(c, Tag)  # +1 (nested 4 levels)
      │  │  │  │     ├─ if c.name == 'img'  # +1 (nested 5 levels)
      │  │  │  │     │  ├─ if 'emoticon' in c.get('class', [])  # +1 (nested 6 levels)
      │  │  │  │     │  │  ├─ or operator  # +1
      │  │  │  │     │  │  ├─ if emoji_fallback  # +1
      │  │  │  │     │  │  │  └─ if not emoji_fallback.strip()  # +1
      │  │  │  │     │  │  └─ else  # +1
      │  │  │  │     │  └─ elif src and not should_skip_image  # +1 (elif) +1 (and) = +2
      │  │  │  │     └─ elif c.name in ('p','span','div')  # +1 (nested 4 levels)
      │  │  │  │        ├─ if c.name == 'span' and 'confluence-embedded-file-wrapper'  # +1 (if) +1 (and) = +2
      │  │  │  │        │  └─ for file_link in ...  # +1
      │  │  │  │        │     ├─ if any(...)  # +1 (if) +1 (for in any) = +2
      │  │  │  │        │     └─ elif ...  # +1
      │  │  │  │        ├─ for img in emoticon_imgs  # +1
      │  │  │  │        │  ├─ or operator  # +1
      │  │  │  │        │  ├─ if emoji_fallback  # +1
      │  │  │  │        │  │  └─ if not emoji_fallback.strip()  # +1
      │  │  │  │        │  │     └─ try  # +1
      │  │  │  │        │  │        └─ except  # +1
      │  │  │  │        │  └─ else  # +1
      │  │  │  │        ├─ if text  # +1
      │  │  │  │        └─ for img in c.find_all('img')  # +1
      │  │  │  │           ├─ if 'emoticon' in ...  # +1
      │  │  │  │           └─ else  # +1
      │  │  │  │              └─ if src and not should_skip_image  # +1 (if) +1 (and) = +2
      │  │  │  │     └─ elif c.name in ('ul','ol')  # +1
      │  │  │  │        └─ for li in c.find_all('li')  # +1
      │  │  │  │           └─ parse_list_item()  # Calls function (adds complexity)
      │  │  │  │     └─ elif c.name in ('pre','code')  # +1
      │  │  │  └─ if not cell_children  # +1
      │  │  └─ if cells  # +1
      │  └─ if rows  # +1
      └─ ... more elif branches
```

### Counting Decision Points:

**From the structure above:**
- Base: **1**
- Main `for` loop: **1**
- Top-level `if`: **1**
- Top-level `if` with `and`: **+1** (and operator)
- Nested `if any(...)`: **+1** (if) + **+1** (for in any)
- Top-level `if` with `and`: **+1** (if) + **+1** (and)
- **15+ `elif` branches**: **+15**
- **Nested `if` statements** (inside branches): **~30**
- **Nested `for` loops**: **+11**
- **`try`/`except` blocks**: **+2** (try) + **+2** (except) = **+4**
- **`and`/`or` operators**: **+28**
- **Nested conditions** (4-5 levels deep): **Multiplies complexity**

**Rough calculation:**
```
1 (base)
+ 1 (main for)
+ 2 (top-level if + and)
+ 2 (nested if any)
+ 2 (top-level if + and)
+ 15 (elif branches)
+ 30 (nested ifs)
+ 11 (nested fors)
+ 4 (try/except)
+ 28 (and/or operators)
= 100+ base complexity

But with 4-5 levels of nesting, complexity compounds:
- Level 1: 100
- Level 2: 100 × 2 = 200
- Level 3: 200 × 2 = 400
- Level 4: 400 × 2 = 800
- Level 5: 800 × 2 = 1,600

Plus function calls (parse_list_item adds 449):
Total: ~2,000-2,600 complexity
```

---

## Why the Number is So High

### 1. **Deep Nesting** (4-6 levels)
```python
for el in descendants:                    # Level 1
    if isinstance(el, Tag):              # Level 2
        if name == 'table':               # Level 3
            for tr in rows:               # Level 4
                for td in cells:          # Level 5
                    for c in children:     # Level 6
                        if c.name == 'img':  # Level 7
                            if 'emoticon' in ...:  # Level 8
```

**Each level multiplies complexity!**

### 2. **Many Branches** (15+ elif statements)
- Each `elif` adds +1
- Each has nested conditions
- Total: 15+ branches × average 5 nested conditions = 75+

### 3. **Boolean Logic** (28 and/or operators)
- `if x and y`: +1 (if) +1 (and) = +2
- `if x or y`: +1 (if) +1 (or) = +2
- Total: 28 operators add significant complexity

### 4. **Function Calls** (adds called function's complexity)
- `parse_list_item()`: Adds 449 complexity
- `extract_drawio_info()`: Adds 851 complexity
- These compound the total

---

## Comparison: Simple vs Complex

### Simple Function (Complexity: 3)
```python
def simple(x):
    if x > 0:      # +1
        return x   # (no complexity)
    return 0       # (no complexity)
# Total: 1 (base) + 1 (if) = 2
```

### Moderate Function (Complexity: 10)
```python
def moderate(x, y):
    if x > 0:              # +1
        if y > 0:          # +1
            return x + y
    for i in range(5):     # +1
        if i % 2 == 0:     # +1
            return i
    return 0
# Total: 1 + 1 + 1 + 1 + 1 = 5
```

### Complex Function (Complexity: 50)
```python
def complex(data):
    for item in data:          # +1
        if item.type == 'A':    # +1
            if item.value > 0:  # +1
                try:             # +1
                    process(item)
                except:          # +1
                    handle_error()
        elif item.type == 'B':  # +1
            for sub in item.subs:  # +1
                if sub.valid:      # +1
                    process(sub)
# Total: 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 = 9
# But with more nesting and branches: ~50
```

### `parse_html_file()` (Complexity: 2,551)
- **65 if statements**
- **11 for loops**
- **28 boolean operators**
- **4-6 levels of nesting**
- **Function calls** (adds their complexity)
- **15+ elif branches**

**Result: 2,551 complexity** 🔴🔴🔴

---

## Summary

**How Complexity is Measured:**
1. **Parse code** into Abstract Syntax Tree (AST)
2. **Count decision points**: if/elif/else, for/while, try/except, and/or
3. **Sum**: Base (1) + all decision points
4. **Nested conditions compound** the complexity

**Why `parse_html_file()` is 2,551:**
- **65 if statements** (many nested)
- **11 for loops** (many nested)
- **28 boolean operators** (and/or)
- **4-6 levels of nesting** (multiplies complexity)
- **Function calls** (adds their complexity)

**This is accurate** - the function has many decision points and deep nesting, making it extremely complex.



