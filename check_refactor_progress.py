#!/usr/bin/env python3
"""
Check refactoring progress for V3 series
Run this script to see which phases are complete
"""
import os
import subprocess
import sys
from pathlib import Path

def run_grep(pattern, path, exclude=None):
    """Run grep and return stdout"""
    cmd = ['grep', '-r', pattern, path]
    if exclude:
        cmd.extend(['--exclude', exclude])
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def check_phase_1():
    """Check if constants.py exists and no magic numbers remain"""
    if not os.path.exists('src/constants.py'):
        return False, "constants.py not created"
    
    # Check for common magic numbers
    stdout = run_grep(r'2000\|600\|80\|0\.35', 'src/', 'constants.py')
    if stdout:
        lines = len(stdout.strip().split('\n'))
        return False, f"Magic numbers still present ({lines} occurrences)"
    return True, "All magic numbers extracted"

def check_phase_2():
    """Check if config model exists"""
    if not os.path.exists('src/models/config.py'):
        return False, "models/config.py not created"
    
    # Check for inline StrategyConfig
    result = subprocess.run(
        ['grep', '-n', 'class StrategyConfig:', 'src/importer.py'],
        capture_output=True, text=True
    )
    if result.stdout:
        return False, "Inline StrategyConfig still exists in importer.py"
    return True, "Config model properly extracted"

def check_phase_3():
    """Check if image processor exists"""
    if not os.path.exists('src/processors/image_processor.py'):
        return False, "processors/image_processor.py not created"
    
    # Check for duplicate image counting
    count_funcs = run_grep('def count_images', 'src/')
    if count_funcs.count('def count_images') > 1:
        return False, "Duplicate image counting functions exist"
    
    # Check for duplicate image URL handling
    url_handling = run_grep(r"image\['external'\]\['url'\]", 'src/')
    if url_handling and 'image_processor.py' not in url_handling:
        return False, "Image URL handling not centralized"
    
    return True, "Image handling centralized"

def check_phase_4():
    """Check HTML parser complexity"""
    try:
        # Try to use radon if available
        result = subprocess.run(
            ['radon', 'cc', 'src/html_parser.py', '-s', '-n', 'C'],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout:
            return False, f"High complexity detected:\n{result.stdout}"
        
        # Check for table parsing methods
        if '_parse_table_element' not in open('src/html_parser.py').read():
            return False, "Table parsing not extracted to separate method"
            
        return True, "Parser complexity reduced"
    except:
        return None, "Install radon to check complexity: pip install radon"

def check_phase_5():
    """Check if importer.py is split"""
    required_files = [
        'src/orchestrator/import_orchestrator.py',
        'src/processors/page_processor.py',
        'src/models/import_models.py'
    ]
    
    for file in required_files:
        if not os.path.exists(file):
            return False, f"{file} not created"
    
    # Check main function length
    try:
        with open('src/importer.py', 'r') as f:
            content = f.read()
            main_start = content.find('def main(')
            if main_start == -1:
                return False, "main() function not found"
            
            # Rough line count after main
            main_content = content[main_start:]
            lines = main_content.split('\n')
            
            # Find the end of main function (next def or end of file)
            main_lines = 0
            indent_level = None
            for line in lines[1:]:
                if line.strip() and indent_level is None:
                    indent_level = len(line) - len(line.lstrip())
                if line.strip() and not line.startswith(' ' * indent_level):
                    break
                main_lines += 1
            
            if main_lines > 50:
                return False, f"main() function too long ({main_lines} lines)"
                
    except Exception as e:
        return False, f"Error checking main function: {e}"
    
    return True, "importer.py properly split"

def check_phase_6():
    """Check if block builder exists"""
    if not os.path.exists('src/builders/block_builder.py'):
        return False, "builders/block_builder.py not created"
    
    # Check for duplicate block creation
    block_patterns = run_grep(r'"type":\s*"paragraph"', 'src/', 'block_builder.py')
    if block_patterns:
        occurrences = len(block_patterns.strip().split('\n'))
        if occurrences > 3:  # Allow some in tests
            return False, f"Duplicate block creation patterns ({occurrences} found)"
    
    # Check transform.py size
    if os.path.exists('src/transform.py'):
        lines = len(open('src/transform.py').readlines())
        if lines > 120:
            return False, f"transform.py still too large ({lines} lines)"
    
    return True, "Block builder implemented"

def check_phase_7():
    """Check test coverage"""
    test_files = [
        'tests/unit/test_block_builder.py',
        'tests/unit/test_image_processor.py',
        'tests/unit/test_page_processor.py',
        'tests/unit/test_config_models.py',
    ]
    
    missing_tests = [f for f in test_files if not os.path.exists(f)]
    if missing_tests:
        return False, f"Missing test files: {', '.join(missing_tests)}"
    
    # Try to run coverage
    try:
        result = subprocess.run(
            ['pytest', '--cov=src', '--cov-report=term', '-q'],
            capture_output=True, text=True
        )
        if 'TOTAL' in result.stdout:
            for line in result.stdout.split('\n'):
                if 'TOTAL' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        coverage = int(parts[-1].rstrip('%'))
                        if coverage < 80:
                            return False, f"Coverage too low ({coverage}%)"
                        return True, f"Good test coverage ({coverage}%)"
    except:
        pass
    
    return None, "Run 'pytest --cov=src' to check coverage"

def get_current_version():
    """Try to determine current version from git tags or files"""
    try:
        result = subprocess.run(['git', 'describe', '--tags'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return "Unknown"

def main():
    print("=" * 60)
    print("Notion Importer V3 Refactoring Progress Check")
    print("=" * 60)
    print(f"Current Version: {get_current_version()}")
    print()
    
    phases = [
        ("Phase 1: Extract Constants", check_phase_1, "3.1.3"),
        ("Phase 2: Config Model", check_phase_2, "3.1.4"),
        ("Phase 3: Image Processor", check_phase_3, "3.1.5"),
        ("Phase 4: Parser Refactor", check_phase_4, "3.1.6"),
        ("Phase 5: Split Importer", check_phase_5, "3.1.7"),
        ("Phase 6: Block Builder", check_phase_6, "3.1.8"),
        ("Phase 7: Unit Tests", check_phase_7, "3.1.9"),
    ]
    
    completed_phases = 0
    for name, check_func, target_version in phases:
        try:
            result = check_func()
            if result is None:
                continue
                
            completed, message = result
            if completed:
                status = "✅"
                completed_phases += 1
            else:
                status = "❌"
            
            print(f"{status} {name} (→ v{target_version})")
            print(f"   {message}")
            print()
            
        except Exception as e:
            print(f"❌ {name}: Error - {e}")
            print()
    
    print("=" * 60)
    print(f"Progress: {completed_phases}/{len(phases)} phases complete")
    print(f"Next version target: v{phases[completed_phases][2] if completed_phases < len(phases) else '3.1.9'}")
    print("=" * 60)
    
    if completed_phases == 0:
        print("\nNote: Using incremental +0.0.1 versioning for refactor phases")
        print("Each completed phase increases version by 0.0.1")

if __name__ == "__main__":
    main()
