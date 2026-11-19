import os, re

rows = []
pat = re.compile(r'^\s*(?:public|internal|private|protected|static|sealed|abstract|partial|\s)*\b(class|struct|enum|interface)\s+([A-Za-z_][A-Za-z0-9_]*)')
base = r'D:\4-player-junqi\reverse-engineering\game-01\static-analysis\decompiled'
for root, _, files in os.walk(base):
    for fn in files:
        if not fn.endswith('.cs'):
            continue
        full = os.path.join(root, fn)
        rel = os.path.relpath(full, base).replace(os.sep, '/')
        with open(full, encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                m = pat.match(line)
                if m:
                    rows.append((rel, i, m.group(1), m.group(2)))
rows.sort()
out_path = r'D:\4-player-junqi\reverse-engineering\game-01\static-analysis\full-class-index.md'
with open(out_path, 'w', encoding='utf-8', newline='\n') as out:
    out.write('# game-01 全量类型索引\n\n')
    out.write('来源：`ilspycmd` 反编译 `Assembly-CSharp.dll`，共 %d 个 class/struct/enum/interface 声明（含嵌套类型）。\n\n' % len(rows))
    out.write('| 类型 | 名称 | 文件:行 |\n|---|---|---|\n')
    for rel, i, kind, name in rows:
        out.write('| %s | `%s` | `%s:%d` |\n' % (kind, name, rel, i))
print('rows', len(rows))
