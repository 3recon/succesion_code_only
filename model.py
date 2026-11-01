"""3년·6개월 승계 예측 모델 학습/검증/최신 후보 산출."""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.inspection import permutation_importance
from labels import build
from features import build_features, FEATURES

H = {"3y": pd.DateOffset(years=3), "1y": pd.DateOffset(years=1), "6m": pd.DateOffset(months=6)}


def make_labels(f, ev, o):
    obs_end = pd.to_datetime(o.groupby("corp_code").stlm_dt.max())
    exact = ev.event.eq("지분승계") & ~ev.date.dt.strftime("%m-%d").eq("12-31")
    first = ev.groupby("corp_code").date.min()
    f = f.copy()
    f["first_event"] = f.corp_code.map(first)
    f = f[~(f.first_event <= f.public_date)]  # 이미 승계가 끝난 기업-연도는 제외
    end = f.corp_code.map(obs_end)
    for k, off in H.items():
        src = ev if k != "6m" else ev[exact]
        y = np.zeros(len(f), bool)
        for cc, P, idx in zip(f.corp_code, f.public_date, range(len(f))):
            d = src.date[src.corp_code == cc]
            y[idx] = ((d > P) & (d <= P + off)).any()
        f["y" + k] = y.astype(int)
        f["valid" + k] = f.public_date + off <= end  # 관측이 끝까지 된 행만 (중도절단 제외)
    # 6개월: 날짜 불명확한(연말 근사) 이벤트가 1년 안에 있으면 학습에서 제외
    fuzzy = ev[~exact]
    near = [((fuzzy.date[fuzzy.corp_code == cc] > P) & (fuzzy.date[fuzzy.corp_code == cc] <= P + pd.DateOffset(years=1))).any()
            for cc, P in zip(f.corp_code, f.public_date)]
    f.loc[np.array(near) & (f.y6m == 0), "valid6m"] = False
    return f


def models():
    gb = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=30,
                                        l2_regularization=1.0, class_weight="balanced", random_state=0)
    lr = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                       LogisticRegression(C=0.1, class_weight="balanced", max_iter=2000))
    return {"GBM": gb, "Logit": lr}


def prec_at(y, p, k):
    k = min(k, len(y))
    return y[np.argsort(-p)[:k]].mean()


def evaluate(d, ycol):
    X, y, g = d[FEATURES].values, d[ycol].values, d.corp_code.values
    res, oof_all = {}, {}
    for name, m in models().items():
        oof = np.zeros(len(y))
        for tr, te in GroupKFold(5).split(X, y, g):
            m.fit(X[tr], y[tr])
            oof[te] = m.predict_proba(X[te])[:, 1]
        res[name] = dict(AUC=roc_auc_score(y, oof), AP=average_precision_score(y, oof), base=y.mean(),
                         P_at_50=prec_at(y, oof, 50), P_at_100=prec_at(y, oof, 100))
        oof_all[name] = oof
    return res, oof_all


def time_split(d, ycol, cut):
    tr, te = d[d.year <= cut], d[d.year > cut]
    if tr[ycol].sum() < 3 or te[ycol].sum() < 3:
        return None
    out = {}
    for name, m in models().items():
        m.fit(tr[FEATURES].values, tr[ycol].values)
        p = m.predict_proba(te[FEATURES].values)[:, 1]
        out[name] = dict(AUC=roc_auc_score(te[ycol], p), AP=average_precision_score(te[ycol], p),
                         n_test=len(te), pos=int(te[ycol].sum()))
    return out


if __name__ == "__main__":
    h, e, c, o, ev = build()
    f = build_features(h, e, c, o)
    lab = make_labels(f, ev, o)
    report, scores, imps = [], {}, {}
    for k in H:
        d = lab[lab["valid" + k]].reset_index(drop=True)
        res, oof = evaluate(d, "y" + k)
        ts = time_split(d, "y" + k, {"3y": 2020, "1y": 2021, "6m": 2022}[k])
        print(f"\n=== {k}: n={len(d)}, 양성={d['y'+k].sum()} ({d['y'+k].mean():.1%}), 기업={d.corp_code.nunique()}")
        for n, r in res.items():
            print(f"  [기업단위 CV] {n}: " + ", ".join(f"{a}={b:.3f}" for a, b in r.items()))
        if ts:
            for n, r in ts.items():
                print(f"  [시간분할] {n}: " + ", ".join(f"{a}={b:.3f}" if isinstance(b, float) else f"{a}={b}" for a, b in r.items()))
        best = max(res, key=lambda n: res[n]["AP"])
        m = models()[best].fit(d[FEATURES].values, d["y" + k].values)
        pi = permutation_importance(m, d[FEATURES].values, d["y" + k].values, scoring="average_precision",
                                    n_repeats=5, random_state=0)
        imps[k] = pd.Series(pi.importances_mean, FEATURES).sort_values(ascending=False)
        print("  주요 변수:", imps[k].head(8).round(3).to_dict())
        # 최신 연도 기업 점수
        latest = f.sort_values("year").drop_duplicates("corp_code", keep="last")
        latest = latest[latest.year >= 2024]
        last_ev = latest.corp_code.map(ev.groupby("corp_code").date.max())
        latest = latest[~(last_ev > latest.public_date - pd.DateOffset(years=5))]  # 최근 5년 내 승계 완료 기업 제외
        scores[k] = pd.Series(m.predict_proba(latest[FEATURES].values)[:, 1], index=latest.corp_code)
        report.append(dict(horizon=k, model=best, n=len(d), pos=int(d["y" + k].sum()), **res[best],
                           **({f"time_{a}": b for a, b in ts[best].items()} if ts else {})))
    latest = f.sort_values("year").drop_duplicates("corp_code", keep="last")
    latest = latest[latest.corp_code.isin(scores["3y"].index)].copy()
    latest["p3y"] = latest.corp_code.map(scores["3y"])
    latest["p6m"] = latest.corp_code.map(scores["6m"])
    pd.to_pickle(dict(lab=lab, latest=latest, ev=ev, report=pd.DataFrame(report), imps=imps, f=f), "results.pkl")
    print(pd.DataFrame(report).round(3).to_string())
