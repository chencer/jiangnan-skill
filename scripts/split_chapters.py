#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
split_chapters.py — 按章节标题切分语料
用法: python3 split_chapters.py <语料.txt> <输出目录>
"""
import sys, re, os

CHAPTER_RE = re.compile(r'^第[一二三四五六七八九十百千零两]+章')

def split(corpus_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    with open(corpus_path, encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # find chapter header line indices (exclude TOC lines with multiple 章 on same line)
    breaks = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if CHAPTER_RE.match(stripped):
            count = len(re.findall(r'第[一二三四五六七八九十百千零两]+章', stripped))
            if count == 1:
                breaks.append((i, stripped))

    chapters = []
    for idx, (lineno, title) in enumerate(breaks):
        start = lineno
        end = breaks[idx + 1][0] if idx + 1 < len(breaks) else len(lines)
        content = ''.join(lines[start:end])
        chapters.append((idx + 1, title, content))

    listing = ['# 章节列表\n\n', '| 编号 | 标题 | 字数 |\n', '|---|---|---|\n']
    for num, title, content in chapters:
        char_count = len(re.sub(r'\s', '', content))
        safe = re.sub(r'[^\w一-鿿]', '_', title)[:20]
        fname = f'ch_{num:03d}_{safe}.txt'
        with open(os.path.join(out_dir, fname), 'w', encoding='utf-8') as f:
            f.write(content)
        listing.append(f'| {num} | {title} | {char_count} |\n')

    with open('analysis/chapter_list.md', 'w', encoding='utf-8') as f:
        f.writelines(listing)

    print(f'切分完成：{len(chapters)} 章，章节列表 -> analysis/chapter_list.md')
    return len(chapters)

if __name__ == '__main__':
    corpus = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else 'analysis/chapters'
    split(corpus, out)
