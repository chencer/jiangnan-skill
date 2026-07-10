#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ngram_check.py — 字符级 n-gram 重叠检测(相似度自检)
检测生成文本是否无意识贴近语料原文。
用法: python3 ngram_check.py <语料.txt> <生成文本.txt> [n]
默认 n=10(连续10个字符完全一致即命中)
"""
import sys, re

def clean(text):
    # 去掉空白,只保留实际字符,避免换行差异干扰
    return re.sub(r'\s+', '', text)

def ngrams(text, n):
    return {text[i:i+n] for i in range(len(text) - n + 1)}

def check(corpus_path, gen_path, n=10):
    with open(corpus_path, encoding='utf-8', errors='ignore') as f:
        corpus = clean(f.read())
    with open(gen_path, encoding='utf-8', errors='ignore') as f:
        gen = clean(f.read())

    corpus_grams = ngrams(corpus, n)
    hits = []
    i = 0
    gen_len = len(gen)
    while i <= gen_len - n:
        g = gen[i:i+n]
        if g in corpus_grams:
            # 向后扩展找最长命中片段
            j = i + n
            while j <= gen_len and gen[i:j] in corpus_grams or (j <= gen_len and _extend(corpus, gen[i:j])):
                j += 1
            hits.append(gen[i:j-1] if j-1 > i+n else g)
            i = j
        else:
            i += 1

    total_grams = max(gen_len - n + 1, 1)
    hit_grams = sum(max(len(h) - n + 1, 1) for h in hits)
    overlap_rate = hit_grams / total_grams * 100

    return {
        'n': n,
        '生成文本长度': gen_len,
        '命中片段数': len(hits),
        '重叠率(%)': round(overlap_rate, 2),
        '命中片段(前10条,截断显示)': [h[:20] + ('…' if len(h) > 20 else '') for h in hits[:10]],
        '结论': '通过' if overlap_rate < 1.0 and all(len(h) < 15 for h in hits) else '需要重写命中片段',
    }

def _extend(corpus, fragment):
    return fragment in corpus

if __name__ == '__main__':
    corpus_path, gen_path = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    import json
    print(json.dumps(check(corpus_path, gen_path, n), ensure_ascii=False, indent=2))
