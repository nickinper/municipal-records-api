#!/usr/bin/env python3
"""Simple web server for the website"""

import http.server
import socketserver
import os

# Change to website directory
os.chdir('municipal-records-website')

# Start server
PORT = 8001
Handler = http.server.SimpleHTTPRequestHandler

print(f"🌐 Starting web server on http://localhost:{PORT}")
print(f"📋 Order form: http://localhost:{PORT}/order.html")
print(f"💵 Test mode: http://localhost:{PORT}/order.html?test=true&amount=2")
print("\nPress Ctrl+C to stop")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()