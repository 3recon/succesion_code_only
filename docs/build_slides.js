const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const { applyTheme } = require("/root/.claude/skills/synced/f9934e83-57b4-4fef-8792-d983db6ad2d9_f492d71c-c27d-44bb-a93b-526beaf51a2e/pptx/scripts/apply_theme.js");

const HEX = {
  navy: "14245C", blue: "2F6FED", purple: "6D4BD8", ink: "1F2937", white: "FFFFFF",
  tint: "EEF3FC", tint2: "DCE6FA", lightblue: "9DB9F5", grey: "6B7280", line: "C9D3E6", asis: "F2F4F8",
};
const THEME = {
  name: "Succession Navy", headFontFace: "맑은 고딕", bodyFontFace: "맑은 고딕",
  colors: { dk1: HEX.ink, lt1: HEX.white, dk2: HEX.navy, lt2: HEX.tint, accent1: HEX.blue, accent2: HEX.navy,
            accent3: HEX.purple, accent4: HEX.lightblue, accent5: "5B7FD6", accent6: HEX.tint2,
            hlink: HEX.blue, folHlink: HEX.purple },
};

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.title = "DART 공시 기반 가업승계 기업 탐지 모델";
  const C = pres.SchemeColor;
  const W = 13.333;
  const FOOT = "DART 공시 기반 가업승계 기업 탐지 모델";

  // ---------- 레이아웃 ----------
  const header = (dark) => [
    { placeholder: { options: { name: "mid", type: "body", x: 0.5, y: 0.34, w: 2.2, h: 0.44, fontSize: 13, bold: true,
        color: C.background1, align: "center", valign: "middle", margin: 0 }, text: "중분류" } },
    { placeholder: { options: { name: "title", type: "title", x: 2.9, y: 0.26, w: 7.53, h: 0.6, fontSize: 22, bold: true,
        color: dark ? C.background1 : C.text2, align: "center", valign: "middle", margin: 0 }, text: "소분류" } },
    { placeholder: { options: { name: "major", type: "body", x: 10.63, y: 0.34, w: 2.2, h: 0.44, fontSize: 13, bold: true,
        color: dark ? C.accent4 : C.accent3, align: "right", valign: "middle", margin: 0 }, text: "대분류" } },
  ];
  pres.defineSlideMaster({
    title: "CONTENT",
    background: { color: C.background1 },
    objects: [
      ...header(false),
      { placeholder: { options: { name: "summary", type: "body", x: 0.72, y: 1.02, w: W - 1.44, h: 0.82, fontSize: 14,
          color: C.text1, align: "left", valign: "middle", margin: 0, lineSpacingMultiple: 1.15 }, text: "요약" } },
      { text: { text: FOOT, options: { x: 0.5, y: 7.05, w: 6, h: 0.3, fontSize: 10, color: HEX.grey, margin: 0 } } },
    ],
    slideNumber: { x: 12.33, y: 7.05, w: 0.5, h: 0.3, fontSize: 10, color: HEX.grey, align: "right" },
  });
  pres.defineSlideMaster({
    title: "COVER",
    background: { color: C.text2 },
    objects: [
      ...header(true),
      { placeholder: { options: { name: "summary", type: "body", x: 0.5, y: 1.02, w: W - 1.0, h: 0.82, fontSize: 14,
          color: C.accent6, align: "left", valign: "middle", margin: 0, lineSpacingMultiple: 1.15 }, text: "요약" } },
    ],
  });

  const fill = (s, mid, title, major, summary, cover = false) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: 0.34, w: 2.2, h: 0.44, rectRadius: 0.22,
      fill: { color: C.accent1 }, line: { type: "none" }, objectName: "mid_pill" });
    if (!cover) s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: 1.02, w: W - 1.0, h: 0.82, rectRadius: 0.08,
      fill: { color: C.background2 }, line: { type: "none" }, objectName: "summary_box" });
    s.addText(mid, { placeholder: "mid" });
    s.addText(title, { placeholder: "title" });
    s.addText(major, { placeholder: "major" });
    s.addText(summary, { placeholder: "summary" });
  };
  const T = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, ...o });
  const iconCircle = async (s, Comp, x, y, d, bg, fg, name) => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: bg }, line: { type: "none" }, objectName: name + "_bg" });
    const p = d * 0.25;
    s.addImage({ data: await icon(Comp, fg), x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p, objectName: name, altText: name });
  };
  const chartText = { catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt",
    titleFontFace: "+mn-lt", legendFontFace: "+mn-lt", catAxisLabelColor: HEX.grey, valAxisLabelColor: HEX.grey,
    catAxisLabelFontSize: 10, valAxisLabelFontSize: 10, dataLabelFontSize: 10, titleFontSize: 12, titleColor: HEX.navy,
    legendFontSize: 10, legendColor: HEX.ink };

  // ================= 1. 표지 =================
  pres.addSection({ title: "Ⅰ. 개요" });
  let s = pres.addSlide({ masterName: "COVER", sectionTitle: "Ⅰ. 개요" });
  fill(s, "표지 · 목적", "공시 데이터로 승계를 준비하는 기업을 미리 찾는다", "Ⅰ. 개요",
    "목적: OpenDART 사업보고서로 3년·6개월 안에 가업승계가 일어날 상장사를 조기에 탐지하는 모델의 구조, 성능, 한계를 공유하고 활용 방향을 논의한다.", true);
  T(s, "DART 공시 기반", { x: 0.5, y: 2.75, w: 7, h: 0.5, fontSize: 20, color: HEX.lightblue, bold: true });
  T(s, "가업승계 기업 탐지 모델", { x: 0.5, y: 3.25, w: 7.2, h: 0.95, fontSize: 40, color: HEX.white, bold: true });
  T(s, "최대주주 · 지분 변동 · 임원 공시로 승계 시점을 점수화", { x: 0.5, y: 4.25, w: 7, h: 0.45, fontSize: 16, color: HEX.tint2 });
  const tags = ["3년 내 탐지", "6개월 내 탐지", "1,833개 상장사"];
  tags.forEach((t, i) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5 + i * 1.95, y: 5.0, w: 1.8, h: 0.44, rectRadius: 0.22,
      fill: { color: HEX.navy }, line: { color: HEX.lightblue, width: 1 }, objectName: "tag" + i });
    T(s, t, { x: 0.5 + i * 1.95, y: 5.0, w: 1.8, h: 0.44, fontSize: 13, color: HEX.white, align: "center", valign: "middle" });
  });
  T(s, "2026. 11", { x: 0.5, y: 6.6, w: 3, h: 0.35, fontSize: 12, color: HEX.lightblue });
  // 이미지: 1세대 → 2세대 + 기업 + 탐지
  s.addShape(pres.shapes.OVAL, { x: 8.55, y: 2.45, w: 4.1, h: 4.1, fill: { color: "1D3277" }, line: { type: "none" }, objectName: "cover_ring" });
  await iconCircle(s, fa.FaBuilding, 9.9, 2.85, 1.4, HEX.white, HEX.navy, "cover_company");
  await iconCircle(s, fa.FaUserTie, 8.95, 4.6, 1.15, HEX.blue, HEX.white, "cover_owner");
  await iconCircle(s, fa.FaUserGraduate, 11.4, 4.6, 1.15, HEX.purple, HEX.white, "cover_heir");
  s.addShape(pres.shapes.LINE, { x: 10.2, y: 5.18, w: 1.1, h: 0, line: { color: HEX.white, width: 2.5, endArrowType: "triangle" }, objectName: "cover_arrow" });
  await iconCircle(s, fa.FaSearch, 10.42, 4.25, 0.62, HEX.lightblue, HEX.navy, "cover_search");
  T(s, "1세대", { x: 8.95, y: 5.8, w: 1.15, h: 0.3, fontSize: 11, color: HEX.tint2, align: "center" });
  T(s, "후계자", { x: 11.4, y: 5.8, w: 1.15, h: 0.3, fontSize: 11, color: HEX.tint2, align: "center" });
  s.addNotes("가업승계 탐지 모델 소개. 목적: 공시 데이터만으로 승계 준비 기업을 3년·6개월 단위로 미리 찾는 것.");

  // ================= 2. As-Is / To-Be =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Ⅰ. 개요" });
  fill(s, "As-Is · To-Be", "수작업 탐색을 점수 기반 조기 탐지로 바꾼다", "Ⅰ. 개요",
    "지금은 승계 대상 기업을 공시를 하나씩 열어보며 찾고, 최대주주가 바뀐 뒤에야 승계를 알게 된다. 탐지 모델은 전 상장사를 매년 자동으로 점수화해 승계 가능성이 큰 기업을 먼저 보여준다.");
  const asis = [
    [fa.FaFileAlt, "수작업 열람", "기업별 사업보고서를 직접 열어 지분·임원 확인"],
    [fa.FaHistory, "사후 인지", "최대주주 변경 공시가 나온 뒤에야 승계 파악"],
    [fa.FaUserClock, "경험 의존", "담당자 감에 의존, 우선순위 근거 부족"],
    [fa.FaExpand, "확장 한계", "대상 기업이 늘면 필요한 인력도 비례해 증가"],
  ];
  const tobe = [
    [fa.FaDatabase, "자동 수집", "OpenDART API로 전 상장사 공시를 매년 갱신"],
    [fa.FaRegClock, "사전 탐지", "3년·1년 안 승계 가능성을 0~1 점수로 예측"],
    [fa.FaChartBar, "근거 제시", "나이·후계 지분·지분 이동 등 신호를 함께 표시"],
    [fa.FaListOl, "우선순위", "점수 순 후보 리스트로 영업·컨설팅 대상 집중"],
  ];
  const panel = async (items, x, label, bg, circ, name) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.1, w: 5.55, h: 3.75, rectRadius: 0.1, fill: { color: bg },
      line: { type: "none" }, objectName: name + "_panel" });
    T(s, label, { x: x + 0.3, y: 2.25, w: 4.9, h: 0.4, fontSize: 16, bold: true, color: circ });
    for (let i = 0; i < items.length; i++) {
      const [ic, t, d] = items[i]; const y = 2.8 + i * 0.75;
      await iconCircle(s, ic, x + 0.3, y, 0.55, circ, HEX.white, `${name}_icon${i}`);
      T(s, t, { x: x + 1.05, y: y - 0.02, w: 4.2, h: 0.3, fontSize: 14, bold: true, color: HEX.ink });
      T(s, d, { x: x + 1.05, y: y + 0.28, w: 4.3, h: 0.3, fontSize: 12, color: HEX.grey });
    }
  };
  await panel(asis, 0.5, "AS-IS  현재 방식", HEX.asis, "7A8599", "asis");
  await panel(tobe, 7.28, "TO-BE  탐지 모델 도입 후", HEX.tint, HEX.blue, "tobe");
  s.addShape(pres.shapes.RIGHT_ARROW, { x: 6.2, y: 3.62, w: 0.93, h: 0.7, fill: { color: HEX.navy }, line: { type: "none" }, objectName: "asis_tobe_arrow" });
  const stats = [["1,833개사", "매년 자동 점수화 대상 상장사"], ["51%", "3년 점수 상위 50개 중 실제 승계 (무작위 7.5%)"],
                 ["약 7배", "1년 점수 상위 5%의 승계 비율 (15% vs 2.2%)"]];
  stats.forEach(([n, l], i) => {
    const x = 0.5 + i * 4.18;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 6.05, w: 3.98, h: 0.85, rectRadius: 0.08, fill: { color: HEX.navy },
      line: { type: "none" }, objectName: "stat" + i });
    T(s, n, { x: x + 0.2, y: 6.05, w: 1.5, h: 0.85, fontSize: 22, bold: true, color: HEX.white, valign: "middle" });
    T(s, l, { x: x + 1.7, y: 6.05, w: 2.15, h: 0.85, fontSize: 11, color: HEX.tint2, valign: "middle" });
  });
  s.addNotes("As-Is는 일반적인 수작업 탐색 방식 기준. 성과 수치는 과거 데이터 검증 결과(교차검증).");

  // ================= 3. 흐름도 =================
  pres.addSection({ title: "Ⅱ. 모델 구조" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Ⅱ. 모델 구조" });
  fill(s, "작동 흐름", "공시 수집부터 후보 리스트까지 6단계로 작동한다", "Ⅱ. 모델 구조",
    "OpenDART에서 받은 사업보고서 3종을 정제해 과거 승계 사례를 찾고, 기업×연도 신호로 모델을 학습한다. 최신 공시를 넣으면 3년 후보와 단기 주의 기업이 나온다.");
  const steps = [
    [fa.FaCloudDownloadAlt, "데이터 수집", "OpenDART API\n사업보고서 3종"],
    [fa.FaBroom, "정제 · 정규화", "관계 표기 700여 종\n→ 12개 유형"],
    [fa.FaTags, "승계 라벨링", "과거 승계 72건\n지분 50 · 경영 22"],
    [fa.FaSlidersH, "특성 생성", "기업×연도 37개 신호\n나이·지분·후계자"],
    [fa.FaCogs, "학습 · 검증", "13개 방법 비교\n교차검증+시간분할"],
    [fa.FaChartLine, "점수 산출", "최신 공시로\n기업별 0~1 점수"],
  ];
  const bw = 1.8, gap = 0.31;
  for (let i = 0; i < steps.length; i++) {
    const [ic, t, d] = steps[i]; const x = 0.5 + i * (bw + gap);
    const last = i === steps.length - 1;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.1, w: bw, h: 2.35, rectRadius: 0.1,
      fill: { color: last ? HEX.navy : HEX.tint }, line: { type: "none" }, objectName: "step" + (i + 1) });
    T(s, String(i + 1).padStart(2, "0"), { x: x + 0.15, y: 2.2, w: 0.6, h: 0.3, fontSize: 12, bold: true, color: last ? HEX.lightblue : HEX.blue });
    await iconCircle(s, ic, x + (bw - 0.7) / 2, 2.5, 0.7, last ? HEX.blue : HEX.white, last ? HEX.white : HEX.blue, "step_icon" + i);
    T(s, t, { x: x + 0.1, y: 3.3, w: bw - 0.2, h: 0.35, fontSize: 14, bold: true, align: "center", color: last ? HEX.white : HEX.navy });
    T(s, d, { x: x + 0.1, y: 3.68, w: bw - 0.2, h: 0.65, fontSize: 11, align: "center", color: last ? HEX.tint2 : HEX.grey });
    if (!last) s.addShape(pres.shapes.LINE, { x: x + bw + 0.04, y: 3.27, w: gap - 0.08, h: 0,
      line: { color: HEX.blue, width: 2, endArrowType: "triangle" }, objectName: "flow_arrow" + i });
  }
  // 산출물 분기
  const sx = 0.5 + 5 * (bw + gap) + bw / 2;
  s.addShape(pres.shapes.LINE, { x: sx, y: 4.45, w: 0, h: 0.35, line: { color: HEX.navy, width: 2 }, objectName: "branch_v" });
  s.addShape(pres.shapes.LINE, { x: 3.4, y: 4.8, w: sx - 3.4, h: 0, line: { color: HEX.navy, width: 2 }, objectName: "branch_h" });
  [3.4, 9.93].forEach((x, i) => s.addShape(pres.shapes.LINE, { x, y: 4.8, w: 0, h: 0.3,
    line: { color: HEX.navy, width: 2, endArrowType: "triangle" }, objectName: "branch_down" + i }));
  const outs = [
    [0.5, HEX.blue, "3년 탐지", "앙상블 모델 점수", "LightGBM·XGBoost·랜덤포레스트·로지스틱 순위 평균", "3년 후보 Top 150"],
    [7.03, HEX.purple, "6개월 탐지", "1년 RF 점수 + 트리거", "지분이전 · 증여상속 · 지분역전 · 80세 이상 · 후계 대표", "6개월 주의 65개사"],
  ];
  for (const [x, col, h, a, b, r] of outs) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 5.15, w: 5.8, h: 1.75, rectRadius: 0.1, fill: { color: HEX.white },
      line: { color: col, width: 1.5 }, objectName: "out_" + h });
    T(s, h, { x: x + 0.25, y: 5.3, w: 2.5, h: 0.35, fontSize: 16, bold: true, color: col });
    T(s, a, { x: x + 0.25, y: 5.72, w: 3.4, h: 0.3, fontSize: 13, bold: true, color: HEX.ink });
    T(s, b, { x: x + 0.25, y: 6.05, w: 3.5, h: 0.7, fontSize: 11, color: HEX.grey });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 3.85, y: 5.65, w: 1.75, h: 0.8, rectRadius: 0.08, fill: { color: col },
      line: { type: "none" }, objectName: "out_result_" + h });
    T(s, r, { x: x + 3.9, y: 5.65, w: 1.65, h: 0.8, fontSize: 13, bold: true, color: HEX.white, align: "center", valign: "middle" });
  }
  s.addNotes("매년 3월 사업보고서 공시 후 재실행. 6개월 탐지는 학습 사례가 적어 1년 점수와 규칙 트리거를 결합.");

  // ================= 4. 학습 데이터 =================
  pres.addSection({ title: "Ⅲ. 학습 · 검증" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Ⅲ. 학습 · 검증" });
  fill(s, "학습 데이터", "사업보고서 3종에서 과거 승계 72건을 찾아 학습했다", "Ⅲ. 학습 · 검증",
    "2015–2025년 1,833개 상장사의 최대주주·지분 변동·임원 공시 약 21만 행을 사용했다. 2019년 이전은 수록 기업이 적고, 승계 사례는 최근으로 갈수록 늘어난다.");
  const src = [
    [fa.FaUsers, "최대주주현황", "73,663행", "주주명 · 관계 · 기초/기말 지분율"],
    [fa.FaExchangeAlt, "최대주주변동현황", "28,607행", "변동일 · 변동 사유(증여·상속·장외매매)"],
    [fa.FaIdBadge, "임원현황", "106,677행", "출생년월 · 직위 · 등기 여부 · 관계"],
  ];
  for (let i = 0; i < src.length; i++) {
    const [ic, t, n, d] = src[i]; const y = 2.1 + i * 1.18;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y, w: 4.1, h: 1.05, rectRadius: 0.08, fill: { color: HEX.tint },
      line: { type: "none" }, objectName: "src" + i });
    await iconCircle(s, ic, 0.7, y + 0.22, 0.6, HEX.blue, HEX.white, "src_icon" + i);
    T(s, t, { x: 1.45, y: y + 0.14, w: 1.9, h: 0.35, fontSize: 14, bold: true, color: HEX.navy });
    T(s, n, { x: 3.2, y: y + 0.14, w: 1.25, h: 0.35, fontSize: 14, bold: true, color: HEX.blue, align: "right" });
    T(s, d, { x: 1.45, y: y + 0.52, w: 3.05, h: 0.4, fontSize: 11, color: HEX.grey });
  }
  const yrs = ["2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"];
  s.addChart(pres.charts.BAR, [{ name: "수록 기업 수", labels: yrs, values: [147, 146, 145, 143, 143, 817, 806, 803, 800, 1801, 1785] }], {
    x: 4.85, y: 2.05, w: 4.1, h: 3.6, barDir: "col", chartColors: [HEX.lightblue], showTitle: true, title: "연도별 수록 기업 수",
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: HEX.ink, showLegend: false, barGapWidthPct: 40,
    valGridLine: { color: "E5E9F2", size: 0.5 }, catGridLine: { style: "none" }, valAxisHidden: true, ...chartText, objectName: "chart_coverage",
  });
  s.addChart(pres.charts.BAR, [
    { name: "지분승계", labels: yrs.slice(1), values: [1, 3, 3, 3, 3, 2, 5, 6, 6, 18] },
    { name: "경영승계", labels: yrs.slice(1), values: [0, 0, 2, 1, 0, 6, 3, 2, 5, 3] },
  ], {
    x: 9.1, y: 2.05, w: 3.73, h: 3.6, barDir: "col", barGrouping: "stacked", chartColors: [HEX.blue, HEX.purple],
    showTitle: true, title: "연도별 승계 이벤트 (건)", showLegend: true, legendPos: "b", barGapWidthPct: 40,
    valGridLine: { color: "E5E9F2", size: 0.5 }, catGridLine: { style: "none" }, ...chartText, objectName: "chart_events",
  });
  const defs = [
    ["지분승계 50건", "최대주주(개인)가 직전 연도 특수관계인 명단의 가족으로 바뀐 경우"],
    ["경영승계 22건", "최대주주의 자녀·손자녀가 처음 대표이사에 오른 경우"],
    ["학습 표본", "3년: 1,233행 중 승계 93건(7.5%)\n1년: 45건 · 6개월: 19건"],
  ];
  defs.forEach(([h, d], i) => {
    const x = 0.5 + i * 4.18;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 5.9, w: 3.98, h: 1.0, rectRadius: 0.08,
      fill: { color: i === 2 ? HEX.navy : HEX.white }, line: { color: i === 2 ? HEX.navy : HEX.line, width: 1 }, objectName: "def" + i });
    T(s, h, { x: x + 0.2, y: 5.98, w: 3.6, h: 0.32, fontSize: 13, bold: true, color: i === 2 ? HEX.white : HEX.blue });
    T(s, d, { x: x + 0.2, y: 6.32, w: 3.6, h: 0.5, fontSize: 11, color: i === 2 ? HEX.tint2 : HEX.ink });
  });
  s.addNotes("2020년부터 수록 기업이 늘어난 것은 수집 범위 차이. 2025년 승계 급증은 최근 증여·상속 증가 영향으로 보임.");

  // ================= 5. 학습 방법 · 결과 =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Ⅲ. 학습 · 검증" });
  fill(s, "학습 방법 · 결과", "3년은 앙상블, 단기는 랜덤포레스트가 가장 정확했다", "Ⅲ. 학습 · 검증",
    "성격이 다른 방법을 같은 조건(기업 단위 5겹 교차검증 5회 반복 + 과거→미래 시간분할)으로 비교했다. 3년 앙상블은 상위 50개 중 51%를 맞혀 무작위보다 약 7배 정확했다.");
  const hdr = (t) => ({ text: t, options: { bold: true, color: HEX.white, fill: { color: HEX.navy }, align: "center", valign: "middle" } });
  const rows = [
    ["앙상블", "여러 모델 순위 평균 → 편차가 가장 작고 안정적", "0.392", "0.127", true],
    ["랜덤포레스트", "적은 데이터·결측값에 강함", "0.364", "0.136", true],
    ["LightGBM", "변수 간 비선형 상호작용 포착", "0.374", "0.117"],
    ["XGBoost", "LightGBM과 다른 방식의 부스팅 비교", "0.363", "0.109"],
    ["해저드", "1년 모델을 3년으로 환산, 학습 사례 확대", "0.275", "-"],
    ["전문가 점수표", "학습 없이 규칙만으로 점수", "0.266", "0.104"],
    ["로지스틱 회귀", "해석이 쉬운 기준선", "0.251", "0.072"],
  ];
  const tbl = [[hdr("방법"), hdr("선정 이유"), hdr("3년 AP"), hdr("1년 AP")]];
  rows.forEach(([m, r, a, b, best]) => {
    const o = { fill: { color: best ? HEX.tint2 : HEX.white }, color: HEX.ink, valign: "middle" };
    tbl.push([{ text: m, options: { ...o, bold: true, color: best ? HEX.navy : HEX.ink } }, { text: r, options: o },
      { text: a, options: { ...o, align: "center", bold: best && m === "앙상블" } },
      { text: b, options: { ...o, align: "center", bold: best && m === "랜덤포레스트" } }]);
  });
  s.addTable(tbl, { x: 0.5, y: 2.1, w: 7.35, colW: [1.65, 3.7, 1.0, 1.0], rowH: 0.42, fontSize: 12,
    border: { type: "solid", color: HEX.line, pt: 0.75 }, margin: [0, 0.08, 0, 0.08], objectName: "table_methods" });
  T(s, "AP: 점수 순으로 확인할 때의 평균 적중률 (무작위 기준 3년 0.075, 1년 0.022) · 음영 = 최종 선정", {
    x: 0.5, y: 5.52, w: 7.35, h: 0.3, fontSize: 10, color: HEX.grey });
  const mnames = ["앙상블", "LightGBM", "랜덤포레스트", "XGBoost", "해저드", "점수표", "로지스틱", "무작위"];
  s.addChart(pres.charts.BAR, [{ name: "3년 AP", labels: mnames, values: [0.392, 0.374, 0.364, 0.363, 0.275, 0.266, 0.251, 0.075] }], {
    x: 8.1, y: 2.05, w: 4.73, h: 3.8, barDir: "bar", catAxisOrientation: "maxMin",
    chartColors: [HEX.blue, HEX.lightblue, HEX.lightblue, HEX.lightblue, HEX.lightblue, HEX.lightblue, HEX.lightblue, "B8BFCC"],
    showTitle: true, title: "3년 탐지 방법별 AP", showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.000",
    dataLabelColor: HEX.ink, showLegend: false, valAxisHidden: true, valAxisMaxVal: 0.5, barGapWidthPct: 35,
    valGridLine: { style: "none" }, catGridLine: { style: "none" }, ...chartText, catAxisLabelColor: HEX.ink, objectName: "chart_ap",
  });
  const kp = [["51%", "3년 점수 상위 50개 중 실제 승계", "무작위 7.5%"], ["0.887", "시간분할 AUC", "2021년 이후 데이터로 검증"],
              ["15%", "1년 점수 상위 5% 적중률", "무작위 2.2%"]];
  kp.forEach(([n, l, sub], i) => {
    const x = 0.5 + i * 4.18;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 6.0, w: 3.98, h: 0.9, rectRadius: 0.08, fill: { color: i === 1 ? HEX.purple : HEX.navy },
      line: { type: "none" }, objectName: "kpi" + i });
    T(s, n, { x: x + 0.2, y: 6.0, w: 1.3, h: 0.9, fontSize: 24, bold: true, color: HEX.white, valign: "middle" });
    T(s, [{ text: l, options: { bold: true, breakLine: true } }, { text: sub, options: { color: HEX.tint2 } }],
      { x: x + 1.55, y: 6.0, w: 2.35, h: 0.9, fontSize: 11, color: HEX.white, valign: "middle" });
  });
  s.addNotes("AP는 희귀 사건 비교의 주 기준. 보강 특성(v2)은 개선 없었음. 6개월은 모든 방법이 약해(양성 19건) 1년 점수+트리거로 대체.");

  // ================= 6. 보완 · 한계 =================
  pres.addSection({ title: "Ⅳ. 향후 과제" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Ⅳ. 향후 과제" });
  fill(s, "보완 · 한계", "정확도 한계는 데이터 양에 있으며, 수시공시로 보완한다", "Ⅳ. 향후 과제",
    "예측 기간이 짧을수록 학습할 승계 사례가 줄어 정확도가 떨어진다. 모델을 바꾸기보다 데이터 범위를 넓히고 수시공시·주가를 결합하는 것이 다음 단계다.");
  const lim = [
    ["학습 사례 부족", "3년 93건 · 6개월 19건 (2019년 이전 140여 개사)", "2015–2019년 수록 기업을 전 상장사로 확대"],
    ["6개월 시점 정밀도", "연 1회 사업보고서만 사용", "수시공시 추가로 증여·상속을 즉시 감지"],
    ["후계자 추정 오차", "'자녀' 표기 · 동성 특수관계인 기준", "가족관계 표기 정제, 상위 후보 수작업 검증"],
    ["최대주주 나이 결측", "약 22%는 임원 명단에 없음", "다른 공시·외부 기업정보로 생년 보완"],
    ["주가 미반영", "공시 정보만 사용", "주가·PBR 결합 (저평가 구간 증여 경향 반영)"],
  ];
  T(s, "한계", { x: 0.5, y: 2.05, w: 3.9, h: 0.3, fontSize: 13, bold: true, color: HEX.navy });
  T(s, "보완 방안", { x: 5.0, y: 2.05, w: 3.9, h: 0.3, fontSize: 13, bold: true, color: HEX.blue });
  for (let i = 0; i < lim.length; i++) {
    const [t, d, f] = lim[i]; const y = 2.45 + i * 0.9;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y, w: 3.95, h: 0.78, rectRadius: 0.08, fill: { color: HEX.asis },
      line: { type: "none" }, objectName: "lim" + i });
    T(s, [{ text: t, options: { bold: true, color: HEX.ink, breakLine: true } }, { text: d, options: { color: HEX.grey, fontSize: 11 } }],
      { x: 0.7, y, w: 3.6, h: 0.78, fontSize: 13, valign: "middle" });
    s.addShape(pres.shapes.RIGHT_ARROW, { x: 4.55, y: y + 0.24, w: 0.35, h: 0.3, fill: { color: HEX.blue }, line: { type: "none" }, objectName: "lim_arrow" + i });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.0, y, w: 3.9, h: 0.78, rectRadius: 0.08, fill: { color: HEX.tint },
      line: { type: "none" }, objectName: "fix" + i });
    T(s, f, { x: 5.2, y, w: 3.55, h: 0.78, fontSize: 12, color: HEX.navy, valign: "middle" });
  }
  s.addChart(pres.charts.BAR, [{ name: "승계 사례 수", labels: ["3년", "1년", "6개월"], values: [93, 45, 19] }], {
    x: 9.2, y: 2.05, w: 3.63, h: 2.9, barDir: "col", chartColors: [HEX.blue, HEX.lightblue, HEX.purple],
    showTitle: true, title: "예측 기간별 학습 승계 사례 (건)", showValue: true, dataLabelPosition: "outEnd", dataLabelColor: HEX.ink,
    showLegend: false, valAxisHidden: true, valAxisMaxVal: 110, barGapWidthPct: 50, valGridLine: { style: "none" },
    catGridLine: { style: "none" }, ...chartText, catAxisLabelColor: HEX.ink, catAxisLabelFontSize: 11, objectName: "chart_cases",
  });
  T(s, [{ text: "AP  ", options: { bold: true, color: HEX.navy } }, { text: "0.39  →  0.14  →  0.03", options: { color: HEX.ink } }],
    { x: 9.2, y: 4.95, w: 3.63, h: 0.3, fontSize: 12, align: "center" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 9.2, y: 5.45, w: 3.63, h: 1.45, rectRadius: 0.1, fill: { color: HEX.purple },
    line: { type: "none" }, objectName: "next_step" });
  T(s, [{ text: "다음 단계", options: { bold: true, fontSize: 14, breakLine: true } },
        { text: "수시공시 2종 수집 → 6개월 탐지 재학습, 주가 데이터 결합 후 성능 재검증", options: { fontSize: 12, color: HEX.tint } }],
    { x: 9.4, y: 5.45, w: 3.25, h: 1.45, color: HEX.white, valign: "middle" });
  s.addNotes("검증 수치는 과거 데이터 기준이며, 현재 후보 목록의 실제 적중 여부는 향후 공시로 확인 필요.");

  await pres.writeFile({ fileName: "가업승계_탐지모델.pptx" });
  await applyTheme("가업승계_탐지모델.pptx", THEME);
  console.log("done");
})();
