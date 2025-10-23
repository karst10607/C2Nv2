# Notion Importer V3 Series Refactoring Plan

## Overview
This document tracks the refactoring progress for the V3 series of Notion Importer. Each phase represents a specific improvement area with clear completion criteria.

**Start Version:** 3.1.2  
**Target Version:** 3.1.9  
**Version Strategy:** +0.0.1 for each phase completion  
**Total Estimated Time:** 55-75 hours (7-10 days of focused work)

### Version Strategy
Since versions 2.5.0 through 3.0.0 already exist as tags, we'll use:
- **+0.0.1** for each refactoring phase
- **3.1.9** for the final refactored release
- Tag with `-refactor` suffix if needed to avoid conflicts

---

## Phase Tracking

### ✅ Phase 1: Extract Constants and Magic Numbers
**Target Version:** 3.1.3  
**Estimated Time:** 2-3 hours  
**Actual Time:** 45 minutes  
**Status:** ✅ COMPLETED

#### Completion Criteria:
- [x] Create `src/constants.py` with all magic numbers
- [x] Replace all hardcoded values in codebase
- [x] No magic numbers in any Python file
- [x] All tests pass

#### Files to Modify:
- Create: `src/constants.py`
- Update: `src/importer.py`, `src/transform.py`, `src/notion_api.py`, `src/verification.py`

#### How to Verify Completion:
```bash
# Should return 0 results (except in constants.py)
grep -r "2000\|600\|80\|0.35" src/ --exclude="constants.py"
```

---

### ✅ Phase 2: Create Proper Configuration Model
**Target Version:** 3.1.4  
**Estimated Time:** 3-4 hours  
**Actual Time:** 1.5 hours  
**Status:** ✅ COMPLETED (with bonus error handling)

#### Completion Criteria:
- [x] Create `src/models/config.py` with StrategyConfig dataclass
- [x] Remove inline StrategyConfig class from `importer.py`
- [x] Update all configuration usage
- [x] Config validation working
- [x] BONUS: Central error handling system (errors.py)
- [x] BONUS: Logger module for future use

#### Files to Modify:
- Create: `src/models/config.py`, `src/models/__init__.py`
- Update: `src/importer.py`, `src/upload_strategies.py`

#### How to Verify Completion:
```bash
# Should show no results
grep -n "class StrategyConfig:" src/importer.py
# Should show the new import
grep -n "from .models.config import StrategyConfig" src/importer.py
```

---

### ✅ Phase 3: Extract Common Image Handling Logic
**Target Version:** 3.1.5  
**Estimated Time:** 4-5 hours  
**Actual Time:** 1.5 hours (Phase 3.1 completed)

#### Completion Criteria:
- [x] Create `src/processors/media_processor.py` (expanded from image_processor)
- [x] Remove duplicate image counting logic
- [x] Remove duplicate image URL handling  
- [x] All image operations use MediaProcessor
- [x] Tests for MediaProcessor
- [ ] Phase 3.2: Add advanced media support (SVG, documents)
- [ ] Phase 3.3: Media conversion pipeline

#### Files to Modify:
- Create: `src/processors/image_processor.py`, `src/processors/__init__.py`
- Update: `src/importer.py`, `src/transform.py`, `src/verification.py`
- Delete duplicate functions

#### How to Verify Completion:
```bash
# Check for duplicate image counting functions (should be only in image_processor.py)
grep -r "count_images" src/
# Check for duplicate URL handling
grep -r "image\['external'\]\['url'\]" src/
```

---

### ✅ Phase 4: Refactor HTML Parser
**Target Version:** 3.1.6  
**Estimated Time:** 3-4 hours  
**Actual Time:** _[To be filled]_

#### Completion Criteria:
- [ ] Extract table parsing to `_parse_table_element()`
- [ ] Extract cell parsing to `_parse_table_cell()`
- [ ] Reduce nesting to max 3 levels
- [ ] Cyclomatic complexity < 10
- [ ] All tests pass

#### Files to Modify:
- Update: `src/html_parser.py`
- Create: `tests/test_html_parser.py`

#### How to Verify Completion:
```bash
# Install radon for complexity checking
pip install radon
# Check cyclomatic complexity (should be A or B rating)
radon cc src/html_parser.py -s
```

---

### ✅ Phase 5: Split importer.py
**Target Version:** 3.1.7  
**Estimated Time:** 6-8 hours  
**Actual Time:** _[To be filled]_

#### Completion Criteria:
- [ ] Create `ImportOrchestrator` class
- [ ] Create `PageProcessor` class
- [ ] Create import result models
- [ ] Main function < 50 lines
- [ ] Each class has single responsibility
- [ ] All integration tests pass

#### Files to Modify:
- Create: `src/orchestrator/import_orchestrator.py`, `src/processors/page_processor.py`
- Create: `src/models/import_models.py`
- Update: `src/importer.py` (significantly reduced)
- Update: `python_tools/run_import.py`

#### How to Verify Completion:
```bash
# Check main function length
grep -n "def main" src/importer.py -A 100 | wc -l
# Should be < 50 lines

# Verify new structure exists
ls -la src/orchestrator/import_orchestrator.py
ls -la src/processors/page_processor.py
```

---

### ✅ Phase 6: Create Block Builder
**Target Version:** 3.1.8  
**Estimated Time:** 4-5 hours  
**Actual Time:** _[To be filled]_

#### Completion Criteria:
- [ ] Create `NotionBlockBuilder` class
- [ ] Remove all duplicate block creation code
- [ ] Consistent block formatting across codebase
- [ ] Transform.py reduced by ~40%
- [ ] Unit tests for all builder methods

#### Files to Modify:
- Create: `src/builders/block_builder.py`, `src/builders/__init__.py`
- Update: `src/transform.py` (major refactor)
- Create: `tests/test_block_builder.py`

#### How to Verify Completion:
```bash
# Check for duplicate block creation patterns
grep -r "\"type\":\"paragraph\"" src/ --exclude="block_builder.py"
# Should only appear in block_builder.py

# Check transform.py line count reduction
wc -l src/transform.py
# Should be ~100 lines (down from ~170)
```

---

### ✅ Phase 7: Add Unit Tests
**Target Version:** 3.1.9  
**Estimated Time:** 8-10 hours  
**Actual Time:** _[To be filled]_

#### Completion Criteria:
- [ ] Test coverage > 80% for new code
- [ ] All core components have unit tests
- [ ] Integration tests for critical paths
- [ ] CI/CD pipeline configured
- [ ] Coverage report generated

#### Files to Create:
```
tests/
├── unit/
│   ├── test_block_builder.py
│   ├── test_image_processor.py
│   ├── test_page_processor.py
│   ├── test_config_models.py
│   └── test_import_orchestrator.py
├── integration/
│   ├── test_import_flow.py
│   └── test_retry_flow.py
├── fixtures/
│   └── sample_html/
└── conftest.py
```

#### How to Verify Completion:
```bash
# Run tests with coverage
pytest --cov=src --cov-report=html --cov-report=term
# Coverage should be > 80%

# Check all new modules have tests
ls tests/unit/test_*.py | wc -l
# Should match number of new modules
```

---

## Version Progression Guide

### How to Know When to Bump Version

Each phase completion triggers a version bump:

```
3.1.2 → 3.1.3: Phase 1 complete (Constants extracted)
3.1.3 → 3.1.4: Phase 2 complete (Config model)
3.1.4 → 3.1.5: Phase 3 complete (Image processor)
3.1.5 → 3.1.6: Phase 4 complete (Parser refactored)
3.1.6 → 3.1.7: Phase 5 complete (Importer split)
3.1.7 → 3.1.8: Phase 6 complete (Block builder)
3.1.8 → 3.1.9: Phase 7 complete (Tests added)
```

### Git Tag Management

Since versions 2.5.0 through 3.0.0 already exist, you have several options:

#### Option 1: Use Incremental Versioning (Recommended)
```bash
git tag v3.1.3 -m "Refactor Phase 1: Constants extracted"
git push origin v3.1.3
```

#### Option 2: Use Refactor Suffix
```bash
git tag v2.5.0-refactor -m "Refactor Phase 1: Constants extracted"
git push origin v2.5.0-refactor
```

#### Option 3: Force Update Existing Tags (NOT Recommended)
```bash
# Only if you're sure no one depends on the old tags
git tag -f v2.5.0 -m "Refactor Phase 1: Constants extracted"
git push origin v2.5.0 --force
```

#### Option 4: Use Feature Branch Tags
```bash
git tag refactor/phase1 -m "Phase 1: Constants extracted"
git tag refactor/phase2 -m "Phase 2: Config model"
```

### Quick Progress Check Script

Create `check_refactor_progress.py`:
```python
#!/usr/bin/env python3
import os
import subprocess

def check_phase_1():
    """Check if constants.py exists and no magic numbers remain"""
    if not os.path.exists('src/constants.py'):
        return False, "constants.py not created"
    
    result = subprocess.run(
        ['grep', '-r', '2000\|600\|80', 'src/', '--exclude=constants.py'],
        capture_output=True
    )
    if result.stdout:
        return False, "Magic numbers still present"
    return True, "Phase 1 complete"

def check_phase_2():
    """Check if config model exists"""
    if not os.path.exists('src/models/config.py'):
        return False, "config.py not created"
    
    result = subprocess.run(
        ['grep', '-n', 'class StrategyConfig:', 'src/importer.py'],
        capture_output=True
    )
    if result.stdout:
        return False, "Inline StrategyConfig still exists"
    return True, "Phase 2 complete"

# Add more phase checks...

if __name__ == "__main__":
    phases = [
        ("Phase 1: Constants", check_phase_1),
        ("Phase 2: Config Model", check_phase_2),
        # Add more...
    ]
    
    for name, check_func in phases:
        try:
            completed, message = check_func()
            status = "✅" if completed else "❌"
            print(f"{status} {name}: {message}")
        except Exception as e:
            print(f"❌ {name}: Error - {e}")
```

---

## Time Estimation Methodology

### How I Estimated Each Phase:

1. **Phase 1 (2-3 hours)**: Simple find/replace operations
   - 30 min: Create constants.py
   - 1-2 hours: Find and replace all occurrences
   - 30 min: Testing

2. **Phase 2 (3-4 hours)**: Structural change with validation
   - 1 hour: Design and create dataclass
   - 1-2 hours: Refactor usage points
   - 1 hour: Testing and validation

3. **Phase 3 (4-5 hours)**: Extract complex logic
   - 1 hour: Design unified interface
   - 2-3 hours: Extract and consolidate logic
   - 1 hour: Update all usage points

4. **Phase 4 (3-4 hours)**: Refactor within single file
   - 1 hour: Extract methods
   - 1-2 hours: Reduce complexity
   - 1 hour: Testing

5. **Phase 5 (6-8 hours)**: Major architectural change
   - 2 hours: Design new structure
   - 3-4 hours: Implementation
   - 1-2 hours: Integration and testing

6. **Phase 6 (4-5 hours)**: Pattern extraction
   - 1 hour: Design builder API
   - 2-3 hours: Implementation
   - 1 hour: Refactor usage

7. **Phase 7 (8-10 hours)**: Comprehensive testing
   - 2 hours: Test setup and fixtures
   - 4-5 hours: Writing unit tests
   - 2-3 hours: Integration tests

### Factors Affecting Time:
- **Positive**: Clear codebase, good separation already exists
- **Negative**: Limited existing tests, some complex nesting
- **Unknown**: Hidden dependencies, edge cases

---

## Tracking Template

For each phase, track:
```markdown
### Phase X Progress
**Started:** [Date]
**Completed:** [Date]
**Actual Hours:** [X]
**Blockers:** [Any issues]
**Notes:** [Lessons learned]
```

---

## Success Indicators

You'll know the refactoring is successful when:
1. New features can be added by modifying 1-2 files instead of 5-6
2. Unit tests can be written without extensive mocking
3. New developers understand the code flow in < 1 hour
4. Performance remains the same or improves
5. Bug fixes don't cause regressions elsewhere
