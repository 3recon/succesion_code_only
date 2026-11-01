"""최종 모델 묶음(앙상블) — 저장/불러오기/점수 계산.

점수 = 구성 모델별로 '학습 데이터 예측 분포 대비 백분위'를 구해 평균 (0~1, 높을수록 승계 가능성 큼).
새 데이터 한 건만 넣어도 같은 기준으로 점수가 나온다.
"""
import joblib
import numpy as np


class EnsembleBundle:
    def __init__(self, models, features, horizon, ref_preds, info):
        self.models, self.features, self.horizon, self.info = models, features, horizon, info
        self.ref = {k: np.sort(v) for k, v in ref_preds.items()}

    def component_scores(self, df):
        X = df[self.features].values
        return {k: m.predict_proba(X)[:, 1] for k, m in self.models.items()}

    def score(self, df):
        out = []
        for k, p in self.component_scores(df).items():
            out.append(np.searchsorted(self.ref[k], p, side="right") / len(self.ref[k]))
        return np.mean(out, axis=0)

    def save(self, path):
        joblib.dump(self, path)

    @staticmethod
    def load(path):
        return joblib.load(path)
