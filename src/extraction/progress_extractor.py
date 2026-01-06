from typing import List, Dict, Optional
from src.preprocessing.bible_reference_normalizer import BibleReferenceNormalizer
from src.extraction.semantic_matcher import SemanticBookMatcher

class ProgressExtractor:
    """
    Main orchestrator for extracting bible reading progress.
    combines rule-based, and semantics
    """

    def __init__(self):
        self.normalizer = BibleReferenceNormalizer()
        self.semantic_matcher = SemanticBookMatcher()

        self.extraction_stats = {
            'rule_based': 0,
            'semantic': 0,
            'failed': 0
        }

    def extract(self, message: str) -> List[Dict]:

        refs = self.normalizer.extract_all_references(message)

        if refs and all(ref['is_valid'] for ref in refs):
            self.extraction_stats['rule_based'] += 1
            return self.enrich_results(refs, method='rule_based')
        
        semantic_refs = self.semantic_matcher.extract_with_correction(message)

        if semantic_refs:
            self.extraction_stats['semantic'] += 1
            return self.enrich_results(semantic_refs, method='semantic')
        
    
    def enrich_results(self, refs: List[Dict], method: str) -> List[Dict]:
        for ref in refs:
            ref['extraction_method'] = method
        return refs
    
    def get_stats(self) -> Dict:
        return self.extraction_stats