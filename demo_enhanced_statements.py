#!/usr/bin/env python3
"""
Demo script to showcase enhanced bank statements with employment details and human-like checkmarks
"""

from generate_multi_page_bank_statement import generate_multi_page_bank_statement
import os


def demo_enhanced_features():
    """Generate statements showcasing the new employment and income sections"""

    # Create output directory if it doesn't exist
    output_dir = "enhanced_demo_statements"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print("🎯 Generating Enhanced Bank Statements with Employment Details...")
    print("=" * 70)
    print("✨ Features included:")
    print("   • Multi-page support (1-3 pages)")
    print("   • Employment Details section")
    print("   • Income & Deposit Details section")
    print("   • Human-like checkbox ticks with natural distortions")
    print("   • Identification documents with point system")
    print("   • PDF conversion")
    print("=" * 70)

    # Generate 3 enhanced statements
    for i in range(1, 4):
        output_file = os.path.join(output_dir, f"enhanced_statement_{i}.png")
        print(f"\n📄 Generating enhanced statement {i}...")
        generate_multi_page_bank_statement(output_file)

    print("\n" + "=" * 70)
    print("✅ Enhanced demo complete! Check the 'enhanced_demo_statements' folder for:")
    print("   • PDF files with employment and income sections")
    print("   • Human-like checkbox ticks that extend outside boxes")
    print("   • Random page counts (1-3 pages each)")
    print("   • Professional multi-page bank statements")


if __name__ == "__main__":
    demo_enhanced_features()
