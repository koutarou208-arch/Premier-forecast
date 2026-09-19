# Global Financial Crisis Watch v5

世界的な信用収縮をリアルタイム監視しつつ、同じロジックを過去データへ walk-forward 適用して、危機捕捉と警報頻度を継続検証する GitHub Pages ダッシュボードです。

## v5: historical validation

v5の最大の変更は、**未来データを参照しない walk-forward backtest**です。各過去時点について、その日までに存在したデータだけで Level / Deviation / Velocity / Breadth / Stage を再計算します。

- 2007年以降をNFCIベースで週次再計算
- ラベル済みストレス窓とreference date前120日は日次サンプリングを追加し、短期Funding shockを捕捉
- 過去検証は長期公開proxyで作る Historical-comparable score を使用し、現在だけ存在するAIイベント手動点は混ぜない
- FREDのICE BofA OAS系列は2026年4月以降3年ローリングに制限されたため、歴史検証では IG=BAA10Y、Credit=NFCICREDIT、Leveraged=NFCIRISK を使用
- Fundingの歴史検証は SOFR-IORB → SOFR-IOER → TED spread の順で制度時点に合わせて切り替え
- 欠損系列は安全=0点にせず、その時点の分母から除外
- ラベル外期間の警報率も計測
- 現在のHistorical-comparable scoreが歴史分布の何percentileか表示
- バックテスト結果は毎回Actionsで再生成

## Validation windows

`data/backtest_config.json` で検証期間を管理します。

- Global Financial Crisis
- Euro-area sovereign stress
- US repo-market stress 2019
- COVID liquidity shock
- US regional-bank stress 2023 — holdout

`reference_date` はlead表示の計算用アンカーであり、危機の公式な開始日を意味しません。

## Why not auto-optimize the weights?

少数の危機イベントだけを最大化するように重みを探索すると過学習しやすいため、v5では重みを自動で書き換えません。まず以下を監査します。

- 各危機窓のpeak score
- 最大Stage
- Watch / Elevated / Highの初回到達日
- reference dateに対するlead days
- ラベル外期間で25 / 45 / 65 / 80を超えた比率
- ラベル外期間のP90 / P95 / P99
- 現在Market-only scoreの歴史percentile

ラベル外で鳴った警報は自動的にfalse positiveとは呼びません。設定していないストレス局面が存在するためです。

## Current production model

v4で追加した12チャネル・5 Pillarsはv5でも継続します。

| Channel | Weight | Automatic source / fallback |
| --- | ---: | --- |
| US IG Corporate OAS | 10% | FRED BAMLC0A0CM |
| US High Yield OAS | 14% | FRED BAMLH0A0HYM2 |
| Leveraged / Structured Credit | 10% | CCC OAS; optional CDX/CLO |
| St. Louis Financial Stress | 8% | FRED STLFSI4 |
| Treasury Vol / Liquidity | 8% | DGS10 RV20 + VIX; optional MOVE |
| Repo / Funding Market | 10% | SOFR - IORB |
| Bank Short-term Funding | 8% | CPFF; optional Bank CDS |
| Italy-Bund | 6% | OECD/FRED monthly; optional daily override |
| Energy shock | 7% | WTI + Henry Hub |
| AI Data-center Financing | 6% | event evidence |
| Private-credit Liquidity | 8% | event evidence; optional BDC NAV discount |
| Bank AI-credit Inventory | 5% | syndication / lender evidence |

## Dynamic scoring

自動時系列は0-100点に変換します。

- Level 45% — 絶対水準
- Deviation 30% — 最大約5年のpercentile + robust Z-score
- Velocity 25% — 5観測・20観測の悪化速度
- Breadth overlay — 複数市場の同時悪化時のみ最大+8点

## Production vs historical-comparable

FRED上のICE BofA系列は2026年4月から直近3年に制限されているため、2008年まで遡る完全同一モデルの再現はできません。v5はここを隠さず、productionとhistorical validationを分離します。

- **Production Market-only Score** — 現在のIG/HY/CCC OASなどを使用
- **Historical-comparable Score** — BAA10Y / NFCICREDIT / NFCIRISKなど長期公開proxyを使用

## Two headline scores

- **Systemic Stress Score** — AI / Private Creditイベント層も含む現在監視用スコア
- **Market-only Score** — 公開市場・Funding・銀行proxyだけ。現在の市場層を分離するためのスコア

バックテストはHistorical-comparable Scoreを使用します。Production Market-only Scoreとは別系列として表示します。

## Data files

- `data/latest.js` — 現在値
- `data/history.json` / `data/history.js` — 日次履歴
- `data/backtest_config.json` — 検証窓
- `data/backtest.json` / `data/backtest.js` — walk-forward検証結果
- `data/manual.json` — MOVE / CDX / CLO / Bank CDS / BDCなどの任意実値

## Scripts

- `scripts/update_data.py` — 現在値更新
- `scripts/backtest.py` — walk-forward historical validation（SOFR-IORB / SOFR-IOER / TED の時代別Funding proxyを使用）

## GitHub Actions

**Actions -> Update crisis dashboard v5 -> Run workflow**

実行順序:

1. Python構文チェック
2. 現在市場データ更新
3. walk-forward backtest
4. v5 payload検証
5. current snapshot + history + backtestをcommit

## GitHub Pages

公開URL: https://koutarou208-arch.github.io/Premier-forecast/

## Important

この指数は金融危機の発生確率ではありません。Stress intensity / breadth / transmissionを測る監視指数です。バックテストも将来の危機を保証するものではなく、既知の過去局面でモデルがどう振る舞ったかを検証するためのものです。
