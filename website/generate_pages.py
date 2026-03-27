#!/usr/bin/env python3
"""Generate individual episode HTML pages from JSON data and markdown simulations."""
import json
import os
import re
import html as html_mod

TEMPLATE = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{episode_id} — {title_escaped}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&family=Noto+Sans+JP:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;500&display=swap');

:root {{
  --black: #0a0a0a;
  --white: #f5f5f0;
  --gray-1: #1a1a1a;
  --gray-2: #2a2a2a;
  --gray-3: #4a4a4a;
  --gray-4: #7a7a7a;
  --gray-5: #aaaaaa;
  --accent: #ff3333;
  --green: #00cc66;
  --blue: #4488ff;
  --grid: 8px;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
  font-family: 'Inter', 'Noto Sans JP', sans-serif;
  background: var(--black);
  color: var(--white);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}}

.container {{ max-width: 900px; margin: 0 auto; padding: 0 calc(var(--grid) * 4); }}

.back {{
  display: inline-block;
  padding: calc(var(--grid) * 4) 0;
  color: var(--gray-4);
  text-decoration: none;
  font-size: 13px;
  letter-spacing: 1px;
}}
.back:hover {{ color: var(--white); }}

.ep-header {{
  padding: calc(var(--grid) * 6) 0;
  border-bottom: 1px solid var(--gray-2);
}}

.ep-id {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--gray-4);
  letter-spacing: 2px;
  margin-bottom: calc(var(--grid) * 2);
}}

.ep-title {{
  font-size: clamp(24px, 4vw, 42px);
  font-weight: 700;
  letter-spacing: -1px;
  line-height: 1.2;
  margin-bottom: calc(var(--grid) * 3);
}}

.ep-badge {{
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1px;
  padding: 3px 10px;
  border-radius: 2px;
  margin-bottom: calc(var(--grid) * 3);
}}
.badge-success {{ background: rgba(0,204,102,0.15); color: var(--green); border: 1px solid rgba(0,204,102,0.3); }}
.badge-failure {{ background: rgba(255,51,51,0.15); color: var(--accent); border: 1px solid rgba(255,51,51,0.3); }}
.badge-warning {{ background: rgba(255,200,50,0.15); color: #ffc832; border: 1px solid rgba(255,200,50,0.3); }}

.ep-summary {{
  font-size: 15px;
  color: var(--gray-5);
  line-height: 1.7;
  margin-bottom: calc(var(--grid) * 4);
}}

.ep-stats {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1px;
  background: var(--gray-2);
  border: 1px solid var(--gray-2);
  margin-bottom: calc(var(--grid) * 8);
}}

.ep-stat {{
  background: var(--black);
  padding: calc(var(--grid) * 3);
  text-align: center;
}}

.ep-stat-value {{
  font-size: 24px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}}
.ep-stat-value.green {{ color: var(--green); }}
.ep-stat-value.red {{ color: var(--accent); }}

.ep-stat-label {{
  font-size: 9px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--gray-4);
  margin-top: 4px;
}}

/* Exchange */
.exchange {{
  padding: calc(var(--grid) * 4) 0;
  border-bottom: 1px solid var(--gray-2);
}}

.exchange-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: calc(var(--grid) * 2);
}}

.exchange-round {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 500;
}}
.round-in {{ color: var(--blue); }}
.round-out {{ color: var(--green); }}
.round-sys {{ color: var(--accent); }}

.exchange-stage {{
  font-size: 10px;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--gray-4);
  background: var(--gray-1);
  padding: 2px 8px;
  border-radius: 2px;
}}

.exchange-from {{
  font-size: 12px;
  color: var(--gray-5);
  margin-bottom: 4px;
}}

.exchange-subject {{
  font-size: 14px;
  font-weight: 600;
  margin-bottom: calc(var(--grid) * 2);
}}

.exchange-body {{
  font-size: 13px;
  line-height: 1.8;
  color: var(--gray-6);
  white-space: pre-wrap;
  padding: calc(var(--grid) * 3);
  background: var(--gray-1);
  border-left: 3px solid var(--gray-3);
  border-radius: 0 4px 4px 0;
  margin-bottom: calc(var(--grid) * 2);
}}

.exchange-body.inbound {{ border-left-color: var(--blue); }}
.exchange-body.outbound {{ border-left-color: var(--green); }}
.exchange-body.system {{ border-left-color: var(--accent); }}

.exchange-apis {{
  margin-top: calc(var(--grid) * 2);
}}

.api-call {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--gray-4);
  padding: 4px 0;
  display: flex;
  gap: 8px;
  align-items: baseline;
}}

.api-name {{ color: var(--gray-5); }}
.api-cost {{ color: var(--accent); font-size: 10px; }}
.api-desc {{ color: var(--gray-3); font-size: 10px; }}

/* Post-mortem */
.postmortem {{
  padding: calc(var(--grid) * 6) 0;
  border-top: 2px solid var(--accent);
  margin-top: calc(var(--grid) * 4);
}}

.postmortem h3 {{
  font-size: 16px;
  color: var(--accent);
  margin-bottom: calc(var(--grid) * 3);
  letter-spacing: 1px;
}}

.postmortem ul {{
  list-style: none;
  padding: 0;
}}

.postmortem li {{
  font-size: 13px;
  color: var(--gray-5);
  padding: 6px 0;
  padding-left: 16px;
  position: relative;
}}

.postmortem li::before {{
  content: '—';
  position: absolute;
  left: 0;
  color: var(--gray-3);
}}

.footer {{
  padding: calc(var(--grid) * 6) 0;
  text-align: center;
  color: var(--gray-3);
  font-size: 11px;
}}
</style>
</head>
<body>
<div class="container">
  <a class="back" href="index.html">← ALL EPISODES</a>

  <div class="ep-header">
    <div class="ep-id">{episode_id}</div>
    <div class="ep-badge {badge_class}">{result_label}</div>
    <h1 class="ep-title">{title_escaped}</h1>
    <p class="ep-summary">{summary_escaped}</p>
  </div>

  <div class="ep-stats">
    <div class="ep-stat">
      <div class="ep-stat-value">{rounds}</div>
      <div class="ep-stat-label">Rounds</div>
    </div>
    <div class="ep-stat">
      <div class="ep-stat-value">{days}d</div>
      <div class="ep-stat-label">Duration</div>
    </div>
    <div class="ep-stat">
      <div class="ep-stat-value {revenue_class}">{revenue_display}</div>
      <div class="ep-stat-label">Revenue</div>
    </div>
    <div class="ep-stat">
      <div class="ep-stat-value">¥{api_cost}</div>
      <div class="ep-stat-label">API Cost</div>
    </div>
  </div>

  {exchanges_html}

  {postmortem_html}

  <div class="footer">SALES MIRROR BOT — 営業ボットには、営業ボットを。</div>
</div>
</body>
</html>
"""


def format_revenue(rev):
    if rev == 0:
        return "¥0"
    if rev >= 1_000_000:
        return f"¥{rev / 1_000_000:.1f}M"
    return f"¥{rev:,}"


def build_exchange_html(ex):
    direction = ex.get("direction", "inbound")
    round_num = ex.get("round", "?")
    stage = ex.get("stage", "")
    subject = html_mod.escape(ex.get("subject", ""))
    body = html_mod.escape(ex.get("body", ""))
    from_addr = html_mod.escape(ex.get("from", ""))

    if direction == "inbound":
        round_class = "round-in"
        round_label = f"R{round_num} ← INBOUND"
        body_class = "inbound"
    elif direction == "outbound":
        round_class = "round-out"
        round_label = f"R{round_num} → OUTBOUND"
        body_class = "outbound"
    else:
        round_class = "round-sys"
        round_label = f"R{round_num} ⚠ SYSTEM"
        body_class = "system"

    apis_html = ""
    for api in ex.get("apis_used", []):
        name = html_mod.escape(api.get("api", ""))
        cost = api.get("cost_usd", api.get("cost", 0))
        cost_str = f"${cost}" if cost else ""
        desc = html_mod.escape(api.get("description", api.get("note", "")))
        apis_html += f'<div class="api-call"><span class="api-name">{name}</span>'
        if cost_str:
            apis_html += f' <span class="api-cost">{cost_str}</span>'
        if desc:
            apis_html += f' <span class="api-desc">// {desc}</span>'
        apis_html += '</div>\n'

    return f"""
    <div class="exchange">
      <div class="exchange-header">
        <span class="exchange-round {round_class}">{round_label}</span>
        <span class="exchange-stage">{stage}</span>
      </div>
      {"<div class='exchange-from'>" + from_addr + "</div>" if from_addr else ""}
      <div class="exchange-subject">{subject}</div>
      <div class="exchange-body {body_class}">{body}</div>
      {"<div class='exchange-apis'>" + apis_html + "</div>" if apis_html else ""}
    </div>
    """


def build_postmortem_html(data):
    pm = data.get("post_mortem")
    if not pm:
        return ""

    lessons = pm.get("lessons", [])
    root = html_mod.escape(pm.get("root_cause", ""))

    items = ""
    for lesson in lessons:
        items += f"<li>{html_mod.escape(lesson)}</li>\n"

    return f"""
    <div class="postmortem">
      <h3>POST-MORTEM</h3>
      {"<p style='color:var(--gray-5);font-size:13px;margin-bottom:16px;'>Root cause: " + root + "</p>" if root else ""}
      <ul>{items}</ul>
    </div>
    """


def generate_json_episode(filepath, output_dir):
    with open(filepath) as f:
        data = json.load(f)

    ep_id = data["episode_id"]
    result = data["result"]
    title = data["title"]
    summary = data.get("summary", "")
    rounds = data["metadata"]["rounds"]
    days = data["metadata"]["duration_days"]
    revenue = data.get("financial", {}).get("revenue", data.get("financial", {}).get("revenue_annual", 0))
    api_cost = data.get("api_summary", {}).get("total_cost_jpy", 0)

    badge_class = "badge-success" if result == "SUCCESS" else "badge-failure"
    result_label = result
    revenue_class = "green" if revenue > 0 else ""
    revenue_display = format_revenue(revenue)

    exchanges_html = ""
    for ex in data.get("exchanges", []):
        exchanges_html += build_exchange_html(ex)

    postmortem_html = build_postmortem_html(data)

    page = TEMPLATE.format(
        episode_id=ep_id,
        title_escaped=html_mod.escape(title),
        summary_escaped=html_mod.escape(summary),
        badge_class=badge_class,
        result_label=result_label,
        rounds=rounds,
        days=days,
        revenue_class=revenue_class,
        revenue_display=revenue_display,
        api_cost=api_cost,
        exchanges_html=exchanges_html,
        postmortem_html=postmortem_html,
    )

    # Determine output filename
    num = ep_id.replace("EP-", "")
    outpath = os.path.join(output_dir, f"episode_{num}.html")
    with open(outpath, "w") as f:
        f.write(page)
    print(f"Generated: {outpath}")


def generate_markdown_case(case_num, md_path, output_dir, meta):
    """Generate an episode page from markdown simulation files."""
    with open(md_path) as f:
        content = f.read()

    ep_id = f"CASE-{case_num:02d}"
    title = meta["title"]
    summary = meta["summary"]
    result = meta["result"]
    rounds = meta["rounds"]
    days = meta["days"]
    revenue = meta["revenue"]
    api_cost = meta["api_cost"]

    badge_class = {"SUCCESS": "badge-success", "FAILURE": "badge-failure", "NEAR-MISS": "badge-warning"}[result]

    # Parse markdown sections into exchange-like blocks
    exchanges_html = ""
    sections = re.split(r'^## ', content, flags=re.MULTILINE)
    round_num = 0
    for section in sections[1:]:  # Skip first part (header)
        lines = section.strip().split('\n')
        heading = lines[0].strip()

        # Determine direction from heading
        if '受信' in heading or '← ' in heading:
            direction = 'inbound'
        elif '送信' in heading or '→ ' in heading:
            direction = 'outbound'
        else:
            direction = 'system'

        round_num += 1

        # Extract body from code blocks
        body_parts = []
        in_code = False
        for line in lines[1:]:
            if line.startswith('```'):
                in_code = not in_code
                continue
            if in_code:
                body_parts.append(line)

        body = '\n'.join(body_parts) if body_parts else '\n'.join(lines[1:5])

        ex = {
            "round": round_num,
            "direction": direction,
            "subject": heading[:60],
            "body": body[:1500],
            "stage": "",
            "apis_used": [],
        }
        exchanges_html += build_exchange_html(ex)

    revenue_class = "green" if revenue > 0 else ""
    revenue_display = format_revenue(revenue)

    page = TEMPLATE.format(
        episode_id=ep_id,
        title_escaped=html_mod.escape(title),
        summary_escaped=html_mod.escape(summary),
        badge_class=badge_class,
        result_label=result,
        rounds=rounds,
        days=days,
        revenue_class=revenue_class,
        revenue_display=revenue_display,
        api_cost=api_cost,
        exchanges_html=exchanges_html,
        postmortem_html="",
    )

    outpath = os.path.join(output_dir, f"episode_case{case_num}.html")
    with open(outpath, "w") as f:
        f.write(page)
    print(f"Generated: {outpath}")


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = base_dir
    episodes_dir = os.path.join(base_dir, "..", "scenarios", "episodes")
    scenarios_dir = os.path.join(base_dir, "..", "scenarios")

    # Generate JSON-based episodes
    for f in sorted(os.listdir(episodes_dir)):
        if f.endswith(".json"):
            generate_json_episode(os.path.join(episodes_dir, f), output_dir)

    # Generate Markdown-based cases
    md_cases = [
        (1, "simulation_case1_success.md", {"title": "インフルエンサーマーケ代理店 → PF本体へAI開発PoC逆受注", "summary": "月額5.5万円の協力店営業から、PF運営本体へのAI開発PoC ¥500万を逆受注。代理店にも紹介手数料10%を支払い味方に。APIコスト約¥75で¥450万の利益。", "result": "SUCCESS", "rounds": 10, "days": 20, "revenue": 4500000, "api_cost": 75}),
        (2, "simulation_case2_success.md", {"title": "AI研修セミナー → 研修共同開発パートナーシップ", "summary": "「無料AI研修いかがですか」に対し「こちらがAI研修を作る側です」と逆転。相手の助成金ノウハウと弊社のAI技術を組み合わせ、研修商品の共同開発パートナーシップ。", "result": "SUCCESS", "rounds": 10, "days": 30, "revenue": 18500000, "api_cost": 75}),
        (3, "simulation_case3_failure.md", {"title": "同一企業の重複営業 — テンプレ返信で疑惑を持たれる", "summary": "同じ会社の別担当者から同じメール。ボットは1通で処理したが、社内で「返信がテンプレっぽい」と疑問を持たれるヒヤリハット。", "result": "NEAR-MISS", "rounds": 2, "days": 3, "revenue": 0, "api_cost": 30}),
        (4, "simulation_case4_failure.md", {"title": "取締役のZoom面談要求 — テキストボットの限界で自然消滅", "summary": "取締役からの「ビデオ面談必須」にテキストボットでは対応不能。海外出張を理由に延期するも、14日間無返信でDEAD判定。推定¥1,300万の機会損失。", "result": "FAILURE", "rounds": 6, "days": 45, "revenue": 0, "api_cost": 45}),
    ]

    for case_num, md_file, meta in md_cases:
        md_path = os.path.join(scenarios_dir, md_file)
        if os.path.exists(md_path):
            generate_markdown_case(case_num, md_path, output_dir, meta)

    print(f"\nDone. Generated pages in {output_dir}")


if __name__ == "__main__":
    main()
