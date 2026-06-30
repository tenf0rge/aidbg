# skill: tranif-contention（パスゲート競合 → X）

## いつ効くか
共有アナログノードに X が出る。抽出netlist(.v)に同じノードを駆動する `tranif`
(tranif1/tranif0) が複数あり、その制御が同時に導通している疑いがあるとき。

## 背景知識
`tranif` は双方向パスゲート。複数が同時に導通し、両側に異なる確定値
（St0 と St1 など）が来ると strength 競合になり、共有ノードは **X** になる。
アナログMUX/スイッチで頻出。`tranif` 自身に制御の良し悪しは無く、**制御は必ず
RTL 側にある**——だから真因は「同時導通させた制御ロジック」に遡れる。

## 手順（aidbg の道具で事実を集める。推論は最後）
1. `grep-log --severity ERROR`（必要なら `--pattern` で net名）で、X/glitch を報告
   している事象と**時刻 T**・対象ネット S を特定する。
2. `query --wave <W> --signal S --time T` で S が本当に X か、`--time` 無しで
   いつ X に落ちたかを確定する。
3. `grep-source --source <SRC> --pattern "tranif"` で netlist を読み、**S を端子に
   持つ tranif を列挙**する（同じノードに 2 つ以上あるか）。各 tranif の制御信号名と
   反対側の端子（入力）を控える。
4. 各 tranif の制御を `query --signal <ctrl> --time T` で読む。**複数が同時に 1
   （tranif1 なら導通）か**を確認。両側の入力値が異なれば競合が成立。
5. 導通している制御を `find-driver --source <SRC> --signal <ctrl>` で RTL の駆動箇所へ。
6. その file:line を `blame --source <SRC> --file <F> --line <N>` で
   「**誰のどのコミット**」に確定する。

## Design / Verification-env の判定
- 物理的に競合が成立（同ノードの tranif が複数導通＋両側に異なる確定値）→ **DESIGN**。
  制御RTLが誤って同時アサートしている。
- 制御は競合しておらず、X が 0 遅延レース/評価順由来に見える → これは tranif 競合では
  ない。`glitch-triage` の sim-artifact 判定に委ねる。

## 例（samples/fixture）
共有ノード **AOUT** に X。grep-source "tranif" で
`tranif1 (AOUT, IN0, SEL0)` と `tranif1 (AOUT, IN1, SEL1)` が AOUT を共有と判明。
reset 時刻に `query SEL0 --time T`→1、`query SEL1 --time T`→1（**同時導通**）、
入力は IN0=0 / IN1=1（衝突）→ strength 競合 → X。
`find-driver SEL0` → `rtl/ctrl.sv:14`、`blame ctrl.sv 14` → **Bob Hotfix / f5d5713**
（"force sel0/sel1 high during reset" という誤ったホットフィックス）。
→ 判定 **DESIGN**。
修正案（提案のみ）: リセット時は sel0/sel1 を**相互排他**にする（両方Highにしない）。
```
1. エラー: AOUT に X（glitch checker 発火）
2. 誰が: Bob Hotfix / commit f5d5713 / rtl/ctrl.sv:14
3. 真因: リセット中に SEL0/SEL1 を同時アサート → 2つの tranif1 が同時導通し
         IN0(0)/IN1(1) が AOUT で衝突 → strength 競合 → X
4. 修正案: reset 時の sel を相互排他に（提案のみ・適用しない）
```
