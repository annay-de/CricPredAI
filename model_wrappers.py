import numpy as np
import pandas as pd

class XGBOutcomeWrapper:
    def __init__(self, model, outcomes):
        self.model = model
        self.classes_ = np.array(outcomes)
        self.feature_names = ["innings","over","legal_ball","team_runs","team_wicket","batter_runs","batter_balls","phase_code"]
    def _transform(self, X):
        if isinstance(X, pd.DataFrame):
            phase_map={"powerplay":0,"middle":1,"death":2}
            Z=pd.DataFrame()
            for c in ["innings","over","legal_ball","team_runs","team_wicket","batter_runs","batter_balls"]:
                Z[c]=pd.to_numeric(X.get(c,0), errors="coerce").fillna(0)
            Z["phase_code"]=X.get("phase","").map(phase_map).fillna(1).astype(float)
            return Z[self.feature_names].values
        return X
    def predict_proba(self, X):
        return self.model.predict_proba(self._transform(X))

