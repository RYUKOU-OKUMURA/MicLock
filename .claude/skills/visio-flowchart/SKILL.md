---
name: visio-flowchart
description: Mermaidのシーケンス図記法からVisio風のモダンなフローチャート画像（PNG）を生成するスキル。ユーザーが「フローチャートを作って」「フロー図を画像で」「Mermaidからフローチャート画像を生成」「シーケンス図をVisio風に」「スイムレーン付きのフロー図」「業務フローを可視化」などと言ったら必ずこのスキルを使う。Mermaid記法がまだ提供されていない場合は、ユーザーの説明からMermaid記法を生成してからレンダリングする。
---

# Visio-style Flowchart Generator

Mermaidのシーケンス図（sequenceDiagram）記法を入力として受け取り、VisioのFlowchartテンプレート風のモダンなフローチャート画像（PNG）を生成する。

## ワークフロー

### 1. 入力の取得

ユーザーから以下のいずれかを受け取る：

- **Mermaid sequenceDiagram記法** → そのままパースへ進む
- **業務フローの自然言語説明** → Mermaid sequenceDiagram記法に変換してからパースへ進む
- **既存のMermaidファイル** → `/mnt/user-data/uploads/` から読み込む

### 2. Mermaid記法の準備

記法がまだない場合は、ユーザーの説明を分析して以下を特定する：

- **参加者（participant）**: 各アクター・システムを特定し、`participant` として定義
- **メッセージフロー**: 各ステップを `A ->> B: アクション` 形式に変換
- **条件分岐**: `alt / else / end` ブロックで表現
- **オプション処理**: `opt / end` ブロックで表現
- **ループ処理**: `loop / end` ブロックで表現
- **自己呼び出し**: `A ->> A: 内部処理` として表現

### 3. レンダリング実行

```bash
python scripts/render_flowchart.py input.mmd -o flowchart.png -t "タイトル"
```

**手順:**
1. Mermaid記法をテキストファイル（`.mmd`）として `/home/claude/` に保存
2. レンダリングスクリプトを実行
3. 出力PNGを `/mnt/user-data/outputs/` にコピー
4. `present_files` で提示

### 4. 出力の確認と調整

生成された画像を確認し、必要に応じて：
- 参加者の順序を変更
- ラベルテキストを短縮
- レイアウト定数（`BOX_WIDTH`, `BOX_VGAP` 等）を調整

## デザイン仕様

スクリプト `scripts/render_flowchart.py` に以下のデザインが組み込まれている：

| 要素 | スタイル |
|------|---------|
| 背景 | 淡いグレー #F7F7F7 |
| スイムレーン | 白背景、#CCCCCC 枠線 |
| ヘッダー | #4A90E2 背景、白テキスト |
| 一般プロセス | 白、#4A90E2 枠線、角丸 |
| 内部処理（自己呼び出し） | 淡いブルー #E8F1FF |
| 受信／入力（他participantから） | 淡いグリーン #E9F7EC |
| 条件分岐 | 菱形、#7B61FF 枠線 |
| 矢印 | ダークグレー #555555 |
| フォント | Noto Sans CJK / DejaVu Sans |

## 対応するMermaid構文

```
sequenceDiagram
    participant A as ユーザー
    participant B as サーバー
    A ->> B: リクエスト
    B ->> B: 内部処理
    B ->> A: レスポンス
    alt 条件
        B ->> A: 成功
    else エラー
        B ->> A: エラー通知
    end
    opt オプション処理
        A ->> B: 追加リクエスト
    end
    loop 繰り返し
        B ->> B: ポーリング
    end
    Note right of A: メモ
```

## アイコンの自動判定

参加者の名前・ラベルから適切なアイコンを自動割り当てする：

- **人物**: user, ユーザー, human, client, customer, operator
- **サーバー**: server, api, backend, service, system
- **AI**: ai, claude, gpt, llm, model, bot, agent
- **データベース**: db, database, store, storage
- **I/O**: input, output, file, upload, download
- **プロセス**: 上記に該当しないもの

## カスタマイズ

レンダリングスクリプトの定数を直接編集してカスタマイズ可能：

- `LANE_MIN_WIDTH`: スイムレーン幅（デフォルト 260px）
- `BOX_WIDTH` / `BOX_HEIGHT`: ボックスサイズ（200x56px）
- `BOX_VGAP`: ボックス間の垂直距離（50px）
- `FONT_SIZE_BOX`: テキストサイズ（15px、2x スケーリングで実質30px）
- `self.scale`: 解像度スケール（デフォルト 2x = 300dpi相当）

必要に応じてこれらの値をユーザーの要望に合わせて調整する。
