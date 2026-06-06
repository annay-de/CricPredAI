from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from scipy.sparse import csr_matrix


class EncodedOutcomeClassifier(ClassifierMixin, BaseEstimator):
    """Encode string outcomes for estimators, such as XGBoost, that require integers."""

    def __init__(self, estimator, outcome_order):
        self.estimator = estimator
        self.outcome_order = list(outcome_order)

    def fit(self, X, y, sample_weight=None):
        observed = {str(value) for value in y}
        self.classes_ = np.asarray([value for value in self.outcome_order if value in observed])
        mapping = {value: index for index, value in enumerate(self.classes_)}
        encoded = np.asarray([mapping[str(value)] for value in y], dtype=int)
        self.estimator.fit(X, encoded, sample_weight=sample_weight)
        return self

    def predict_proba(self, X):
        return self.estimator.predict_proba(X)


class OutcomeModel:
    """Stable artifact wrapper that aligns classes and applies temperature scaling."""

    def __init__(self, model, outcomes, temperature: float = 1.0):
        self.model = model
        self.classes_ = np.asarray(outcomes)
        self.temperature = float(temperature)

    def predict_proba(self, X):
        raw = np.asarray(self.model.predict_proba(X), dtype=float)
        source_classes = [str(value) for value in self.model.classes_]
        aligned = np.full((len(raw), len(self.classes_)), 1e-12, dtype=float)
        for source_index, outcome in enumerate(source_classes):
            matches = np.flatnonzero(self.classes_ == outcome)
            if len(matches):
                aligned[:, matches[0]] = raw[:, source_index]
        aligned /= aligned.sum(axis=1, keepdims=True)
        if self.temperature != 1.0:
            logits = np.log(np.clip(aligned, 1e-12, 1.0)) / self.temperature
            logits -= logits.max(axis=1, keepdims=True)
            aligned = np.exp(logits)
            aligned /= aligned.sum(axis=1, keepdims=True)
        return aligned


class FastPipelineOutcomeModel:
    """Compact single-row inference path for a fitted preprocessing pipeline."""

    def __init__(self, pipeline, numeric_features, categorical_features):
        preprocessor = pipeline.named_steps["pre"]
        self.estimator = pipeline.named_steps["classifier"]
        self.classes_ = np.asarray(self.estimator.classes_)
        self.numeric_features = list(numeric_features)
        self.categorical_features = list(categorical_features)

        numeric = preprocessor.named_transformers_["num"]
        imputer = numeric.named_steps["impute"]
        scaler = numeric.named_steps["scale"]
        self.impute_values = np.asarray(imputer.statistics_, dtype=float)
        self.numeric_means = np.asarray(scaler.mean_, dtype=float)
        self.numeric_scales = np.asarray(scaler.scale_, dtype=float)

        encoder = preprocessor.named_transformers_["cat"]
        self.category_maps = []
        offset = len(self.numeric_features)
        for feature_index, original_categories in enumerate(encoder.categories_):
            transformed = list(encoder._compute_transformed_categories(feature_index))
            mapping = {
                str(category): offset + category_index
                for category_index, category in enumerate(transformed)
                if str(category) != "infrequent_sklearn"
            }
            infrequent = encoder.infrequent_categories_[feature_index]
            infrequent_values = set(map(str, infrequent)) if infrequent is not None else set()
            infrequent_index = (
                offset + transformed.index("infrequent_sklearn")
                if "infrequent_sklearn" in transformed
                else None
            )
            self.category_maps.append((mapping, infrequent_values, infrequent_index))
            offset += len(transformed)
        self.n_output_features = offset

    def _transform(self, X):
        if not hasattr(X, "iloc"):
            return X
        row_count = len(X)
        row_indices = []
        column_indices = []
        values = []
        for row_index, (_, row) in enumerate(X.iterrows()):
            numeric = np.asarray(
                [row.get(feature, np.nan) for feature in self.numeric_features],
                dtype=float,
            )
            numeric = np.where(np.isnan(numeric), self.impute_values, numeric)
            numeric = (numeric - self.numeric_means) / self.numeric_scales
            for column_index, value in enumerate(numeric):
                if value != 0:
                    row_indices.append(row_index)
                    column_indices.append(column_index)
                    values.append(float(value))

            for feature, (mapping, infrequent, infrequent_index) in zip(
                self.categorical_features,
                self.category_maps,
                strict=True,
            ):
                category = str(row.get(feature, "Unknown"))
                output_index = mapping.get(category)
                if output_index is None and category in infrequent:
                    output_index = infrequent_index
                if output_index is not None:
                    row_indices.append(row_index)
                    column_indices.append(output_index)
                    values.append(1.0)
        return csr_matrix(
            (values, (row_indices, column_indices)),
            shape=(row_count, self.n_output_features),
            dtype=float,
        )

    def predict_proba(self, X):
        return self.estimator.predict_proba(self._transform(X))


class XGBOutcomeWrapper(OutcomeModel):
    """Legacy name retained so committed v3 artifacts can still be loaded."""

    feature_names = [
        "innings",
        "over",
        "legal_ball",
        "team_runs",
        "team_wicket",
        "batter_runs",
        "batter_balls",
        "phase_code",
    ]

    def _legacy_transform(self, X):
        import pandas as pd

        if not isinstance(X, pd.DataFrame):
            return X
        phase_map = {"powerplay": 0, "middle": 1, "death": 2}
        transformed = pd.DataFrame(index=X.index)
        for column in self.feature_names[:-1]:
            value = X[column] if column in X else 0
            if np.isscalar(value):
                value = pd.Series(value, index=X.index)
            transformed[column] = pd.to_numeric(value, errors="coerce").fillna(0)
        phase = X["phase"] if "phase" in X else pd.Series("", index=X.index)
        transformed["phase_code"] = phase.map(phase_map).fillna(1).astype(float)
        return transformed[self.feature_names].values

    def predict_proba(self, X):
        return np.asarray(self.model.predict_proba(self._legacy_transform(X)), dtype=float)
