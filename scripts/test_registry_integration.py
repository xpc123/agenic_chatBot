#!/usr/bin/env python3
import sys
sys.path.insert(0, 'backend')

from app.core.agent_engine import init_tool_registry, get_tool_registry, get_tools_from_registry

print("Initializing tool registry...")
registry = init_tool_registry(load_builtin=True, load_extended=True)

print("\n=== Registered Tools ===")
for t in registry.list_tools():
    name = t["name"]
    cat = t["category"]
    perm = t["permission"]
    print("  - %s: %s (%s)" % (name, cat, perm))

total = len(registry.get_tool_names())
print("\nTotal: %d tools" % total)

print("\n=== Get tools from registry ===")
tools = get_tools_from_registry()
print("Got %d tools" % len(tools))

print("\n=== Filter by builtin category ===")
builtin_tools = get_tools_from_registry(categories=["builtin"])
print("Builtin tools: %d" % len(builtin_tools))

print("\nDone!")
