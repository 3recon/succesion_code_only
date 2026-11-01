"""최종 모델 묶음 저장 → 재로딩 검증 → 결과 엑셀 생성.  (compare.py 실행 후)"""
import json
import joblib
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from ensemble import EnsembleBundle
from compare import scorecard

A = "artifacts"
ds = pd.read_pickle(f"{A}/dataset.pkl")
lab, L, ev = ds["lab"], ds["latest"].copy(), ds["ev"]
meta = json.load(open(f"{A}/meta.json"))


def bundle(h, comps, file):
    d = lab[lab["valid" + h]]
    models, feats = {}, None
    for c in comps:
        obj = joblib.load(f"{A}/models/{h}__{c}.joblib")
        models[c], feats = obj["model"], obj["features"]
    ref = {c: m.predict_proba(d[feats].values)[:, 1] for c, m in models.items()}
    b = EnsembleBundle(models, feats, h, ref, dict(trained_rows=len(d), positives=int(d["y" + h].sum()),
                                                   years=meta[h]["years"], components=comps))
    b.save(f"{A}/{file}")
    return b


b3 = bundle("3y", ["LightGBM", "XGBoost", "RandomForest", "Logit"], "final_3y_ensemble.joblib")
b1 = bundle("1y", ["RandomForest"], "final_1y_randomforest.joblib")

# 재로딩 검증: 저장 파일로 다시 계산한 점수 = 메모리 점수
for b, f in [(b3, "final_3y_ensemble.joblib"), (b1, "final_1y_randomforest.joblib")]:
    assert np.allclose(EnsembleBundle.load(f"{A}/{f}").score(L), b.score(L)), f
L["s3y"], L["s1y"], L["scorecard"] = b3.score(L), b1.score(L), scorecard(L).round(0)
L[["corp_code", "corp_name", "stock_code", "year", "s3y", "s1y", "scorecard"]].to_csv(f"{A}/final_scores_latest.csv", index=False)

# 단기 트리거
L["T_지분이전"] = (L.owner_stake_chg1 < -0.5) & (L.heir_stake_chg1 > 0.5)
L["T_증여상속"] = L.n_gift > 0
L["T_지분역전"] = L.heir_stake >= L.owner_stake
L["T_80세이상"] = L.owner_age >= 80
L["T_후계대표"] = L.heir_is_ceo > 0
T = ["T_지분이전", "T_증여상속", "T_지분역전", "T_80세이상", "T_후계대표"]
L["트리거수"] = L[T].sum(axis=1)
action = L.T_지분이전 | L.T_증여상속 | L.T_지분역전

cols = {"corp_name": "기업명", "stock_code": "종목코드", "year": "기준연도", "owner": "최대주주", "owner_age": "최대주주 나이",
        "owner_stake": "최대주주 지분(%)", "heir_stake": "후계 지분(%)", "heir_stake_chg1": "후계 지분 1년 변화(%p)",
        "heir_exec_n": "후계 임원 수", "s3y": "3년 점수(앙상블)", "s1y": "1년 점수(RF)", "scorecard": "점수표(0~9)"}
out = L.assign(stock_code=L.stock_code.str.zfill(6), owner_age=L.owner_age.round(0))
s1 = out.sort_values("s3y", ascending=False).head(150)[list(cols) + T].rename(columns=cols)
s1.insert(0, "순위", range(1, len(s1) + 1))
short = out[(out.s3y >= 0.7) & (((out["트리거수"] >= 2) & action) | (out.s1y >= 0.95))]
short = short.sort_values(["s1y", "트리거수"], ascending=False)
s2 = short[list(cols) + ["트리거수"] + T].rename(columns=cols)
s2.insert(0, "순위", range(1, len(s2) + 1))

s3 = ev.assign(stock_code=ev.stock_code.str.zfill(6), date=ev.date.dt.date)[
    ["corp_name", "stock_code", "event", "date", "from_", "to", "rel_before", "cause"]].sort_values("date", ascending=False)
s3.columns = ["기업명", "종목코드", "유형", "발생일(근사)", "이전 최대주주", "승계자", "승계자 직전 관계", "변동 사유"]

cv, tm = pd.read_csv(f"{A}/metrics_cv.csv"), pd.read_csv(f"{A}/metrics_time.csv")
cmp = cv.merge(tm[["horizon", "method", "AUC", "AP"]].rename(columns={"AUC": "시간분할 AUC", "AP": "시간분할 AP"}),
               on=["horizon", "method"], how="left")
cmp = cmp[["horizon", "method", "AUC_mean", "AP_mean", "AP_std", "P_at_50_mean", "P_at_100_mean", "시간분할 AUC", "시간분할 AP"]]
cmp.columns = ["기간", "방법", "AUC", "AP", "AP 표준편차", "상위50 적중률", "상위100 적중률", "시간분할 AUC", "시간분할 AP"]
cmp["기간"] = pd.Categorical(cmp["기간"], ["3y", "1y", "6m"])
cmp = cmp.sort_values(["기간", "AP"], ascending=[True, False]).round(3)

m3, m1 = cmp[(cmp.기간 == "3y") & (cmp.방법 == "Ensemble")].iloc[0], cmp[(cmp.기간 == "1y") & (cmp.방법 == "RandomForest")].iloc[0]
old3 = cmp[(cmp.기간 == "3y") & (cmp.방법 == "HistGB")].iloc[0]
notes = [
    ["데이터", "OpenDART 사업보고서: 최대주주현황, 최대주주변동현황, 임원현황 (2015–2025, 1,833개사)"],
    ["승계 정의", "① 지분승계: 최대주주(개인)가 직전 연도 특수관계인 명단의 가족으로 변경  ② 경영승계: 최대주주 자녀·손자녀가 처음 대표이사 취임 → 과거 72건"],
    ["비교한 방법", "로지스틱, HistGB, 랜덤포레스트, ExtraTrees, LightGBM, XGBoost, 해저드(1년→3년), 전문가 점수표, 앙상블 × 특성 v1/v2 (5겹 기업단위 교차검증 5회 반복 + 시간분할)"],
    ["3년 최종 모델", f"앙상블(LightGBM·XGBoost·랜덤포레스트·로지스틱 백분위 평균): AUC {m3.AUC}, AP {m3.AP}, 상위50 적중률 {m3['상위50 적중률']:.0%}, 시간분할 AUC {m3['시간분할 AUC']} (이전 HistGB: AP {old3.AP}, 상위50 {old3['상위50 적중률']:.0%})"],
    ["단기 최종 모델", f"1년 랜덤포레스트: AUC {m1.AUC}, AP {m1.AP}, 상위50 적중률 {m1['상위50 적중률']:.0%}. 6개월은 과거 양성 19건뿐이라 모든 방법이 약함 → 1년 점수 + 트리거로 대체"],
    ["효과 없던 시도", "보강 특성(v2)은 교차검증에서 개선 없음, 해저드 방식·점수표는 3년에서 앙상블보다 낮음"],
    ["점수 해석", "0~1 백분위 점수(학습 데이터 대비). 1년 점수 상위 5% 구간은 교차검증에서 1년 내 실제 승계 비율 약 15% (전체 평균 2.2%의 약 7배)"],
    ["6개월 주의 조건", "3년 점수 ≥ 0.7 이면서 (1년 점수 ≥ 0.95 또는 트리거 2개 이상 + 지분이전·증여상속·지분역전 중 1개)"],
    ["저장된 모델", "artifacts/final_3y_ensemble.joblib, final_1y_randomforest.joblib (EnsembleBundle.load(경로).score(데이터)) + 비교한 모든 모델 models/*.joblib"],
    ["한계", "후계 지분은 자녀 표기·동성 특수관계인 기준 추정, 최대주주 나이 약 22% 결측. 6개월 정밀 탐지는 수시공시(대량보유·임원 소유보고) 추가 필요"],
]

fn = "가업승계_탐지결과_v2.xlsx"
with pd.ExcelWriter(fn, engine="openpyxl") as w:
    pd.DataFrame(notes, columns=["항목", "내용"]).to_excel(w, sheet_name="설명", index=False)
    cmp.to_excel(w, sheet_name="모델 비교", index=False)
    s1.to_excel(w, sheet_name="3년 후보 Top150", index=False)
    s2.to_excel(w, sheet_name="6개월 주의", index=False)
    s3.to_excel(w, sheet_name="과거 승계 이벤트", index=False)

wb = load_workbook(fn)
best = PatternFill("solid", fgColor="E2EFDA")
for ws in wb.worksheets:
    for row in ws.iter_rows():
        for c in row:
            c.font = Font(name="Arial", size=10, bold=c.row == 1, color="FFFFFF" if c.row == 1 else "000000")
            if c.row == 1:
                c.fill = PatternFill("solid", fgColor="1F3864")
                c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            if isinstance(c.value, bool):
                c.value = "●" if c.value else ""
                c.alignment = Alignment(horizontal="center")
    ws.freeze_panes = "A2" if ws.title in ("설명", "모델 비교") else "C2"
    for i, col in enumerate(ws.columns, 1):
        width = max(len(str(c.value or "")) for c in col[:60])
        ws.column_dimensions[get_column_letter(i)].width = min(max(width * 1.6, 8), 18)
    ws.auto_filter.ref = ws.dimensions
    for row in ws.iter_rows(min_row=2):
        for c in row:
            if isinstance(c.value, float):
                c.number_format = "0.000" if ws.title == "모델 비교" else "0.00"
ws = wb["모델 비교"]
for row in ws.iter_rows(min_row=2):
    if (row[0].value, row[1].value) in [("3y", "Ensemble"), ("1y", "RandomForest")]:
        for c in row:
            c.fill = best
            c.font = Font(name="Arial", size=10, bold=True)
ws = wb["설명"]
ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 16, 120
for row in ws.iter_rows(min_row=2):
    row[1].alignment = Alignment(wrap_text=True, vertical="top")
wb.save(fn)
print("3y top150", len(s1), "short", len(s2))
print(s2.head(15)[["기업명", "최대주주 나이", "3년 점수(앙상블)", "1년 점수(RF)", "트리거수"]].to_string(index=False))
