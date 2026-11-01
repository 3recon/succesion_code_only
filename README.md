# 가업승계 탐지 (OpenDART)

실행 결과 정리: **[RESULTS.md](RESULTS.md)**

원천 데이터(OpenDART 수집 CSV)와 개인정보가 담긴 산출물(dataset.pkl, 엑셀)은 포함하지 않습니다. 실행하려면 OpenDART API로 직접 수집해 data/ 에 두세요.

## 실행
data/ 에 holders.csv, changes.csv, executives.csv(탭 구분)를 두고:

    pip install pandas scikit-learn lightgbm xgboost openpyxl joblib
    python compare.py   # 라벨링 → 특성 → 13개 방법 × 3개 기간 비교 → artifacts/ 저장 (약 8분)
    python export.py    # 최종 모델 묶음 저장·재로딩 검증 → 가업승계_탐지결과_v2.xlsx
    python make_results_md.py  # RESULTS.md 생성

## 저장된 결과 (artifacts/)
| 파일 | 내용 |
|---|---|
| final_3y_ensemble.joblib | 3년 최종 모델 (LightGBM·XGBoost·RF·로지스틱 앙상블) |
| final_1y_randomforest.joblib | 단기(1년) 최종 모델 |
| models/*.joblib | 비교한 모든 모델 (전체 데이터 학습본) |
| metrics_cv.csv / metrics_time.csv | 방법별 성능 (교차검증 평균·표준편차 / 시간분할) |
| metrics_cv_by_repeat.csv | 반복별 원자료 |
| oof_*.csv | 교차검증 예측값 (행별) |
| scores_latest.csv, final_scores_latest.csv | 최신 연도 기업별 점수 |
| meta.json | 특성 목록·학습 데이터 범위·설정 (dataset.pkl은 원천 데이터라 제외) |

## 저장된 모델로 점수 내기
    from ensemble import EnsembleBundle
    b = EnsembleBundle.load("artifacts/final_3y_ensemble.joblib")
    score = b.score(df)   # df: features.build_features() 결과, b.features 열 필요

## 파일
common.py 로딩·관계 정규화 / labels.py 승계 이벤트 / features.py 특성 / model.py 라벨(기간별) /
compare.py 방법 비교 / ensemble.py 모델 묶음 / export.py 엑셀
