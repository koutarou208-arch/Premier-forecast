# Global Financial Crisis Watch v4

世界的な信用収縮を、企業信用だけでなく **repo資金市場・銀行短期調達・レバレッジド／構造化クレジット・AI/Private Credit・欧州・エネルギー** まで横断して監視する GitHub Pages ダッシュボードです。

## v4 additions

- SOFR − IORB: repo / secured funding pressure
- 3-Month Financial Commercial Paper − Fed Funds (CPFF): bank / short-term funding proxy
- CCC & Lower HY OAS: leveraged-credit / structured-credit proxy
- optional CDX HY 5Y override
- optional CLO AAA / BBB spread overrides
- optional representative Bank CDS override
- optional BDC discount-to-NAV overlay for private credit
- 12 weighted risk channels and 5 pillars

無料で安定取得できないCDX/CLO/Bank CDS/BDCは、未入力を安全=0点とは扱いません。自動代理指標と手動の実値を明示的に分離し、実値が入った時だけより強いシグナルとして採用します。

## 12 risk channels

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

Total = 100%.

## Dynamic scoring

自動時系列は0-100点に変換します。

- Level 45%: 絶対水準
- Deviation 30%: 最大約5年のpercentile + robust Z-score
- Velocity 25%: 5観測・20観測の悪化速度
- Breadth overlay: 複数市場が同時悪化した場合だけ最大+8点

欠損は0点にせず分母から除外し、coverage_pct を表示します。

## v4 proxy / override policy

### Leveraged / Structured Credit

自動: ICE BofA CCC & Lower US HY OAS (BAMLH0A3HYC)。
オプション: CDX HY 5Y、CLO AAA、CLO BBB。入力された値の方がよりストレスを示す場合はそちらを採用します。

### Funding Market

SOFR − IORB をbpsで計算します。SOFRがIORBを大きく上回るほど、secured funding / repo pressure のシグナルとして扱います。

### Banking Stress

自動: 3-Month AA Financial Commercial Paper − Federal Funds Rate (CPFF)。
オプション: representative bank 5Y CDS。CDSが入力され、より強いストレスを示す場合は上書きします。

### Private Credit

既存のファンド償還・ゲート等のイベントスコアに加え、BDC discount-to-NAV を正の割引率で入力可能です。例: NAV比12%ディスカウントなら 12。

## 5 pillars

- Broad Credit: IG / HY / Leveraged
- Funding / Liquidity: STLFSI / Treasury vol / SOFR-IORB
- Banking: CPFF/Bank CDS + Bank AI inventory
- AI / Private Credit: Data-center / Private Credit / Bank AI inventory
- Europe / Energy

## Transmission stages

- Stage 0 — CALM
- Stage 1 — SECTOR REPRICING
- Stage 2 — CREDIT TRANSMISSION
- Stage 3 — FUNDING STRESS
- Stage 4 — SYSTEMIC / FREEZE

Stage 4には Broad Credit、Funding、Banking、Breadth の複数条件を同時に要求します。単一市場の急騰だけではStage 4になりません。

## Manual market overrides

`data/manual.json`:

- `move_index`
- `europe_daily_spread_bps`
- `cdx_hy_spread_bps`
- `clo_aaa_spread_bps`
- `clo_bbb_spread_bps`
- `bank_cds_bps`
- `bdc_discount_pct`

値が不明な場合は null のままにします。

## Refresh

GitHub Actions: **Actions -> Update crisis dashboard v4 -> Run workflow**

平日の定期更新に加え、計算エンジンやmanual inputを変更した時も再計算します。

## GitHub Pages

公開URL: https://koutarou208-arch.github.io/Premier-forecast/

## Important

このスコアは金融危機の発生確率ではありません。市場・信用・資金調達のストレス強度と、セクター間の伝播度を測る監視指数です。
