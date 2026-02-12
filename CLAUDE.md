# CLAUDE.md

このファイルは、本リポジトリで作業する Claude Code (claude.ai/code) へのガイドを提供します。

## プロジェクト概要

**MicLock** は、ユーザーが指定したマイク入力音量を維持する macOS アプリケーションです。外部アプリやシステム変更で音量が変動しても、目標値へ自動的に復元します。

- **対象プラットフォーム**: macOS（最新安定版）
- **対象ユーザー**: 会議/配信時に安定したマイク音量が必要な非エンジニア
- **主要インターフェース**: メニューバー（MenuBarExtra）- Dockアイコンは不要

## アーキテクチャ（Clean Architecture + SwiftUI）

```
┌─────────────────────────────────────────────────────────────────┐
│                     Presentation Layer                          │
│              (SwiftUI + MenuBarExtra)                           │
│  - MenuBarController: アイコン状態表示、クイック操作            │
│  - SettingsViewModel: 設定編集・バリデーション                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                            │
│           (状態管理、ユースケース実行)                           │
│  - MicLockEngine: 監視開始/停止、補正ロジック                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Domain Layer                                │
│     (ビジネスルール、音量ロック判定、エラー分類)                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                           │
│  - AudioDeviceRepository: CoreAudio アクセス                    │
│  - DeviceObserver: デバイス/音量変更イベント                     │
│  - PollingGuard: 周期監視のバックアップ                         │
│  - ConfigStore: UserDefaults への永続化                        │
│  - DiagnosticsLogger: os.Logger 構造化ログ                      │
│  - LaunchAtLoginManager: SMAppService 自動起動                  │
└─────────────────────────────────────────────────────────────────┘
```

## ステートマシン

```
Idle ──(ロックON)──> Monitoring ──(音量ズレ)──> Correcting ──> Monitoring
                     │
                     └──(非対応デバイス)──> Unsupported ──(再試行/デバイス変更)──> Monitoring
```

**状態**: `Idle`（待機）, `Monitoring`（監視中）, `Correcting`（補正中）, `Unsupported`（非対応）, `Error`（エラー）

## 技術スタック

- **言語**: Swift（最新安定版）
- **UI**: SwiftUI (`MenuBarExtra`)
- **音声制御**: CoreAudio / AudioToolbox
- **ログ**: OSLog (`Logger`)
- **自動起動**: ServiceManagement (`SMAppService`)
- **永続化**: UserDefaults
- **テスト**: XCTest

## 監視戦略（ハイブリッドアプローチ）

1. **メイン**: `AudioObjectAddPropertyListenerBlock` による即時検知
2. **バックアップ**: 500ms ポーリング（設定可能）で取りこぼし防止
3. **補正条件**: `abs(current - target) > epsilon`
4. **補正順序**: マスチャンネル → 個別チャンネル（フォールバック）
5. **非対応デバイス処理**: `Unsupported` 状態へ遷移、ユーザーにわかりやすいメッセージ表示

## コンポーネントの責務

| コンポーネント | 責務 |
|--------------|------|
| `MenuBarController` | メニューバーアイコン表示、クイックトグル、設定表示 |
| `SettingsViewModel` | 目標音量スライダー、監視間隔、epsilon、自動起動トグル |
| `MicLockEngine` | 監視ライフサイクル、ドリフト検知、補正実行 |
| `AudioDeviceRepository` | デフォルト入力デバイス取得、音量読み書き、対応可否チェック |
| `DeviceObserver` | CoreAudio プロパティ変更のリスニング |
| `PollingGuard` | バックアップ用の定期ボリュームチェック |
| `ConfigStore` | UserDefaults 経由の設定保存/読み込み |
| `DiagnosticsLogger` | トラブルシューティング用構造化ログ |
| `LaunchAtLoginManager` | `SMAppService` 経由のログイン項目有効/無効 |

## データモデル

```swift
// AppSettings（永続化）
struct AppSettings {
    var isLockEnabled: Bool           // ロック有効/無効
    var targetVolume: Float           // 0.0...1.0（既定: 0.8）
    var pollingIntervalSec: Double    // 既定: 0.5
    var epsilon: Float                // 許容差閾値
    var launchAtLogin: Bool           // ログイン時自動起動
    var pauseUntil: Date?             // 一時停止期限
}

// RuntimeStatus（メモリ上）
struct RuntimeStatus {
    var activeDeviceID: AudioDeviceID?    // アクティブデバイスID
    var activeDeviceName: String?         // アクティブデバイス名
    var state: EngineState                // 現在の状態
    var lastErrorCode: String?             // 最後のエラーコード
    var lastErrorMessage: String?          // 最後のエラーメッセージ
    var lastCorrectionAt: Date?            // 最後の補正日時
}
```

## 実装ロードマップ

### Phase 1: MVP（2-4日）
- コア音量ロック（イベント + ポーリング）
- メニューバーUI（ON/OFF、目標音量、状態表示）
- UserDefaults 永続化
- 自動起動 ON/OFF

### Phase 2: 運用強化（2-3日）
- エラーメッセージ改善、診断情報コピー
- 一時停止機能
- 通知抑制・再試行ポリシー実装

### Phase 3: 配布品質（1-2日）
- コード署名/Notarization（必要時）
- 初回ガイド改善
- リリースノートテンプレート整備

## 設計原則（非エンジニア向け開発）

1. **UIファースト**: ユーザー操作はすべてUI経由；CLIはデバッグ用途のみ
2. **次のアクションを常に表示**: 失敗時に「何をすべきか」を提示
3. **最小限の設定**: 強力な既定値、少ない設定項目
4. **モジュール化されたロジック**: AIが理解・修正しやすい構造

## エラーハンドリング方針

- ユーザー向けエラー（平易な言葉）と開発者向けログ（詳細）を分離
- 重複するエラー通知を抑制（スパム防止）
- 回復可能エラーは自動再試行、回復不能エラーは明示的に停止

## 外部依存ライブラリ

- **v1**: 標準フレームワークのみ（外部パッケージなし）
- 理由: 非エンジニア開発者の保守負担を軽減

## 配布

- **v1**: ローカル `.app` ビルド配布
- **v1.1+**: コード署名・Notarization で初回起動警告を抑制

## CoreAudio の注意点

CoreAudio APIは可変長構造体とunsafeポインタを使用します。これらは薄い抽象化レイヤーでラップし、変更時にはユニットテストとハードウェア検証を必須としてください。

主要API: `AudioObjectAddPropertyListenerBlock`（イベント駆動の音量変更検知）
