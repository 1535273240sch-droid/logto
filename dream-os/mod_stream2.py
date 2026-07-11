import sys

with open(sys.argv[1], "r") as f:
    content = f.read()

old = 'if intent.intent_type == "image_generation" or any('
new = 'if intent.intent_type == "image" or any('
content = content.replace(old, new)

with open(sys.argv[1], "w") as f:
    f.write(content)

print("Fixed")