# recommendation/engine/multi_source_trainer.py
class QuantumEnsembleTrainer:
    """多源量子态模型融合引擎 - 绕过ID空间断层"""

    def __init__(self):
        self.local_model = GBDTRecommender(prefix='local')
        self.kaggle_model = GBDTRecommender(prefix='kaggle')
        self.ensemble_weights = {'local': 0.65, 'kaggle': 0.35}

    def train_local_model(self):
        """爬虫数据训练管道"""
        X, y = self._prepare_local_data()
        return self.local_model.fit(X, y)

    def train_kaggle_model(self, kaggle_dir):
        """Kaggle独立训练管道"""
        # 直接使用原始ID空间，不做映射
        df = self._load_kaggle_data(kaggle_dir)
        X, y = self._prepare_kaggle_features(df)
        return self.kaggle_model.fit(X, y)

    def predict(self, user_features, anime_features):
        """集成预测 - 后验概率融合"""
        # 检查此anime是否在本地ID空间
        if anime_features['in_local_space']:
            # 本地空间ID - 高权重使用本地模型
            local_pred = self.local_model.predict(user_features, anime_features)
            kaggle_pred = self.kaggle_model.predict_with_similar_features(user_features, anime_features)
            return local_pred * 0.8 + kaggle_pred * 0.2
        else:
            # 只存在于Kaggle空间 - 只用Kaggle模型
            return self.kaggle_model.predict(user_features, anime_features)