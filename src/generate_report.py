#!/usr/bin/env python3
"""
Generate Mislabeled Papers Report for arXiv
Create comprehensive list with evidence for arXiv submission
"""

import json
import torch
from pathlib import Path

print("="*80)
print("GENERATING MISLABELED PAPERS REPORT FOR ARXIV")
print("="*80)

# Load data
with open('papers_export.json') as f:
    papers = json.load(f)

data_dir = Path('cached_embeddings')
labels = torch.load(data_dir / 'labels.pt')

with open(data_dir / 'graph_metadata.json') as f:
    csdc_idx = json.load(f)['categories'].index('cs.DC')

# Define non-CS topic indicators
non_cs_indicators = {
    'medicine': ['cancer', 'tumor', 'patient', 'clinical', 'disease', 'drug', 'therapy',
                 'diagnosis', 'treatment', 'surgery', 'cardiovascular', 'respiratory'],
    'chemistry': ['catalyst', 'chemical reaction', 'synthesis', 'molecule', 'electrocatalytic',
                  'electrochemical', 'polymer', 'organic chemistry'],
    'biology': ['gene', 'protein', 'dna', 'rna', 'genome', 'cell', 'molecular biology'],
    'climate': ['climate change', 'ecosystem', 'biodiversity', 'carbon emission', 'deforestation'],
    'physics': ['gravitational wave', 'black hole', 'neutron star', 'quantum mechanics', 'cosmology'],
    'materials': ['nanoparticle', 'crystal', 'alloy', 'metal oxide']
}

# Find mislabeled papers
mislabeled_papers = []

for i in range(len(papers)):
    is_csdc = labels[i, csdc_idx].item() > 0.5
    if not is_csdc:
        continue

    paper = papers[i]
    title = paper.get('title', '').lower()
    abstract = paper.get('abstract', '').lower()
    full_text = title + ' ' + abstract
    categories = paper.get('categories', [])

    # Check for non-CS topics
    for topic, keywords in non_cs_indicators.items():
        matches = []
        for kw in keywords:
            if kw in full_text:
                matches.append(kw)

        if len(matches) >= 3:  # Strong evidence
            mislabeled_papers.append({
                'arxiv_id': paper.get('arxiv_id', f'paper_{i}'),
                'title': paper['title'],
                'categories_listed': categories,
                'primary_category': categories[0] if categories else 'unknown',
                'actual_topic': topic,
                'evidence_keywords': matches[:5],  # First 5 matches
                'keyword_count': len(matches),
                'abstract_snippet': paper.get('abstract', '')[:200] + '...'
            })
            break

# Sort by keyword count (strongest evidence first)
mislabeled_papers.sort(key=lambda x: x['keyword_count'], reverse=True)

print(f"\n[FOUND] {len(mislabeled_papers)} mislabeled papers in cs.DC")

# Group by topic
by_topic = {}
for paper in mislabeled_papers:
    topic = paper['actual_topic']
    if topic not in by_topic:
        by_topic[topic] = []
    by_topic[topic].append(paper)

print(f"\n[BREAKDOWN BY ACTUAL TOPIC]")
for topic, papers_list in sorted(by_topic.items(), key=lambda x: len(x[1]), reverse=True):
    print(f"  {topic}: {len(papers_list)} papers")

# Create report
report = {
    'report_date': '2025-10-20',
    'category_analyzed': 'cs.DC',
    'total_csdc_papers': int(labels[:, csdc_idx].sum().item()),
    'mislabeled_count': len(mislabeled_papers),
    'mislabel_rate': f"{len(mislabeled_papers) / labels[:, csdc_idx].sum().item() * 100:.1f}%",
    'methodology': {
        'detection_method': 'Keyword-based topic identification',
        'threshold': '3+ keywords from same non-CS topic',
        'topics_checked': list(non_cs_indicators.keys())
    },
    'mislabeled_papers': mislabeled_papers,
    'by_topic_summary': {topic: len(papers_list) for topic, papers_list in by_topic.items()}
}

# Save full report
with open('arxiv_mislabel_report.json', 'w') as f:
    json.dump(report, f, indent=2)

print(f"\n[SAVED] arxiv_mislabel_report.json")

# Create human-readable summary
print(f"\n{'='*80}")
print("SAMPLE MISLABELED PAPERS (Top 20)")
print("="*80)

for i, paper in enumerate(mislabeled_papers[:20], 1):
    print(f"\n{i}. {paper['title']}")
    print(f"   arXiv Categories: {paper['categories_listed']}")
    print(f"   Actual Topic: {paper['actual_topic'].upper()}")
    print(f"   Evidence: {', '.join(paper['evidence_keywords'])}")

print(f"\n{'='*80}")
print(f"Total mislabeled: {len(mislabeled_papers)} / {int(labels[:, csdc_idx].sum().item())} ({report['mislabel_rate']})")
print(f"Report saved for arXiv submission: arxiv_mislabel_report.json")
print("="*80)
