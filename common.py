"""공통 로딩·정규화 함수 (OpenDART 최대주주현황/변동현황/임원현황)."""
import re
import pandas as pd
import numpy as np

DATA = "data"

# ---------- 관계(relate) 정규화 ----------
SELF = re.compile(r"^(본인|최대주주|최대주주본인|최대주주\(본인\)|대주주|최대주주인본인)$")
CHILD = re.compile(r"(^|최대주주의?|본인의?|특수관계\(|최대주주본인의)(자|자녀|子|子女|녀|장남|차남|삼남|장녀|차녀|아들|딸|직계비속|자부|사위|며느리)\)?$")
GRAND = re.compile(r"^(최대주주의?)?(손|손자|손녀|孫|손주)$")
SPOUSE = re.compile(r"^(최대주주의?)?(배우자|처|부인|남편|妻)$")
PARENT = re.compile(r"^(최대주주의?)?(부|모|부친|모친|父|母)$")
SIBLING = re.compile(r"^(최대주주의?)?(형제|제|매|형|동생|누나|누이|오빠|언니|자매|남매|형제자매)$")
RELATIVE = re.compile(r"(친인척|친인천|백부|^축$|친족|혈족|조카|사촌|촌|숙부|숙모|삼촌|형수|제수|인척|고모|이모|외숙|질녀|^질$|처남|처제|매형|매제|종형제|가족|친척|당질|방계|제의자)")
FOUND = re.compile(r"(재단|학교법인|비영리|장학)")
CORP = re.compile(r"(계열|관계회사|관계사|관계기업|법인|회사|자사주|자기주식|피지배|지배회사|출자)")
EXEC = re.compile(r"(임원|이사|감사|회장|대표|임직원)")

FAMILY = {"child", "grand", "spouse", "parent", "sibling", "relative"}


def norm_rel(s: str) -> str:
    s = re.sub(r"\s", "", str(s or ""))
    if not s or s in {"-", "nan", "〃", "＂", "˝"}:
        return "unknown"
    for name, pat in [("self", SELF), ("child", CHILD), ("grand", GRAND), ("spouse", SPOUSE),
                      ("parent", PARENT), ("sibling", SIBLING)]:
        if pat.search(s):
            return name
    if RELATIVE.search(s):
        return "relative"
    if FOUND.search(s):
        return "foundation"
    if CORP.search(s) and not re.search(r"임원", s):
        return "corp"
    if EXEC.search(s):
        return "exec"
    return "other"


PERSON = re.compile(r"^[가-힣]{2,4}$")
CORPWORD = re.compile(r"(주식|㈜|\(주\)|홀딩스|재단|은행|공사|투자|펀드|조합|기금|연금|보험|증권|산업|전자|그룹)")


def is_person(nm: str) -> bool:
    nm = re.sub(r"\s", "", str(nm or ""))
    return bool(PERSON.match(nm)) and not CORPWORD.search(nm)


def clean_name(nm) -> str:
    return re.sub(r"[\s\(\)（）]", "", str(nm or ""))


def to_num(x):
    return pd.to_numeric(pd.Series(x).astype(str).str.replace(r"[%,\s]", "", regex=True)
                         .replace({"-": "0", "": "0", "nan": np.nan}), errors="coerce").values


def read_tsv(path):
    """셀 안 줄바꿈·짝 안 맞는 따옴표에 견디는 TSV 리더: 열 수가 찰 때까지 줄을 이어 붙인다."""
    start = re.compile(r"^\d{1,8}\t[^\t]*\t[^\t]*\t\d{4}\t")  # corp_code, stock_code, corp_name, bsns_year
    with open(path, encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        n, rows, recs, buf = len(header), [], [], None
        for line in f:
            line = line.rstrip("\n")
            if start.match(line) or buf is None:
                if buf is not None:
                    recs.append(buf)
                buf = line
            else:
                buf += line  # 셀 안 줄바꿈 → 이어 붙임
        if buf is not None:
            recs.append(buf)
    for r in recs:
        parts = r.split("\t")
        if len(parts) < n:
            parts += [""] * (n - len(parts))
        rows.append([p.strip().strip('"').strip() for p in parts[:n - 1]] +
                    [" ".join(parts[n - 1:]).strip().strip('"')])
    d = pd.DataFrame(rows, columns=header).replace({"": np.nan})
    return d


def load(name):
    d = read_tsv(f"{DATA}/{name}.csv")
    d = d[d.bsns_year.str.fullmatch(r"\d{4}", na=False)].drop_duplicates()
    d["year"] = d.bsns_year.astype(int)
    return d


def load_holders():
    h = load("holders")
    h = h[h.nm.fillna("").str.strip() != "계"].copy()
    # 보통주(의결권 있는 주식)만 사용
    sk = h.stock_knd.fillna("").str.replace(r"\s", "", regex=True)
    h = h[sk.str.contains("보통") | (sk == "") | sk.str.contains("의결권있는")].copy()
    h["rel"] = h.relate.map(norm_rel)
    h["name"] = h.nm.map(clean_name)
    h["person"] = h.name.map(is_person)
    h["stake"] = to_num(h.trmend_rt)
    h["stake_bgn"] = to_num(h.bsis_rt)
    # 같은 사람이 여러 행(보통주 중복 표기)일 경우 합산
    h = (h.groupby(["corp_code", "corp_name", "stock_code", "year", "public_date", "stlm_dt", "name"], as_index=False)
           .agg(rel=("rel", "first"), person=("person", "first"), stake=("stake", "sum"), stake_bgn=("stake_bgn", "sum")))
    return h


def load_execs():
    e = load("executives")
    e["rel"] = e.relate.map(norm_rel)
    e["name"] = e.nm.map(clean_name)
    by = e.birth_ym.fillna("").str.extract(r"(\d{4})")[0]
    e["birth_year"] = pd.to_numeric(by, errors="coerce")
    e.loc[(e.birth_year < 1910) | (e.birth_year > 2010), "birth_year"] = np.nan
    pos = e.ofcps.fillna("").str.replace(r"\s", "", regex=True)
    e["is_ceo"] = pos.str.contains("대표")
    e["is_chair"] = pos.str.contains("회장")
    e["registered"] = e.rgist_exctv_at.fillna("").str.contains("^등기|사내이사|사외이사", regex=True) & \
        ~e.rgist_exctv_at.fillna("").str.contains("미등기")
    return e


def load_changes():
    c = load("changes")
    c = c[c.holder.fillna("-").str.strip() != "-"].copy()
    c["name"] = c.holder.map(clean_name)
    s = c.change_on.fillna("").str.replace(r"\s", "", regex=True)
    m = s.str.extract(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})")
    c["date"] = pd.to_datetime(m[0] + "-" + m[1].str.zfill(2) + "-" + m[2].str.zfill(2), errors="coerce")
    c["cause"] = c.change_cause.fillna("").str.replace(r"\s", "", regex=True)
    c["stake"] = to_num(c.qota_rt)
    return c
