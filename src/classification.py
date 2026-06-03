import pandas as pd
import joblib
from pathlib import Path
from typing import Union

from core.config import CLS_MODEL_PATH, CLS_VECTORIZER_PATH

LABEL_MAP = {1: 'progress', 0: 'non-progress'}

class MessageClassifier:
    def __init__(self, 
                 model_path: Union[str, Path] = CLS_MODEL_PATH, 
                 vectorizer_path: Union[str, Path] = CLS_VECTORIZER_PATH):
        self.model = joblib.load(model_path)
        self.vectorizer = joblib.load(vectorizer_path)

    def classify_one(self, text: str) -> str:
        """
        Classify a single message string.

        Args:
            text: Raw message text
        
        Returns:
            label: 'progress' or 'non-progress'
        """
        result = self.classify(pd.DataFrame([{'message': text or ''}]))
        return result.iloc[0]['label']
    

    def classify(self, df: pd.DataFrame, text_column: str = 'message', inplace: bool = False):
        """
        Classify messages as progress or non-progress.

        Args:
            df: Input DataFrame
            text_column: Name of column containing text to classify
            inplace: if True, modify df in place; if False, return a copy

        Returns:
            DataFrame with added columns:
            - label: label ('progress' or 'non-progress')
        """
        if not inplace:
            df = df.copy()
        
        X = self.vectorizer.transform(df[text_column].fillna(''))
        df['label'] = pd.Series(
            self.model.predict(X), index=df.index
        ).map(LABEL_MAP)
        
        return df