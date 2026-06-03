import pandas as pd

class TestClassifyOne:
    def test_returns_progress_label(self, classifier):
        classifier.model.predict.return_value = [1]
        assert classifier.classify_one('Kej 1-3 done') == 'progress'
    
    def test_returns_non_progress_label(self, classifier):
        classifier.model.predict.return_value = [0]
        assert classifier.classify_one('Selamat pagi semua') == 'non-progress'
    
    def test_empty_string_does_not_raise(self, classifier):
        classifier.model.predict.return_value = [0]
        result = classifier.classify_one('')
        assert result in ('progress', 'non-progress')
    
    def test_none_coerced_to_empty_string(self, classifier):
        classifier.model.predict.return_value = [0]
        result = classifier.classify_one(None)
        assert result in ('progress', 'non-progress')

class TestClassify:
    def df(self, messages):
        return pd.DataFrame({'message': messages})
    
    def test_adds_label_column(self, classifier):
        classifier.model.predict.return_value = [1, 0]
        result = classifier.classify(self.df(['Kej 1-3 done', 'Selamat pagi semua']))
        assert 'label' in result.columns
    
    def test_label_values_are_mapped_correctly(self, classifier):
        classifier.model.predict.return_value = [1, 0]
        result = classifier.classify(self.df(['Kej 1-3 done', 'Selamat pagi semua']))
        assert list(result['label']) == ['progress', 'non-progress']
    
    def test_returns_copy_by_default(self, classifier):
        classifier.model.predict.return_value = [1]
        df = self.df(['Kej 1-3 done'])
        result = classifier.classify(df)
        assert 'label' not in df.columns
        assert 'label' in result.columns
    
    def test_inplace_modifies_the_original(self, classifier):
        classifier.model.predict.return_value = [1]
        df = self.df(['Kej 1-3 done'])
        classifier.classify(df, inplace=True)
        assert 'label' in df.columns
    
    def test_custom_text_column(self, classifier):
        classifier.model.predict.return_value = [1]
        df = pd.DataFrame({'text': ['Kej 1-3 done']})
        result = classifier.classify(df, text_column='text')
        assert result.iloc[0]['label'] == 'progress'
    
    def test_nan_message_handled(self, classifier):
        classifier.model.predict.return_value = [0]
        result = classifier.classify(self.df([None]))
        assert result.iloc[0]['label'] == 'non-progress'
    
    def test_index_preserved(self, classifier):
        classifier.model.predict.return_value = [1, 0]
        df = self.df(['Kej 1-3 done', 'Selamat pagi semua'])
        df.index = [10, 20]
        result = classifier.classify(df)
        assert list(result.index) ==  [10, 20]