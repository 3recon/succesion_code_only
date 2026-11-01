"""기업×연도 특성 생성 (기준시점 = 해당 연도 사업보고서 공시일)."""
import numpy as np
import pandas as pd
from common import FAMILY

GIFT = r"증여|수증|증유|상속"
OTC = r"장외|시간외|블록"
PLEDGE = r"담보|질권"
RESTRUCT = r"합병|분할|현물출자|공개매수|교환"


def build_features(h, e, c, o):
    o = o[o.owner_is_person].copy()
    key = ["corp_code", "year"]
    f = o[key + ["corp_name", "stock_code", "public_date", "stlm_dt", "owner", "owner_stake"]].copy()

    # ---- 지분 구조 ----
    hh = h.merge(o[key + ["owner"]], on=key)
    hh["kin_surname"] = hh.person & (hh.name != hh.owner) & (hh.name.str[0] == hh.owner.str[0]) & \
        hh.rel.isin(["other", "unknown", "relative", "exec"])
    agg = lambda mask, col="stake", fn="sum": hh[mask].groupby(key)[col].agg(fn)
    f = f.set_index(key)
    f["child_stake"] = agg(hh.rel.isin(["child", "grand"]))
    f["child_n"] = agg(hh.rel.isin(["child", "grand"]) & (hh.stake > 0), fn="count")
    f["child_max_stake"] = agg(hh.rel.isin(["child", "grand"]), fn="max")
    f["spouse_stake"] = agg(hh.rel == "spouse")
    f["relative_stake"] = agg(hh.rel.isin(["relative", "sibling", "parent"]))
    f["kin_surname_stake"] = agg(hh.kin_surname)
    f["kin_surname_max"] = agg(hh.kin_surname, fn="max")
    f["foundation_stake"] = agg(hh.rel == "foundation")
    f["affil_corp_stake"] = agg(hh.rel == "corp")
    f["n_holders"] = hh.groupby(key).size()
    f = f.fillna({k: 0 for k in ["child_stake", "child_n", "child_max_stake", "spouse_stake", "relative_stake",
                                 "kin_surname_stake", "kin_surname_max", "foundation_stake", "affil_corp_stake"]})
    f["heir_stake"] = f[["child_stake", "kin_surname_stake"]].max(axis=1)
    f["family_stake"] = f.owner_stake + f.child_stake + f.spouse_stake + f.relative_stake + f.kin_surname_stake
    f["heir_to_owner"] = f.heir_stake / (f.owner_stake + 0.5)
    f["has_child_listed"] = (f.child_n > 0).astype(int)
    f = f.reset_index()

    # ---- 임원(오너 나이·후계자 경영 참여) ----
    em = e.merge(o[key + ["owner"]], on=key)
    owner_birth = (e.groupby(["corp_code", "name"]).birth_year.median().rename("owner_birth"))
    f = f.merge(owner_birth, left_on=["corp_code", "owner"], right_index=True, how="left")
    f["owner_age"] = f.year - f.owner_birth
    oe = em[em.name == em.owner].groupby(key).agg(owner_is_exec=("name", "size"), owner_is_ceo=("is_ceo", "max"),
                                                    owner_is_chair=("is_chair", "max"), owner_registered=("registered", "max"))
    f = f.merge(oe, on=key, how="left")
    # 후계자 후보: 자녀 표기 임원, 또는 오너와 성이 같고 20살 이상 어린 임원
    em = em.merge(f[key + ["owner_birth"]], on=key, how="left")
    em["heir"] = (em.name != em.owner) & (em.rel.isin(["child", "grand"]) |
                  ((em.name.str[0] == em.owner.str[0]) & (em.birth_year - em.owner_birth >= 20)))
    he = em[em.heir].groupby(key).agg(heir_exec_n=("name", "nunique"), heir_is_ceo=("is_ceo", "max"),
                                      heir_registered=("registered", "max"), heir_age=("birth_year", "max"))
    f = f.merge(he, on=key, how="left")
    f["heir_age"] = f.year - f.heir_age
    for col in ["owner_is_exec", "owner_is_ceo", "owner_is_chair", "owner_registered", "heir_exec_n",
                "heir_is_ceo", "heir_registered"]:
        f[col] = f[col].fillna(0).astype(float)
    f["owner_age_missing"] = f.owner_age.isna().astype(int)

    # ---- 최대주주 변동 사유(해당 연도 보고서) ----
    cc = c.copy()
    for k, pat in [("n_gift", GIFT), ("n_otc", OTC), ("n_pledge", PLEDGE), ("n_restruct", RESTRUCT)]:
        cc[k] = cc.cause.str.contains(pat, regex=True)
    cc["n_changes"] = 1
    ca = cc.groupby(key)[["n_changes", "n_gift", "n_otc", "n_pledge", "n_restruct"]].sum()
    f = f.merge(ca, on=key, how="left")
    for col in ca.columns:
        f[col] = f[col].fillna(0)

    # ---- 시계열 변화(직전·3년 전 대비) ----
    f = f.sort_values(key)
    g = f.groupby("corp_code")
    for col in ["owner_stake", "heir_stake", "family_stake", "heir_exec_n"]:
        prev = g[col].shift(1)
        f[col + "_chg1"] = np.where(g.year.shift(1) == f.year - 1, f[col] - prev, np.nan)
    for col in ["owner_stake", "heir_stake"]:
        f[col + "_chg3"] = f[col] - g[col].shift(3).where(g.year.shift(3) == f.year - 3)
    f["gift_3y"] = g.n_gift.transform(lambda s: s.rolling(3, min_periods=1).sum())
    f["owner_tenure_obs"] = f.groupby(["corp_code", "owner"]).cumcount() + 1
    f["public_date"] = pd.to_datetime(f.public_date, errors="coerce")

    # ---- v2 보강 특성 ----
    kin = hh[(hh.rel.isin(["child", "grand"]) | hh.kin_surname) & (hh.stake > 0)].groupby(key).name.nunique()
    f = f.merge(kin.rename("heir_n_people"), on=key, how="left").fillna({"heir_n_people": 0})
    f["gen_gap"] = f.owner_age - f.heir_age
    f["spouse_to_owner"] = f.spouse_stake / (f.owner_stake + 0.5)
    f["holdco_dominant"] = (f.affil_corp_stake > f.owner_stake).astype(int)
    f["owner_age_sq"] = f.owner_age ** 2
    f["age70"] = (f.owner_age >= 70).astype(float).where(f.owner_age.notna())
    f["age_x_heir"] = f.owner_age * f.heir_to_owner
    g = f.sort_values(["corp_code", "year"]).groupby("corp_code")
    f["n_changes_2y"] = g.n_changes.transform(lambda s: s.rolling(2, min_periods=1).sum())
    f["owner_stake_chg2"] = f.owner_stake - g.owner_stake.shift(2).where(g.year.shift(2) == f.year - 2)
    f["heir_stake_chg2"] = f.heir_stake - g.heir_stake.shift(2).where(g.year.shift(2) == f.year - 2)
    return f.reset_index(drop=True)


FEATURES = ["owner_stake", "owner_age", "owner_age_missing", "owner_is_exec", "owner_is_ceo", "owner_is_chair",
            "owner_registered", "child_stake", "child_n", "child_max_stake", "spouse_stake", "relative_stake",
            "kin_surname_stake", "kin_surname_max", "heir_stake", "heir_to_owner", "family_stake", "has_child_listed",
            "foundation_stake", "affil_corp_stake", "n_holders", "heir_exec_n", "heir_is_ceo", "heir_registered",
            "heir_age", "n_changes", "n_gift", "n_otc", "n_pledge", "n_restruct", "gift_3y",
            "owner_stake_chg1", "heir_stake_chg1", "family_stake_chg1", "heir_exec_n_chg1",
            "owner_stake_chg3", "heir_stake_chg3"]

FEATURES_V2 = FEATURES + ["heir_n_people", "gen_gap", "spouse_to_owner", "holdco_dominant", "owner_age_sq", "age70",
                          "age_x_heir", "n_changes_2y", "owner_stake_chg2", "heir_stake_chg2"]
