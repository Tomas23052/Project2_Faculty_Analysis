#!/usr/bin/env python3
"""
IPT Faculty Assessment System - Verification Script
Quick verification that all components are working properly.
"""

import sys
from pathlib import Path
import pandas as pd

def test_data_files():
    """Test that data files are available and readable"""
    print("📊 Testing data files...")
    data_dir = Path("data")
    
    if not data_dir.exists():
        print("❌ Data directory not found")
        return False
    
    essential_files = [
        "faculty_research_metrics.csv",
        "faculty_basic.csv", 
        "faculty_enhanced_complete.csv"
    ]
    
    for file in essential_files:
        file_path = data_dir / file
        if file_path.exists():
            df = pd.read_csv(file_path)
            print(f"✅ {file}: {len(df)} records")
        else:
            print(f"⚠️  {file}: not found (will be generated)")
    
    return True

def test_imports():
    """Test that all modules can be imported"""
    print("\n📦 Testing module imports...")
    
    try:
        # Add src to path
        sys.path.append(str(Path("src")))
        
        # Test core modules
        from parse_hr_pdfs import IPTHRParser
        print("✅ parse_hr_pdfs imported")
        
        from extract_basic_info import IPTProfileScraper
        print("✅ extract_basic_info imported")
        
        from collect_research_data import ResearchDataCollector
        print("✅ collect_research_data imported")
        
        # Test dashboard dependencies
        import streamlit
        import plotly.express
        import plotly.graph_objects
        print("✅ Dashboard dependencies imported")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_project_structure():
    """Test that project structure is correct"""
    print("\n📁 Testing project structure...")
    
    required_dirs = ["src", "data", "notebooks"]
    required_files = [
        "README.md",
        "requirements.txt", 
        "install.sh",
        "src/collect_all_data.py",
        "src/advanced_dashboard.py"
    ]
    
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            print(f"✅ {dir_name}/ directory exists")
        else:
            print(f"❌ {dir_name}/ directory missing")
            return False
    
    for file_name in required_files:
        if Path(file_name).exists():
            print(f"✅ {file_name} exists")
        else:
            print(f"❌ {file_name} missing")
            return False
    
    return True

def main():
    """Run all verification tests"""
    print("🎓 IPT Faculty Assessment System - Verification")
    print("=" * 50)
    
    tests = [
        test_project_structure,
        test_imports, 
        test_data_files
    ]
    
    all_passed = True
    for test in tests:
        try:
            if not test():
                all_passed = False
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ All verification tests PASSED!")
        print("\n🚀 System is ready to use:")
        print("   1. Run data collection: python src/collect_all_data.py")
        print("   2. Launch dashboard: streamlit run src/advanced_dashboard.py")
    else:
        print("❌ Some verification tests FAILED!")
        print("   Please check the installation and try running: ./install.sh")
    
    return all_passed

if __name__ == "__main__":
    main()
