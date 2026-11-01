"""승계 이벤트 라벨링.

이벤트 정의
  A. 지분승계: 최대주주(개인)가 다른 개인으로 바뀌었고, 새 최대주주가 직전 연도
     특수관계인 명단에 가족(자녀·배우자·친인척 등, 또는 같은 성의 특수관계인)으로 있었던 경우
  B. 경영승계: 최대주주의 자녀·손자녀가 처음으로 대표이사에 오른 경우
날짜: A는 최대주주변동현황의 변동일(없으면 결산일), B는 결산일(연 단위 근사)
"""
import pandas as pd
from common import load_holders, load_execs, load_changes, FAMILY


def owners(h):
    """기업·연도별 최대주주(본인) 1명."""
    self_rows = h[h.rel == "self"].sort_values("stake", ascending=False)
    own = self_rows.drop_duplicates(["corp_code", "year"])
    # 본인 표기가 없는 기업은 지분 1위
    miss = h[~h.set_index(["corp_code", "year"]).index.isin(own.set_index(["corp_code", "year"]).index)]
    own2 = miss.sort_values("stake", ascending=False).drop_duplicates(["corp_code", "year"])
    o = pd.concat([own, own2])[["corp_code", "corp_name", "stock_code", "year", "stlm_dt", "public_date",
                                 "name", "person", "stake"]]
    return o.rename(columns={"name": "owner", "person": "owner_is_person", "stake": "owner_stake"})


def ownership_events(h, o, c):
    o = o.sort_values(["corp_code", "year"])
    prev = o.groupby("corp_code").shift(1)
    o = o.assign(prev_owner=prev.owner, prev_person=prev.owner_is_person, prev_year=prev.year)
    cand = o[(o.prev_year == o.year - 1) & (o.owner != o.prev_owner) & o.owner_is_person & (o.prev_person == True)]
    ev = []
    for r in cand.itertuples():
        before = h[(h.corp_code == r.corp_code) & (h.year == r.year - 1)]
        m = before[before.name == r.owner]
        if m.empty:
            continue
        rel = m.rel.iloc[0]
        same_surname = r.owner[0] == r.prev_owner[0]
        if rel in FAMILY or (rel in {"other", "unknown"} and same_surname):
            cc = c[(c.corp_code == r.corp_code) & (c.name == r.owner) & c.date.notna()
                   & (c.year.isin([r.year, r.year + 1]))]
            cc = cc[cc.date > pd.Timestamp(f"{r.year - 1}-12-31")]
            date = cc.date.min() if len(cc) else pd.Timestamp(r.stlm_dt)
            cause = cc.sort_values("date").cause.iloc[0] if len(cc) else ""
            ev.append(dict(corp_code=r.corp_code, corp_name=r.corp_name, stock_code=r.stock_code, year=r.year,
                           event="지분승계", from_=r.prev_owner, to=r.owner, rel_before=rel,
                           date=date, cause=cause))
    return pd.DataFrame(ev)


def management_events(e, o):
    kid_ceo = e[e.rel.isin(["child", "grand"]) & e.is_ceo]
    first = kid_ceo.sort_values("year").drop_duplicates("corp_code")
    span = o.groupby("corp_code").year.min()
    first = first[first.year > first.corp_code.map(span)]  # 관측 첫해에 이미 대표면 시점 불명 → 제외
    first = first.merge(o[["corp_code", "year", "owner", "stlm_dt"]], on=["corp_code", "year"], how="left")
    return pd.DataFrame(dict(corp_code=first.corp_code, corp_name=first.corp_name, stock_code=first.stock_code,
                             year=first.year, event="경영승계", from_=first.owner, to=first.name,
                             rel_before=first.rel, date=pd.to_datetime(first.stlm_dt), cause="자녀 대표이사 취임"))


def build():
    h, e, c = load_holders(), load_execs(), load_changes()
    o = owners(h)
    ev = pd.concat([ownership_events(h, o, c), management_events(e, o)], ignore_index=True)
    return h, e, c, o, ev.sort_values(["date"])


if __name__ == "__main__":
    h, e, c, o, ev = build()
    print(ev.event.value_counts(), ev.groupby([ev.event, ev.date.dt.year]).size().unstack(0))
    print(ev.rel_before.value_counts())
    print(ev.sample(min(25, len(ev)), random_state=1)[["corp_name", "year", "event", "from_", "to", "rel_before", "date", "cause"]].to_string())
    ev.to_csv("events.csv", index=False)
