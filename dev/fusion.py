#!/usr/bin/env python3

import os
import sys

# Add Fusion libraries to Python path
fusion_path = "/opt/resolve/libs/Fusion"
if os.path.exists(fusion_path):
    sys.path.append(fusion_path)
    print(f"Added {fusion_path} to Python path")
else:
    print(f"WARNING: {fusion_path} does not exist!")

# Try to import fusionscript
try:
    import fusionscript as fs

    print("✅ Successfully imported fusionscript module")
except ImportError as e:
    print(f"❌ Failed to import fusionscript: {e}")
    sys.exit(1)

# Try different methods to connect to Fusion
print("Attempting to connect to Fusion...")

try:
    # Method 1: Using scriptapp with Fusion
    print("Method 1: scriptapp('Fusion')")
    fusion = fs.scriptapp("Fusion")
    if fusion:
        print("✅ Method 1 succeeded")
    else:
        print("❌ Method 1 failed (returned None)")
except Exception as e:
    print(f"❌ Method 1 exception: {e}")

try:
    # Method 2: Using scriptapp with FuScript
    print("\nMethod 2: scriptapp('FuScript')")
    fusion = fs.scriptapp("FuScript")
    if fusion:
        print("✅ Method 2 succeeded")
    else:
        print("❌ Method 2 failed (returned None)")
except Exception as e:
    print(f"❌ Method 2 exception: {e}")

try:
    # Method 3: Try to get Resolve first, then Fusion
    print("\nMethod 3: Get Resolve then Fusion")
    resolve = fs.scriptapp("Resolve")
    if resolve:
        print("✅ Connected to Resolve")
        fusion_page = resolve.GetFusionScript()
        if fusion_page:
            print("✅ Method 3 succeeded - got Fusion from Resolve")

            # Test if we can access Fusion functionality
            comps = fusion_page.GetCompList()
            if comps:
                print(f"Found {len(comps)} compositions")
        else:
            print("❌ Failed to get Fusion page from Resolve")
    else:
        print("❌ Failed to connect to Resolve")
except Exception as e:
    print(f"❌ Method 3 exception: {e}")

print("\nDebugging information:")
print(f"Python version: {sys.version}")
print(f"FusionScript module location: {fs.__file__}")
print("\nTest complete.")
