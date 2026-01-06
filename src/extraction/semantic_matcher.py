from typing import Dict, List, Optional, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from pathlib import Path
import numpy as np
import re
import json

class SemanticBookMatcher:

    def __init__(self,
                 json_path: Optional[str] = None,
                 model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2',
                 similarity_threshold: float = 0.7):
        
        self.model = SentenceTransformer(model_name)
        self.similarity_threshold = similarity_threshold
        
        # Load bible data automatically
        if json_path is None:
            json_path = self.find_bible_json()
        
        self.bible_data = self.load_bible_data(json_path)
        
        self.book_embeddings = self.precompute_embeddings()
    
    def find_bible_json(self) -> str:
        path = Path(__file__).parent / '../../data/bible_references.json'
        path = path.resolve()

        if not path.exists():
            raise FileNotFoundError(
                f"could not find bible_references.json at {path}"
            )

        return str(path)
    
    def load_bible_data(self, json_path: str) -> Dict:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    

    def precompute_embeddings(self) -> Dict:
        embeddings = {}

        for book in self.bible_data['books']:
            book_id = book['id']

            variations = [book['name']] + book['aliases']

            variation_embeddings = self.model.encode(variations)

            embeddings[book_id] = {
                'book_name': book['name'],
                'book_data': book,
                'variations': variations,
                'embeddings': variation_embeddings,
                'mean_embedding': np.mean(variation_embeddings, axis=0)
            }
        return embeddings
    
    def find_closest_book(self, query_text: str, top_k: int = 3) -> List[Tuple[Dict, float]]:

        query_embedding = self.model.encode([query_text])[0]

        similarities = []

        for book_id, book_info in self.book_embeddings.items():

            sim = cosine_similarity([query_embedding], [book_info['mean_embedding']])[0][0]

            similarities.append({
                'book_data':  book_info['book_data'],
                'similarity': float(sim),
                'matched_variation':self.find_best_variation(query_embedding, book_info)
            })
        
        similarities.sort(key=lambda x: x['similarity'], reverse=True)

        matches = [
            (item['book_data'], item['similarity'], item['matched_variation'])
            for item in similarities[:top_k]
            if item['similarity'] >= self.similarity_threshold
        ]

        return matches
    

    def find_best_variation(self, query_embedding: np.ndarray, book_info: Dict) -> str:

        similarities = cosine_similarity([query_embedding], book_info['embeddings'])

        best_idx = np.argmax(similarities)
        return book_info['variations'][best_idx]

    def correct_typo(self, query_text: str) -> Optional[Dict]:

        matches = self.find_closest_book(query_text, top_k=1)

        if not matches:
            return None

        book_data, similarity, matched_variation = matches[0]

        return {
            'book': book_data['name'],
            'book_id': book_data['id'],
            'book_data': book_data,
            'confidence': similarity,
            'original_query': query_text,
            'matched_via': matched_variation,
            'correction_applied': True 
        }
    
    def extract_with_correction(self, text: str) -> List[Dict]:

        pattern = re.compile(
            r'(\d?\s?[a-zA-Z\-]+(?:\s+[a-zA-Z\-]+){0,2})\s+(\d+(?:\s*-\s*\d+)?)',
            re.IGNORECASE
        )

        results = []

        for match in pattern.finditer(text):
            book_text, chapter_text = match.groups()

            correction = self.correct_typo(book_text.strip())

            if correction:

                if '-' in chapter_text:
                    start, end = map(int, chapter_text.split('-'))
                    chapters = list(range(start, end + 1))
                else:
                    start = end = int(chapter_text)
                    chapters = [start]
                
                results.append({
                    'book': correction['book'],
                    'book_id': correction['book_id'],
                    'testament': correction['book_data']['testament'],
                    'start_chapter': start,
                    'end_chapter': end,
                    'chapters': chapters,
                    'raw_text': match.group(0),
                    'normalized_text': f"{correction['book']} {chapter_text}",
                    'confidence': correction['confidence'],
                    'typo_corrected': correction['original_query'] != correction['book']
                })
    
        return results