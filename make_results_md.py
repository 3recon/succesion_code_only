"""artifacts/ 의 실행 결과를 RESULTS.md 로 정리 (개인 실명·나이 등 원천 데이터는 넣지 않음)."""
import json
import pandas as pd

A = "artifacts"
meta = json.load(open(f"{A}/meta.json"))
cv, tm = pd.read_csv(f"{A}/metrics_cv.csv"), pd.read_csv(f"{A}/metrics_time.csv")
m = cv.merge(tm[["horizon", "method", "AUC", "AP"]], on=["horizon", "method"], how="left")
S = pd.read_csv(f"{A}/final_scores_latest.csv", dtype={"stock_code": str})
S["stock_code"] = S.stock_code.str.zfill(6)


def table(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join("-" if pd.isna(v) else (f"{v:.3f}" if isinstance(v, float) else str(v)) for v in r) + " |")
    return "\n".join(out)


def comp(h):
    x = m[m.horizon == h].sort_values("AP_mean", ascending=False)
    x = x[["method", "AP_mean", "AP_std", "AUC_mean", "P_at_50_mean", "P_at_100_mean", "AUC", "AP"]]
    x.columns = ["방법", "AP", "AP 표준편차", "AUC", "상위50 적중률", "상위100 적중률", "시간분할 AUC", "시간분할 AP"]
    return table(x)


top = S.sort_values("s3y", ascending=False).head(30)[["corp_name", "stock_code", "s3y", "s1y", "scorecard"]]
top.insert(0, "순위", range(1, 31))
top["scorecard"] = top.scorecard.astype(int)
top.columns = ["순위", "기업명", "종목코드", "3년 점수", "1년 점수", "점수표(0~9)"]
short = S[(S.s3y >= 0.7) & (S.s1y >= 0.95)].sort_values("s1y", ascending=False)[["corp_name", "stock_code", "s3y", "s1y"]]
short.columns = ["기업명", "종목코드", "3년 점수", "1년 점수"]

h3, h1, h6 = meta["3y"], meta["1y"], meta["6m"]
md = f"""# 가업승계 탐지 실행 결과

OpenDART 사업보고서(최대주주현황·최대주주변동현황·임원현황, 2015–2025, 1,833개사)로 상장사의 가업승계 시점을 예측한 결과입니다.
원천 데이터와 개인 정보(실명·나이·가족관계)는 이 저장소에 포함하지 않았습니다.

## 1. 요약
- **3년 내 승계**: 앙상블(LightGBM·XGBoost·랜덤포레스트·로지스틱)이 최고. AP {h3['cv_mean']['AP']:.3f}, 상위 50개 중 {h3['cv_mean']['P_at_50']:.0%} 적중 (무작위 {h3['positives']/h3['rows']:.1%})
- **1년 내 승계**: 랜덤포레스트가 최고. AUC {h1['cv_mean']['AUC']:.3f}, 점수 상위 5%의 실제 승계 비율 약 15% (무작위 2.2%)
- **6개월 내 승계**: 과거 양성 {h6['positives']}건뿐이라 신뢰할 만한 모델 없음 → 1년 점수로 단기 후보 선별
- 가장 중요한 변수: 최대주주 나이 > 가족 총지분 > 최대주주 지분 > 후계자 지분 > 가족지분 1년 변화

## 2. 방법
**승계 이벤트(정답) 정의** — 과거 72건 (지분승계 50, 경영승계 22)
1. 지분승계: 최대주주(개인)가 직전 연도 특수관계인 명단의 가족(자녀·배우자·친인척·동성 특수관계인)으로 변경
2. 경영승계: 최대주주의 자녀·손자녀가 처음 대표이사 취임

**학습 단위**: 기업×연도, 기준시점 = 사업보고서 공시일. 라벨 = 기준시점 이후 3년 / 1년 / 6개월 안에 승계 발생 여부.
관측 기간이 끝나기 전에 잘리는 행, 이미 승계가 끝난 기업-연도는 제외.

**특성(37개, v2는 +10개)**: 최대주주 나이·지분·직위, 자녀/배우자/친인척/동성 특수관계인 지분, 후계자 임원 등재·대표 여부,
가족지분 1·3년 변화, 최대주주 변동 사유(증여·상속·장외매매·담보·합병분할) 건수 등.

**검증**
- 기업 단위 5겹 교차검증 × 5회 반복 (같은 기업이 학습·평가에 동시에 들어가지 않게)
- 시간분할: 3년 모델은 2020년까지 학습 → 2021년 이후 평가 (1년 2021, 6개월 2022 기준)

**지표**
- AP: 점수 순으로 확인해 나갈 때의 평균 적중률. 무작위 기준 = 양성 비율. 희귀 사건 비교의 주 기준
- AUC: 승계/비승계 기업 한 쌍에서 승계 기업에 더 높은 점수를 줄 확률 (0.5 = 무작위)
- 상위50 적중률: 점수 상위 50개 중 실제 승계 비율
- 시간분할 AUC/AP: 과거로 학습해 이후 연도를 예측했을 때 성능 (실전과 가장 가까움)

## 3. 방법 비교

### 3년 (학습 {h3['rows']}행, 양성 {h3['positives']}건)
{comp('3y')}

### 1년 (학습 {h1['rows']}행, 양성 {h1['positives']}건)
{comp('1y')}

### 6개월 (학습 {h6['rows']}행, 양성 {h6['positives']}건)
{comp('6m')}

방법 설명: `+v2` 보강 특성 추가, `Hazard(1y→)` 1년 모델 확률을 기간으로 환산, `Scorecard` 학습 없는 전문가 점수표,
`Ensemble` LightGBM·XGBoost·RF·로지스틱 순위 평균.

**결론**: 보강 특성(v2)·해저드·점수표는 앙상블보다 개선되지 않음. 정확도의 한계는 모델보다 양성 사례 수(3년 {h3['positives']}건)에서 옴.

## 4. 최신 연도 후보 (2025년 사업보고서 기준, {len(S)}개사)
최근 5년 안에 승계가 끝난 기업은 제외. 점수는 학습 데이터 대비 백분위(0~1).

### 3년 내 승계 후보 Top 30
{table(top)}

### 단기 후보 (3년 점수 ≥ 0.7, 1년 점수 ≥ 0.95) — {len(short)}개사
{table(short)}

## 5. 한계
- 후계자 지분은 '자녀' 표기 또는 최대주주와 성이 같은 특수관계인 기준 추정 → 친인척이 섞일 수 있음
- 최대주주 나이는 임원 명단에 있을 때만 확인 (약 22% 결측)
- 2015–2019년 데이터는 약 140개사만 있어 초기 연도 학습 데이터가 적음
- 6개월 정밀 탐지에는 수시공시(대량보유상황보고, 임원·주요주주 소유상황보고)가 필요

## 6. 재현
```
pip install pandas scikit-learn lightgbm xgboost openpyxl joblib
# data/ 에 holders.csv, changes.csv, executives.csv (OpenDART, 탭 구분) 준비
python compare.py          # 방법 비교·모델 저장 (약 8분)
python export.py           # 최종 모델 묶음·엑셀
python make_results_md.py  # 이 문서
```
"""
open("RESULTS.md", "w", encoding="utf-8").write(md)
print(len(md))
