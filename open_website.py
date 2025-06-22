#!/usr/bin/env python3
"""Open the order form in browser"""

import webbrowser
import os
import subprocess
import platform

# Get the absolute path
order_form = os.path.abspath("municipal-records-website/order.html")

print(f"📋 Opening order form...")
print(f"📁 File location: {order_form}")

# Try different methods to open
try:
    # For WSL, try to open with Windows browser
    if 'microsoft' in platform.uname().release.lower():
        windows_path = subprocess.check_output(['wslpath', '-w', order_form]).decode().strip()
        print(f"🪟 Windows path: {windows_path}")
        subprocess.run(['cmd.exe', '/c', 'start', windows_path])
    else:
        # For regular Linux
        webbrowser.open(f'file://{order_form}')
    
    print("\n✅ Browser should be opening...")
    print("\nIf it doesn't open automatically, copy and paste this URL:")
    print(f"file://{order_form}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\n📋 Copy and paste this path into your browser:")
    print(f"file://{order_form}")