#!/usr/bin/env python3
"""
Reusable arXiv Category Mislabel Cleaner
Apply to any CS category to remove obvious mislabels

Usage:
    python arxiv_category_cleaner.py --category cs.AI
    python arxiv_category_cleaner.py --category cs.CV --threshold 3
"""

import argparse
import json
import torch
from pathlib import Path
from typing import Dict, List, Tuple

class ArxivCategoryCleaner:
    """Remove mislabeled papers from arXiv categories"""

    # Non-CS topic indicators (papers that shouldn't be in CS categories)
    NON_CS_TOPICS = {
        'medicine': [
            'cancer', 'tumor', 'disease', 'patient', 'clinical trial', 'drug',
            'therapy', 'diagnosis', 'medical treatment', 'surgery', 'cardiovascular',
            'cardiac', 'hemophilia', 'acute kidney injury', 'respiratory distress'
        ],
        'biology': [
            'gene expression', 'protein', 'dna sequence', 'genome', 'cell biology',
            'molecular biology', 'genetic', 'transcriptome', 'biomedical'
        ],
        'chemistry': [
            'catalyst', 'chemical reaction', 'synthesis', 'molecule', 'electrocatalytic',
            'electrochemical reduction', 'co2 reduction', 'organic synthesis'
        ],
        'climate': [
            'climate change', 'global warming', 'ecosystem', 'biodiversity',
            'carbon emission', 'deforestation', 'wastewater treatment', 'environmental'
        ],
        'physics': [
            'gravitational wave', 'black hole', 'neutron star', 'dark matter',
            'quantum mechanics', 'particle physics', 'cosmology', 'coalescence'
        ],
        'materials': [
            'nanoparticle', 'crystal structure', 'alloy', 'metal oxide',
            'material science', 'polymer'
        ]
    }

    # Category-specific positive indicators (keep papers WITH these)
    CATEGORY_KEYWORDS = {
        'cs.DC': [
            'distributed', 'parallel', 'concurrency', 'cloud', 'cluster',
            'consensus', 'blockchain', 'federated learning', 'edge computing',
            'serverless', 'mapreduce', 'hadoop', 'spark', 'kubernetes',
            'microservices', 'peer-to-peer', 'replication', 'consistency'
        ],
        'cs.AI': [
            'artificial intelligence', 'machine learning', 'deep learning',
            'neural network', 'reinforcement learning', 'planning', 'reasoning',
            'knowledge representation', 'expert system'
        ],
        'cs.CV': [
            'computer vision', 'image', 'video', 'detection', 'segmentation',
            'object recognition', 'visual', 'convolutional', '3d reconstruction'
        ],
        'cs.CL': [
            'natural language', 'nlp', 'text', 'language model', 'translation',
            'sentiment analysis', 'named entity', 'parsing', 'tokenization'
        ],
        'cs.LG': [
            'machine learning', 'supervised learning', 'unsupervised learning',
            'classification', 'regression', 'clustering', 'neural network',
            'gradient descent', 'optimization'
        ],
        'cs.DB': [
            'database', 'query', 'sql', 'transaction', 'index', 'relational',
            'nosql', 'data management', 'query optimization'
        ],
        'cs.SE': [
            'software engineering', 'code', 'program', 'bug', 'testing',
            'debugging', 'software development', 'version control', 'refactoring'
        ],
        'cs.RO': [
            'robot', 'robotics', 'autonomous', 'manipulation', 'motion planning',
            'slam', 'navigation', 'control', 'actuator'
        ]
    }

    def __init__(self, papers_file: str, labels_file: str, metadata_file: str,
                 category: str, threshold: int = 3):
        """
        Args:
            papers_file: Path to papers_export.json
            labels_file: Path to labels.pt
            metadata_file: Path to graph_metadata.json
            category: Category to clean (e.g., 'cs.DC')
            threshold: Min keywords from same non-CS topic to remove (default: 3)
        """
        self.category = category
        self.threshold = threshold

        # Load data
        with open(papers_file) as f:
            self.papers = json.load(f)

        self.labels = torch.load(labels_file)

        with open(metadata_file) as f:
            metadata = json.load(f)

        self.category_idx = metadata['categories'].index(category)
        print(f"\n[LOADED] {len(self.papers)} papers, category: {category}")

    def analyze_paper(self, paper: Dict) -> Tuple[bool, str]:
        """
        Analyze if paper should be removed

        Returns:
            (should_remove, reason)
        """
        title = paper.get('title', '').lower()
        abstract = paper.get('abstract', '').lower()
        full_text = title + ' ' + abstract

        # Count non-CS topic matches
        topic_scores = {}
        for topic, keywords in self.NON_CS_TOPICS.items():
            matches = sum(1 for kw in keywords if kw in full_text)
            if matches > 0:
                topic_scores[topic] = matches

        # Remove if >= threshold keywords from same non-CS topic
        for topic, score in topic_scores.items():
            if score >= self.threshold:
                return True, f"{topic} ({score} keywords)"

        return False, ""

    def clean_labels(self) -> Tuple[torch.Tensor, List[Dict]]:
        """
        Clean labels by removing mislabeled papers

        Returns:
            (cleaned_labels, removed_papers_info)
        """
        print(f"\n[CLEANING] Removing mislabeled {self.category} papers...")

        labels_cleaned = self.labels.clone()
        removed_papers = []
        original_count = 0

        for i, paper in enumerate(self.papers):
            is_category = self.labels[i, self.category_idx].item() > 0.5

            if not is_category:
                continue

            original_count += 1

            should_remove, reason = self.analyze_paper(paper)

            if should_remove:
                labels_cleaned[i, self.category_idx] = 0.0
                removed_papers.append({
                    'idx': i,
                    'title': paper['title'],
                    'categories': paper.get('categories', []),
                    'reason': reason
                })

        final_count = labels_cleaned[:, self.category_idx].sum().item()

        print(f"\n[RESULTS]")
        print(f"  Original {self.category}: {original_count}")
        print(f"  Removed (mislabeled): {len(removed_papers)}")
        print(f"  Kept (legitimate): {final_count:.0f}")
        print(f"  Removal rate: {len(removed_papers)/original_count*100:.1f}%")

        return labels_cleaned, removed_papers

    def save_cleaned_labels(self, output_dir: str):
        """Clean and save labels with metadata"""
        labels_cleaned, removed_papers = self.clean_labels()

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save cleaned labels
        labels_file = output_path / f'labels_{self.category.replace(".", "_")}_cleaned.pt'
        torch.save(labels_cleaned, labels_file)
        print(f"\n[SAVED] Labels: {labels_file}")

        # Save metadata
        metadata = {
            'category': self.category,
            'cleaning_date': '2025-10-20',
            'method': 'targeted_topic_filtering',
            'threshold': self.threshold,
            'non_cs_topics': self.NON_CS_TOPICS,
            'statistics': {
                'original_count': int(self.labels[:, self.category_idx].sum().item()),
                'removed_count': len(removed_papers),
                'final_count': int(labels_cleaned[:, self.category_idx].sum().item())
            },
            'removed_papers_sample': removed_papers[:20]
        }

        metadata_file = output_path / f'cleaning_metadata_{self.category.replace(".", "_")}.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"[SAVED] Metadata: {metadata_file}")

        return labels_cleaned, removed_papers


def main():
    parser = argparse.ArgumentParser(description='Clean arXiv category labels')
    parser.add_argument('--category', required=True, help='Category to clean (e.g., cs.DC)')
    parser.add_argument('--papers', default='papers_export.json', help='Papers file')
    parser.add_argument('--labels', default='production/graph_db/cached_embeddings/labels.pt', help='Labels file')
    parser.add_argument('--metadata', default='production/graph_db/cached_embeddings/graph_metadata.json', help='Metadata file')
    parser.add_argument('--output', default='production/graph_db/cached_embeddings', help='Output directory')
    parser.add_argument('--threshold', type=int, default=3, help='Keyword threshold (default: 3)')

    args = parser.parse_args()

    print("="*80)
    print(f"arXiv CATEGORY CLEANER - {args.category}")
    print("="*80)

    cleaner = ArxivCategoryCleaner(
        papers_file=args.papers,
        labels_file=args.labels,
        metadata_file=args.metadata,
        category=args.category,
        threshold=args.threshold
    )

    labels_cleaned, removed_papers = cleaner.save_cleaned_labels(args.output)

    print(f"\n[SAMPLE REMOVED] (First 10)")
    for i, paper in enumerate(removed_papers[:10], 1):
        print(f"{i}. {paper['title'][:70]}")
        print(f"   Reason: {paper['reason']}")

    print(f"\n{'='*80}")
    print(f"CLEANING COMPLETE")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()
