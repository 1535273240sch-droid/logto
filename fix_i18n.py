#!/usr/bin/env python3
"""Fix English/Chinese mixing in Dream OS frontend pages."""

fixes = [
    ('/dream-os/frontend/project-workspace.html', [
        ('<title>Dream OS \u2014 Project Workspace \u9879\u76ee\u5de5\u4f5c\u533a</title>',
         '<title>Dream OS \u00b7 \u9879\u76ee\u5de5\u4f5c\u533a</title>'),
        ('<div class="badge">Project Workspace \u00b7 \u7b2c\u4e09\u9636\u6bb5</div>',
         '<div class="badge">\u9879\u76ee\u5de5\u4f5c\u533a \u00b7 \u7b2c\u4e09\u9636\u6bb5</div>'),
    ]),
    ('/dream-os/frontend/status-widget.html', [
        ('Dream OS \u2014 AI \u5de5\u4f5c\u72b6\u6001\u53ef\u89c6\u5316',
         'Dream OS \u00b7 \u667a\u80fd\u5bf9\u8bdd'),
        ('<div class="badge">AI \u5de5\u4f5c\u72b6\u6001\u53ef\u89c6\u5316 \u00b7 Phase 1</div>',
         '<div class="badge">\u667a\u80fd\u5bf9\u8bdd \u00b7 \u7b2c\u4e00\u9636\u6bb5</div>'),
        ('<h1>Dream OS</h1>',
         '<h1>Dream OS \u667a\u80fd\u5de5\u4f5c\u53f0</h1>'),
    ]),
    ('/dream-os/frontend/tool-center.html', [
        ('Dream OS \u2014 Tool Center \u5de5\u5177\u4e2d\u5fc3',
         'Dream OS \u00b7 \u5de5\u5177\u4e2d\u5fc3'),
        ('<div class="badge">Tool Center \u00b7 \u7b2c\u4e8c\u9636\u6bb5</div>',
         '<div class="badge">\u5de5\u5177\u4e2d\u5fc3 \u00b7 \u7b2c\u4e8c\u9636\u6bb5</div>'),
    ]),
]

for filepath, changes in fixes:
    with open(filepath, 'r') as f:
        content = f.read()
    original = content
    for old, new in changes:
        if old in content:
            content = content.replace(old, new)
            print(f'  OK {filepath.split("/")[-1]}: replaced')
        else:
            print(f'  MISS {filepath.split("/")[-1]}: pattern not found')
            print(f'      looking for: {repr(old[:80])}')
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f'  -> saved')
    print()