# Refactoring Priority & Macro Detection Analysis

## Current State Analysis

### Complexity Metrics
```
parse_html_file(): 2,551 complexity (CRITICAL)
├─ 65 if statements
├─ 11 for loops  
├─ 15+ elif branches
├─ 4-6 levels of nesting
└─ 380+ lines of code in one function
```

### Macro Detection Status
- **JIRA Macros**: ❌ Not implemented
- **Google Embeds**: ❌ Not implemented
- **Draw.io**: ✅ Already implemented
- **TOC Macro**: ✅ Skipped (line 389)

---

## What Needs Refactoring First

### Priority 1: Extract Element Handlers (CRITICAL)
**Why**: Reduce complexity from 2,551 to ~200-300

1. **Extract Paragraph Handler**
   ```python
   def parse_paragraph(el: Tag, colorid_map: Dict) -> List[Dict]:
       # Lines 411-458 (47 lines)
       # Complexity: ~12
   ```

2. **Extract Table Handler**
   ```python
   def parse_table(el: Tag, colorid_map: Dict) -> Dict:
       # Lines 621-755 (134 lines!)
       # Complexity: ~400-500
   ```

3. **Extract Image Handler**
   ```python
   def parse_image(el: Tag) -> Optional[Dict]:
       # Lines 473-498 (25 lines)
       # Complexity: ~10
   ```

4. **Extract Embedded Wrapper Handler**
   ```python
   def parse_embedded_wrapper(el: Tag, colorid_map: Dict) -> List[Dict]:
       # Lines 499-567 (68 lines)
       # Complexity: ~50
   ```

5. **Extract List Handler**
   ```python
   def parse_list(el: Tag, colorid_map: Dict) -> Dict:
       # Lines 459-467 (8 lines)
       # Complexity: ~5
   ```

### Priority 2: Create Element Router
```python
def parse_html_file(path: Path) -> Dict[str, Any]:
    # Setup code...
    
    element_handlers = {
        'h1': parse_heading,
        'h2': parse_heading,
        'p': parse_paragraph,
        'table': parse_table,
        'img': parse_image,
        'ul': parse_list,
        'ol': parse_list,
        # etc...
    }
    
    for el in content.descendants:
        if handler := element_handlers.get(el.name):
            result = handler(el, context)
            if result:
                blocks.extend(result if isinstance(result, list) else [result])
```

### Priority 3: Extract Helper Functions
- `process_table_cell()` - Extract from table handler
- `convert_emoticons_to_emoji()` - Common pattern
- `process_inline_images()` - Common pattern

---

## Macro Detection: Before or After Refactoring?

### Option A: Add Macro Detection AFTER Refactoring ✅ (RECOMMENDED)

**Advantages:**
1. **Clean Foundation**: Add features to clean, modular code
2. **Easy Integration**: Add new handlers to element router
3. **Clear Testing**: Test macros in isolation
4. **Lower Risk**: Won't add complexity to already complex code
5. **Faster Development**: Clear where to add macro code

**Implementation After Refactoring:**
```python
# Easy to add new handlers
element_handlers = {
    # ... existing handlers ...
    'div': lambda el, ctx: (
        parse_jira_macro(el, ctx) if is_jira_macro(el)
        else parse_google_embed(el, ctx) if is_google_embed(el)
        else parse_div(el, ctx)
    )
}

def is_jira_macro(el: Tag) -> bool:
    return 'confluence-jim-macro' in el.get('class', [])

def parse_jira_macro(el: Tag, context: Dict) -> Dict:
    # Extract JIRA data
    # Return callout block with JIRA info
    pass
```

### Option B: Add Macro Detection BEFORE Refactoring ❌ (NOT RECOMMENDED)

**Disadvantages:**
1. **Increases Complexity**: Adding to 2,551 complexity function
2. **Harder Testing**: Can't test macros in isolation
3. **Risk of Bugs**: More chance of breaking existing code
4. **Slower Progress**: Navigate complex code to add features
5. **Technical Debt**: Makes future refactoring harder

**Would look like:**
```python
# Adding to already complex parse_html_file():
elif name == 'div':
    if 'confluence-jim-macro' in el.get('class', []):
        # Parse JIRA macro (adds complexity)
    elif 'google-embed' in el.get('data-card-appearance', ''):
        # Parse Google embed (adds complexity)
    # More nested conditions...
# Complexity would jump from 2,551 to ~2,800+
```

---

## Recommended Action Plan

### Phase 1: Refactor (1-2 days)
1. **Extract `parse_table()`** - Biggest win (removes ~400 complexity)
2. **Extract `parse_paragraph()`** - Quick win
3. **Extract `parse_embedded_wrapper()`** - Moderate win
4. **Create element router** - Clean architecture
5. **Test thoroughly** - Ensure no regression

**Result**: Complexity drops from 2,551 to ~200-300

### Phase 2: Add Macro Detection (1 day)
1. **Add `is_jira_macro()` detector**
2. **Add `parse_jira_macro()` handler**
3. **Add `is_google_embed()` detector**
4. **Add `parse_google_embed()` handler**
5. **Update element router**

**Result**: Clean, testable macro support

---

## Code Examples

### Before Refactoring (Current):
```python
def parse_html_file(path: Path):  # 2,551 complexity!
    # ... 380+ lines of nested code ...
    elif name == 'table':
        # ... 134 lines of table parsing ...
        for tr in all_trs:
            if in_thead:
                # ... nested ...
            for td in tr.find_all(['td','th']):
                for c in td.children:
                    if isinstance(c, Tag):
                        if c.name == 'img':
                            if 'emoticon' in c.get('class', []):
                                # ... 6 levels deep! ...
```

### After Refactoring:
```python
def parse_html_file(path: Path):  # ~200 complexity
    # ... setup ...
    for el in content.descendants:
        if handler := get_handler(el):
            blocks.extend(handler(el, context))
    return {'title': title, 'blocks': blocks}

def parse_table(el: Tag, context: Dict) -> List[Dict]:  # ~40 complexity
    """Parse table element into Notion table block"""
    rows = []
    for tr in el.find_all('tr'):
        cells = parse_table_row(tr, context)
        if cells:
            rows.append(cells)
    return [{'type': 'table', 'rows': rows}] if rows else []

def parse_table_cell(td: Tag, context: Dict) -> Dict:  # ~20 complexity
    """Parse individual table cell"""
    # Focused, testable logic
```

### After Adding Macros (Clean):
```python
def get_handler(el: Tag) -> Optional[Callable]:
    """Get appropriate handler for element"""
    if el.name == 'div':
        if is_jira_macro(el):
            return parse_jira_macro
        elif is_google_embed(el):
            return parse_google_embed
    
    return element_handlers.get(el.name)

def parse_jira_macro(el: Tag, context: Dict) -> List[Dict]:
    """Convert JIRA macro to Notion callout"""
    jira_key = el.get('data-jira-key', '')
    jira_title = el.find(class_='summary').get_text() if el.find(class_='summary') else ''
    
    return [{
        'type': 'callout',
        'callout': {
            'rich_text': [{'type': 'text', 'text': {'content': f'JIRA: {jira_key} - {jira_title}'}}],
            'icon': {'emoji': '🎫'},
            'color': 'blue'
        }
    }]
```

---

## Complexity Reduction Forecast

### Current:
```
parse_html_file: 2,551 ❌❌❌
```

### After Refactoring:
```
parse_html_file: 200 ✅
├─ parse_table: 40 ✅
├─ parse_paragraph: 20 ✅
├─ parse_embedded_wrapper: 30 ✅
├─ parse_image: 15 ✅
├─ parse_list: 10 ✅
└─ parse_heading: 10 ✅
```

### After Adding Macros:
```
parse_html_file: 210 ✅ (+10 for routing)
├─ parse_jira_macro: 25 ✅ (new)
├─ parse_google_embed: 20 ✅ (new)
└─ ... existing handlers ...
```

---

## Decision Matrix

| Factor | Refactor First | Add Macros First |
|--------|----------------|------------------|
| **Complexity Management** | ✅ Reduces first | ❌ Increases complexity |
| **Code Quality** | ✅ Clean architecture | ❌ More technical debt |
| **Testing** | ✅ Test in isolation | ❌ Hard to test |
| **Development Speed** | ✅ Clear boundaries | ❌ Navigate complex code |
| **Risk** | ✅ Lower risk | ❌ Higher risk |
| **Future Maintenance** | ✅ Easy to extend | ❌ Harder to maintain |
| **Integration** | ✅ Clean integration | ❌ Messy integration |

**Score: 7-0 in favor of refactoring first**

---

## Conclusion

### Recommendation: **REFACTOR FIRST, THEN ADD MACROS**

1. **Immediate Action**: Start extracting `parse_table()` (biggest complexity win)
2. **Next**: Extract other element handlers
3. **Then**: Create clean element router
4. **Finally**: Add macro detection to clean architecture

### Benefits:
- ✅ Complexity: 2,551 → 200 (92% reduction)
- ✅ Testability: Each function testable in isolation
- ✅ Maintainability: Clear, focused functions
- ✅ Extensibility: Easy to add new features (macros)
- ✅ Performance: Potentially faster (less nested loops)

### Timeline:
- Day 1: Extract main handlers, reduce complexity
- Day 2: Complete refactoring, test thoroughly
- Day 3: Add macro detection cleanly

This approach gives you a solid foundation for adding macro detection and any future features.
