#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
style_stats.py — 文风统计分析(纯脚本层,无需LLM)
统计:句长分布 / 对话占比 / 段落长度 / 标点节奏
用法: python3 style_stats.py <语料.txt> [输出.json]
"""
import sys, json, re
from collections import Counter

def split_sentences(text):
    """按中文句末标点切句"""
    parts = re.split(r'(?<=[。！？…])', text)
    return [p.strip() for p in parts if p.strip()]

def analyze(path):
    with open(path, encoding='utf-8', errors='ignore') as f:
        raw = f.read()

    paragraphs = [p.strip() for p in raw.split('\n') if p.strip()]
    total_chars = sum(len(p) for p in paragraphs)

    # ---- 对话检测(中文引号 + 英文引号)----
    dialogue_re = re.compile(r'[“"](.+?)[”"]')
    dialogue_chars = 0
    dialogue_para_count = 0
    for p in paragraphs:
        matches = dialogue_re.findall(p)
        if matches:
            dialogue_para_count += 1
            dialogue_chars += sum(len(m) for m in matches)

    # ---- 句长分布 ----
    sentences = []
    for p in paragraphs:
        sentences.extend(split_sentences(p))
    sent_lens = [len(s) for s in sentences]

    def bucket(lens):
        b = Counter()
        for L in lens:
            if L <= 8:    b['短句(≤8字)'] += 1
            elif L <= 20: b['中句(9-20字)'] += 1
            elif L <= 40: b['长句(21-40字)'] += 1
            else:         b['超长句(>40字)'] += 1
        total = sum(b.values()) or 1
        return {k: round(v/total*100, 1) for k, v in b.items()}

    # ---- 段落长度分布 ----
    para_lens = [len(p) for p in paragraphs]
    def para_bucket(lens):
        b = Counter()
        for L in lens:
            if L <= 30:    b['极短段(≤30字)'] += 1
            elif L <= 80:  b['短段(31-80字)'] += 1
            elif L <= 200: b['中段(81-200字)'] += 1
            else:          b['长段(>200字)'] += 1
        total = sum(b.values()) or 1
        return {k: round(v/total*100, 1) for k, v in b.items()}

    # ---- 分句级分析(检测逗号粘连碎片) ----
    def clause_analysis(sents):
        clause_lens = []
        glued = 0  # 粘连句:分句数>=4 且 分句平均长<=7字
        for s in sents:
            clauses = [c for c in re.split(r'[，,、；;]', re.sub(r'[。！？…]', '', s)) if c.strip()]
            if not clauses:
                continue
            lens = [len(c) for c in clauses]
            clause_lens.extend(lens)
            if len(clauses) >= 4 and sum(lens)/len(lens) <= 7:
                glued += 1
        avg_clause = round(sum(clause_lens)/max(len(clause_lens),1), 1)
        short_clause_pct = round(sum(1 for L in clause_lens if L <= 5)/max(len(clause_lens),1)*100, 1)
        return avg_clause, short_clause_pct, round(glued/max(len(sents),1)*100, 1)

    avg_clause_len, short_clause_pct, glued_sent_pct = clause_analysis(sentences)

    # ---- 常见"AI腔"信号词频率(每万字) ----
    ai_markers = ['仿佛', '宛如', '像是', '似乎', '如同']
    marker_freq = {w: round(raw.count(w) / total_chars * 10000, 2) for w in ai_markers}

    # ---- 省略号/破折号节奏 ----
    punct_freq = {
        '省略号…(每万字)': round(raw.count('…') / total_chars * 10000, 2),
        '破折号—(每万字)': round(raw.count('—') / total_chars * 10000, 2),
        '感叹号(每万字)': round(raw.count('！') / total_chars * 10000, 2),
        '问号(每万字)': round(raw.count('？') / total_chars * 10000, 2),
    }

    result = {
        '总字数': total_chars,
        '总段落数': len(paragraphs),
        '总句数': len(sentences),
        '平均句长(字)': round(sum(sent_lens)/max(len(sent_lens),1), 1),
        '句长分布(%)': bucket(sent_lens),
        '平均段落长(字)': round(sum(para_lens)/max(len(para_lens),1), 1),
        '段落长度分布(%)': para_bucket(para_lens),
        '平均分句长(逗号切,字)': avg_clause_len,
        '极短分句占比(≤5字,%)': short_clause_pct,
        '粘连句占比(≥4分句且均长≤7字,%)': glued_sent_pct,
        '含对话段落占比(%)': round(dialogue_para_count/max(len(paragraphs),1)*100, 1),
        '对话字数占比(%)': round(dialogue_chars/max(total_chars,1)*100, 1),
        '比喻信号词频率(每万字)': marker_freq,
        '标点节奏(每万字)': punct_freq,
    }
    return result

if __name__ == '__main__':
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    r = analyze(path)
    s = json.dumps(r, ensure_ascii=False, indent=2)
    print(s)
    if out:
        with open(out, 'w', encoding='utf-8') as f:
            f.write(s)
