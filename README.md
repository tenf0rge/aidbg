# aidbg

Autonomous debug assistant for SoC verification. From SVA/UVM failures, it
works out the **root cause** and — most importantly — whether the defect is on
the **design (RTL/netlist)** side or the **verification-environment (UVM/TB)**
side. It only ever *reads* the waveform, log, and source repo; its sole output
is a report. It never edits a file.

## Three layers

aidbg is deliberately thin. The intelligence is the LLM agent; aidbg gives it
**eyes** (precise queries over huge waveforms/logs) and **knowledge** (skill
playbooks), then gets out of the way.

```
1. toolbox (aidbg/toolbox)  — read-only primitives the agent calls (the "eyes")
2. profile + engine         — profiles/<name>/AGENTS.md picks the persona, the
                              read-only rules, the report format, AND which
                              skill playbooks to load; an LLM engine does the
                              judgement
3. skills (skills/*.md)     — domain knowledge as *procedure playbooks* (method
                              + worked example). Swap these → swap the battlefield
```

The judgement lives in the LLM. A **skill is a markdown 手順書** — "do these
queries, read this evidence, here's a worked example, decide design vs TB" — not
code. To target a new kind of verification you write a playbook and a profile;
the toolbox and the core don't change.

---

# Getting started

## 1. Prerequisites（まず準備するもの）

| 必須 | 用途 |
|---|---|
| **Python 3.10+** | toolbox は標準ライブラリのみ（実行時依存ゼロ） |
| **git** | `blame` / `find-driver` の attribution（「誰のどのコミット」）に必要 |
| **LLM エンジン**（`aidbg auto` を使うとき） | 判断を行う本体。下のどちらか |

LLM エンジンは2択（`--engine` で切替）:

- **opencode**（無料・ログイン不要、同梱の無料モデル）
  ```bash
  curl -fsSL https://opencode.ai/install | bash      # → ~/.opencode/bin/opencode
  ```
- **claude**（高品質・Claude Code CLI、自分の Claude 利用枠を消費）
  ```bash
  # 既に Claude Code CLI（~/.local/bin/claude）が認証済みであること
  ```

primitives（`env`/`query`/`blame` など）だけなら LLM エンジンは不要です。

## 2. Install

```bash
git clone git@github.com:tenf0rge/aidbg.git
cd aidbg
python -m venv .venv && . .venv/bin/activate      # 任意
pip install -e .                                   # `aidbg` コマンドが有効に
# インストールせず `python -m aidbg ...` でも動く
```

## 3. 入力として用意するもの（3つ、すべて read-only で渡すだけ）

| 入力 | 形式 | 例 |
|---|---|---|
| **waveform** `--wave` | テキスト。CSVテーブル（`Time(ns),sig,sig[31:0],…` バスはhex、FSDB→CSVエクスポート）か、イベントリスト（`time scope.signal value(strength)`、混合信号向け）。**自動判別** | `samples/apb/wave.csv` |
| **log** `--log` | Xcelium / UVM ログ（`UVM_ERROR … @ N: comp [ID] msg` や SVA 失敗、`*W/E/F`） | `samples/apb/run.log` |
| **source** `--source`（任意） | 設計/TB の **git リポジトリのルート**。指定すると blame で「誰のどのコミット」まで辿れる | `samples/fixture/design` |

最低1つ（普通は wave か log）あれば動きます。波形は巨大でも OK——aidbg が変化点に圧縮し、エージェントは丸読みせず**問い合わせ**で事実を取ります。

## 4. まず動かす（同梱サンプルで30秒）

```bash
# どんな profile があるか
aidbg profiles
#   apb-uvm
#   mixed-signal

# デジタル: APBレジスタ read 不一致を 設計 vs TB に切り分け（無料エンジン・日本語）
aidbg auto --profile apb-uvm --engine opencode \
  --wave samples/apb/wave.csv --log samples/apb/run.log --lang ja

# ミックスドシグナル: tranif 競合 → X を git blame 付きで（source も渡す）
aidbg auto --profile mixed-signal --engine opencode \
  --wave samples/fixture/sim/wave.txt --log samples/fixture/sim/uvm.log \
  --source samples/fixture/design --lang ja
```

`--out report.md` でファイル出力、`--engine claude` で高品質（枠消費）。

## 5. サンプルが示すこと（何を検証できるか）

| サンプル | 何のデモ | 期待される結論 |
|---|---|---|
| `samples/apb/` | 実フォーマット（CSV波形＋Xcelium UVMログ）。SCB不一致2件 | 0x1000=**DESIGN**（バスが誤データ）/ 0x1004=**VERIFICATION-ENV**（バス正・TB取り違え） |
| `samples/fixture/` | **既知コミットにバグを仕込んだ git fixture**（Alice正常→Bob Hotfix）。`build_fixture.sh` で再構築 | tranif 競合→X を **Bob Hotfix / rtl/ctrl.sv:14** に attribution |
| `samples/scenario_tb/` | 検証環境側が真因のケース | グリッチが sim-artifact（**VERIFICATION-ENV**）と判定 |

primitives を直接叩いて事実だけ見ることもできます:

```bash
aidbg env       --log  samples/apb/run.log                       # 環境理解（まずこれ）
aidbg grep-log  --log  samples/apb/run.log --severity ERROR      # 失敗イベント
aidbg query     --wave samples/apb/wave.csv --signal prdata --time 110
aidbg blame     --source samples/fixture/design --file rtl/ctrl.sv --line 14
```

## 6. 自分の検証に合わせる（profile と skill を書く）

新しい検証ドメインを足す＝**ファイルを置くだけ**。toolbox もコアも触りません。

1. **手順書を書く** `skills/<name>.md` — 方法＋実例（「このクエリを叩け／この証拠で設計かTBか決めろ」）。
2. **profile を書く** `profiles/<name>/AGENTS.md` — ペルソナ・read-only規約・レポート様式（①エラー→②誰のコミット→③真因→④修正案）と、**使う手順書と使いどころ**:
   ```markdown
   ## 使う手順書と使いどころ
   - レジスタ read 不一致が出たら → skills/reg-data-mismatch.md
   - UVM ERROR の発報元を切り分けたいとき → skills/uvm-env.md
   ```
   AGENTS.md が `skills/<name>.md` と参照した手順書だけがロードされます（全ロードではない＝profile が戦場のスキルを明示選択）。
3. **実行** `aidbg auto --profile <name> …`

リポジトリ外に置くなら環境変数で:

```bash
AIDBG_PROFILES_PATH=~/my-org/profiles AIDBG_SKILLS_PATH=~/my-org \
  aidbg auto --profile my-custom --wave … --log …
```

---

## The primitive tool box (what the agent calls — Layer 1)

| command | purpose |
|---|---|
| `aidbg env --log L` | understand the environment (loaded files, snapshot, test, sequences, UVM component tree) — the "read the log first" step |
| `aidbg signals --wave W` | list signals |
| `aidbg query --wave W --signal S [--time N]` | value at a time / all change points |
| `aidbg grep-log --log L [--severity E] [--pattern RE]` | filter log events (JSON) |
| `aidbg grep-source --source DIR --pattern RE` | search SV/Verilog (read an assertion's intent by name) |
| `aidbg find-driver --source DIR --signal S` | where a signal is driven in SV |
| `aidbg blame --source DIR --file F --line N` | git blame a line ("who/which commit") |

Deterministic, stdlib-only, JSON out — usable by any agent or a human directly.

## Bundled profiles

- **mixed-signal** — tranif pass-gate contention → X, glitch real-vs-artifact,
  UVM triage. (skills: tranif-contention, glitch-triage, uvm-env)
- **apb-uvm** — APB register read mismatch split into DUT vs TB bug by reading
  the real bus `prdata`. (skills: reg-data-mismatch, uvm-env)

## Principles

- **The toolbox holds no debug knowledge.** It is read-only data access. The
  knowledge is in the skill playbooks; the judgement is the LLM's.
- **aidbg never edits source.** It reads the design/TB and the inputs. Its sole
  output is the report. Fix suggestions are proposals for a human, never applied.
- **The report answers, in order:** what error → which commit/author introduced
  it (git blame) → **the root cause (most important)** → a suggested fix.

## Layout

```
aidbg/
  toolbox/      Layer 1 — read-only primitives (the eyes)
    primitives.py   env / signals / query / grep-log / grep-source / blame / find-driver
    wave.py logs.py repo.py source.py   loaders + git blame + source scan
    models.py       Edge / LogEvent / Attribution
  launcher.py   Layer 2 — resolve a profile, load its skills, drive the engine
  cli.py        `aidbg auto` + the primitives
profiles/<name>/AGENTS.md   Layer 2 — persona, rules, report format, skill list
skills/<name>.md            Layer 3 — procedure playbooks (judgement knowledge)
samples/                    runnable scenarios + a git fixture (planted bug)
tests/                      toolbox + launcher + fixture-attribution tests
```

## Develop

```bash
pip install -e ".[dev]"
pytest                       # toolbox + launcher + fixture attribution (read-only verified)
```
