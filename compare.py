"""여러 방법을 같은 조건(반복 기업단위 교차검증 + 시간분할)으로 비교하고, 모델·결과를 저장한다.

산출물(artifacts/):
  metrics_cv.csv, metrics_time.csv   방법별 성능
  oof_{h}.csv                        교차검증 예측(행별)
  models/{h}__{method}.joblib        전체 데이터로 학습한 모델
  scores_latest.csv                  최신 연도 기업별 방법별 점수
  meta.json                          특성 목록·학습 데이터 범위·최고 방법
"""
import json, os, warnings
from datetime import datetime
import joblib
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier, ExtraTreesClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
from labels import build
from features import build_features, FEATURES, FEATURES_V2
from model import make_labels

warnings.filterwarnings("ignore")
OUT = "artifacts"
os.makedirs(f"{OUT}/models", exist_ok=True)
REPEATS, FOLDS = 5, 5
TIME_CUT = {"3y": 2020, "1y": 2021, "6m": 2022}
LEARNED_FOR_ENS = ["LightGBM", "XGBoost", "RandomForest", "Logit"]


def imp():
    return SimpleImputer(strategy="median", add_indicator=True)


def learners(pos_weight):
    return {
        "Logit": make_pipeline(imp(), StandardScaler(), LogisticRegression(C=0.1, class_weight="balanced", max_iter=3000)),
        "HistGB": HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=30,
                                                 l2_regularization=1.0, class_weight="balanced", random_state=0),
        "RandomForest": make_pipeline(imp(), RandomForestClassifier(n_estimators=500, min_samples_leaf=5, max_features=0.3,
                                                                    class_weight="balanced_subsample", n_jobs=-1, random_state=0)),
        "ExtraTrees": make_pipeline(imp(), ExtraTreesClassifier(n_estimators=500, min_samples_leaf=5, max_features=0.4,
                                                                class_weight="balanced_subsample", n_jobs=-1, random_state=0)),
        "LightGBM": LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=7, min_child_samples=20,
                                   subsample=0.8, subsample_freq=1, colsample_bytree=0.7, reg_lambda=1.0,
                                   scale_pos_weight=pos_weight, verbose=-1, random_state=0),
        "XGBoost": XGBClassifier(n_estimators=300, learning_rate=0.03, max_depth=3, min_child_weight=3, subsample=0.8,
                                 colsample_bytree=0.7, reg_lambda=1.0, scale_pos_weight=pos_weight,
                                 eval_metric="logloss", n_jobs=4, random_state=0),
    }


def scorecard(d):
    """전문가 점수표(학습 없음): 나이·후계 지분·후계자 경영참여·최근 지분 이동·증여."""
    a = d.owner_age
    s = np.select([a >= 80, a >= 70, a >= 65], [3, 2, 1], 0).astype(float)
    s += np.select([d.heir_to_owner >= 1, d.heir_to_owner >= 0.5], [2, 1], 0)
    s += np.where(d.heir_is_ceo > 0, 2, np.where(d.heir_registered > 0, 1, 0))
    s += ((d.heir_stake_chg1 > 0.5) | (d.owner_stake_chg1 < -0.5)).astype(int)
    s += (d.n_gift > 0).astype(int)
    return s + 1e-3 * d.family_stake.fillna(0)  # 동점 정리


def metrics(y, p):
    o = np.argsort(-p)
    return dict(AUC=roc_auc_score(y, p), AP=average_precision_score(y, p),
                P_at_50=y[o[:50]].mean(), P_at_100=y[o[:100]].mean(), Recall_at_100=y[o[:100]].sum() / y.sum())


def group_folds(groups, seed):
    u = np.unique(groups)
    rng = np.random.RandomState(seed)
    fold_of = dict(zip(u, rng.permutation(len(u)) % FOLDS))
    f = np.array([fold_of[g] for g in groups])
    return [(np.where(f != k)[0], np.where(f == k)[0]) for k in range(FOLDS)]


def run_horizon(h, lab, hazard_src):
    yc = "y" + h
    d = lab[lab["valid" + h]].reset_index(drop=True)
    y, g = d[yc].values, d.corp_code.values
    pw = (1 - y.mean()) / y.mean()
    rows, oof_keep = [], {}
    specs = [(n, m, FEATURES) for n, m in learners(pw).items()] + \
            [("LightGBM+v2", learners(pw)["LightGBM"], FEATURES_V2), ("XGBoost+v2", learners(pw)["XGBoost"], FEATURES_V2),
             ("RandomForest+v2", learners(pw)["RandomForest"], FEATURES_V2), ("Logit+v2", learners(pw)["Logit"], FEATURES_V2)]
    for rep in range(REPEATS):
        folds = group_folds(g, rep)
        preds = {}
        for name, m, feats in specs:
            p = np.zeros(len(y))
            for tr, te in folds:
                p[te] = clone(m).fit(d.loc[tr, feats].values, y[tr]).predict_proba(d.loc[te, feats].values)[:, 1]
            preds[name] = p
        if h != "1y":  # 해저드: 1년 라벨로 더 많은 행을 학습해 순위 산출
            hz = hazard_src.reset_index(drop=True)
            for tr, te in folds:
                trc = set(g[tr])
                ht = hz[hz.corp_code.isin(trc)]
                m = clone(learners((1 - ht.y1y.mean()) / ht.y1y.mean())["LightGBM"]).fit(ht[FEATURES_V2].values, ht.y1y.values)
                p1 = m.predict_proba(d.loc[te, FEATURES_V2].values)[:, 1]
                preds.setdefault("Hazard(1y→)", np.zeros(len(y)))[te] = 1 - (1 - p1) ** (3 if h == "3y" else 0.5)
        preds["Scorecard"] = scorecard(d).values
        r = {k: rankdata(v) / len(v) for k, v in preds.items()}
        preds["Ensemble"] = np.mean([r[k] for k in LEARNED_FOR_ENS], axis=0)
        preds["Ensemble+v2"] = np.mean([r[k + "+v2"] for k in LEARNED_FOR_ENS], axis=0)
        for name, p in preds.items():
            rows.append(dict(horizon=h, method=name, repeat=rep, **metrics(y, p)))
            if rep == 0:
                oof_keep[name] = p
    cv = pd.DataFrame(rows)
    pd.concat([d[["corp_code", "corp_name", "year", yc]], pd.DataFrame(oof_keep)], axis=1).to_csv(f"{OUT}/oof_{h}.csv", index=False)

    # 시간분할(과거로 학습 → 이후 연도 평가)
    tr, te = d[d.year <= TIME_CUT[h]], d[d.year > TIME_CUT[h]]
    trow = []
    if tr[yc].sum() >= 3 and te[yc].sum() >= 3:
        tp = {}
        for name, m, feats in specs:
            tp[name] = clone(m).fit(tr[feats].values, tr[yc].values).predict_proba(te[feats].values)[:, 1]
        tp["Scorecard"] = scorecard(te).values
        r = {k: rankdata(v) for k, v in tp.items()}
        tp["Ensemble"] = np.mean([r[k] for k in LEARNED_FOR_ENS], axis=0)
        tp["Ensemble+v2"] = np.mean([r[k + "+v2"] for k in LEARNED_FOR_ENS], axis=0)
        for name, p in tp.items():
            mm = metrics(te[yc].values, p)
            trow.append(dict(horizon=h, method=name, AUC=mm["AUC"], AP=mm["AP"], n_test=len(te), pos=int(te[yc].sum())))
    return d, specs, cv, pd.DataFrame(trow)


if __name__ == "__main__":
    h_, e_, c_, o_, ev = build()
    f = build_features(h_, e_, c_, o_)
    lab = make_labels(f, ev, o_)
    hazard_src = lab[lab.valid1y]
    latest = f.sort_values("year").drop_duplicates("corp_code", keep="last")
    latest = latest[latest.year >= 2024]
    last_ev = latest.corp_code.map(ev.groupby("corp_code").date.max())
    latest = latest[~(last_ev > latest.public_date - pd.DateOffset(years=5))].reset_index(drop=True)

    all_cv, all_t, meta, scores = [], [], {}, latest[["corp_code", "corp_name", "stock_code", "year"]].copy()
    for h in ["3y", "1y", "6m"]:
        d, specs, cv, tm = run_horizon(h, lab, hazard_src)
        all_cv.append(cv); all_t.append(tm)
        summ = cv.groupby("method")[["AUC", "AP", "P_at_50", "P_at_100"]].mean().sort_values("AP", ascending=False)
        print(f"\n=== {h}  n={len(d)} 양성={int(d['y'+h].sum())}\n", summ.round(3).to_string())
        if len(tm):
            print(tm.set_index("method")[["AUC", "AP"]].round(3).T.to_string())
        # 전체 데이터로 최종 학습·저장, 최신 기업 점수
        y = d["y" + h].values
        ranks = {}
        for name, m, feats in specs:
            fm = clone(m).fit(d[feats].values, y)
            joblib.dump(dict(model=fm, features=feats, horizon=h, trained_rows=len(d), positives=int(y.sum()),
                             trained_at=datetime.now().isoformat(timespec="seconds")),
                        f"{OUT}/models/{h}__{name.replace('+', '_')}.joblib")
            p = fm.predict_proba(latest[feats].values)[:, 1]
            scores[f"{h}__{name}"] = p
            ranks[name] = rankdata(p) / len(p)
        scores[f"{h}__Scorecard"] = scorecard(latest).values
        scores[f"{h}__Ensemble"] = np.mean([ranks[k] for k in LEARNED_FOR_ENS], axis=0)
        scores[f"{h}__Ensemble+v2"] = np.mean([ranks[k + "+v2"] for k in LEARNED_FOR_ENS], axis=0)
        meta[h] = dict(rows=len(d), positives=int(y.sum()), years=[int(d.year.min()), int(d.year.max())],
                       best_by_cv_AP=summ.index[0], cv_mean=summ.iloc[0].round(4).to_dict())
    pd.concat(all_cv).to_csv(f"{OUT}/metrics_cv_by_repeat.csv", index=False)
    cvm = pd.concat(all_cv).groupby(["horizon", "method"])[["AUC", "AP", "P_at_50", "P_at_100", "Recall_at_100"]].agg(["mean", "std"])
    cvm.columns = [f"{a}_{b}" for a, b in cvm.columns]
    cvm.reset_index().to_csv(f"{OUT}/metrics_cv.csv", index=False)
    pd.concat(all_t).to_csv(f"{OUT}/metrics_time.csv", index=False)
    scores.to_csv(f"{OUT}/scores_latest.csv", index=False)
    pd.to_pickle(dict(lab=lab, latest=latest, ev=ev, f=f), f"{OUT}/dataset.pkl")
    meta.update(features_v1=FEATURES, features_v2=FEATURES_V2, folds=FOLDS, repeats=REPEATS, time_cut=TIME_CUT,
                created=datetime.now().isoformat(timespec="seconds"))
    json.dump(meta, open(f"{OUT}/meta.json", "w"), ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in meta.items() if k in ["3y", "1y", "6m"]}, ensure_ascii=False, indent=1))
