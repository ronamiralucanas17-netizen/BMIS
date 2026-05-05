import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.cluster import KMeans
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.exceptions import NotFittedError
import joblib
import os

class VulnerabilityClassifier:
    def __init__(self, algorithm="logistic_regression"):
        self.algorithm = algorithm
        self.model = self._build_model()
        self.model_path = f"ml_models/vulnerability_model_{self.algorithm}.joblib"
        if not os.path.exists("ml_models"):
            os.makedirs("ml_models")

    def train(self, data):
        """
        Train the model using household data.
        Expected features: ['household_size', 'num_elderly', 'num_children', 'is_near_river', 'is_near_slope']
        Target: 'vulnerability_level' (0: Low, 1: Medium, 2: High)
        """
        df = pd.DataFrame(data)
        X = df[['household_size', 'num_elderly', 'num_children', 'is_near_river', 'is_near_slope']]
        y = df['vulnerability_level']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        self.model.fit(X_train, y_train)
        joblib.dump(self.model, self.model_path)
        return self.model.score(X_test, y_test)

    def predict(self, household_data):
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
        else:
            self._train_fallback()
        data = np.array(household_data).reshape(1, -1)
        try:
            prediction = self.model.predict(data)
        except NotFittedError:
            self._train_fallback()
            prediction = self.model.predict(data)
        levels = {0: 'Low', 1: 'Medium', 2: 'High'}
        return levels[prediction[0]]

    def _train_fallback(self):
        rng = np.random.default_rng(42)
        household_size = rng.integers(1, 12, size=500)
        num_elderly = rng.integers(0, 4, size=500)
        num_children = rng.integers(0, 5, size=500)
        is_near_river = rng.integers(0, 2, size=500)
        is_near_slope = rng.integers(0, 2, size=500)

        risk_score = (
            (household_size >= 7).astype(int)
            + (num_elderly >= 2).astype(int)
            + (num_children >= 3).astype(int)
            + is_near_river
            + is_near_slope
        )
        vulnerability_level = np.clip(risk_score // 2, 0, 2)

        X = np.column_stack([household_size, num_elderly, num_children, is_near_river, is_near_slope])
        y = vulnerability_level

        self.model.fit(X, y)
        joblib.dump(self.model, self.model_path)

    def _build_model(self):
        if self.algorithm == "logistic_regression":
            return Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression(max_iter=1000))])
        if self.algorithm == "gradient_boosting":
            return GradientBoostingClassifier(random_state=42)
        return RandomForestClassifier(n_estimators=100, random_state=42)

class HouseholdClusterer:
    def __init__(self, algorithm="kmeans", n_clusters=3):
        self.algorithm = algorithm
        self.n_clusters = n_clusters
        self.model = KMeans(n_clusters=self.n_clusters, random_state=42)
        self.model_path = f"ml_models/household_clusters_{self.algorithm}_{self.n_clusters}.joblib"
        if not os.path.exists("ml_models"):
            os.makedirs("ml_models")

    def fit(self, data):
        X = np.array(data)
        self.model.fit(X)
        joblib.dump(self.model, self.model_path)
        return self.model.inertia_

    def predict(self, household_data):
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
        else:
            self._fit_fallback()
        data = np.array(household_data).reshape(1, -1)
        try:
            return int(self.model.predict(data)[0])
        except NotFittedError:
            self._fit_fallback()
            return int(self.model.predict(data)[0])

    def _fit_fallback(self):
        rng = np.random.default_rng(42)
        X = np.column_stack([
            rng.integers(1, 12, size=500),  # household_size
            rng.integers(0, 4, size=500),   # num_elderly
            rng.integers(0, 5, size=500),   # num_children
            rng.integers(0, 2, size=500),   # is_near_river
            rng.integers(0, 2, size=500),   # is_near_slope
        ])
        self.model.fit(X)
        joblib.dump(self.model, self.model_path)
