# MicLock アーキテクチャ

## 全体構成図

```mermaid
graph TB
    subgraph Presentation["Presentation Layer (SwiftUI)"]
        MenuBar["MenuBarController<br/>アイコン表示・クイック操作"]
        Settings["SettingsViewModel<br/>設定編集・バリデーション"]
    end

    subgraph Application["Application Layer"]
        Engine["MicLockEngine<br/>監視開始/停止・補正ロジック"]
    end

    subgraph Domain["Domain Layer"]
        Rules["ビジネスルール<br/>音量ロック判定・エラー分類"]
    end

    subgraph Infrastructure["Infrastructure Layer"]
        AudioRepo["AudioDeviceRepository<br/>CoreAudioアクセス"]
        DeviceObs["DeviceObserver<br/>プロパティ変更リスナー"]
        Polling["PollingGuard<br/>周期監視バックアップ"]
        Config["ConfigStore<br/>UserDefaults永続化"]
        Logger["DiagnosticsLogger<br/>構造化ログ"]
        Launch["LaunchAtLoginManager<br/>SMAppService"]
    end

    MenuBar --> Engine
    Settings --> Engine
    Engine --> Rules
    Rules --> AudioRepo
    Engine --> DeviceObs
    Engine --> Polling
    Engine --> Config
    Engine --> Logger
    MenuBar --> Launch

    DeviceObs --> AudioRepo
    Polling --> AudioRepo

    subgraph States["状態遷移"]
        Idle["Idle<br/>待機"]
        Monitor["Monitoring<br/>監視中"]
        Correct["Correcting<br/>補正中"]
        Unsupport["Unsupported<br/>非対応"]
        Error["Error<br/>エラー"]
    end

    Idle -->|"ロックON"| Monitor
    Monitor -->|"音量ズレ"| Correct
    Correct --> Monitor
    Monitor -->|"非対応デバイス"| Unsupport
    Unsupport -->|"デバイス変更"| Monitor

    style Presentation fill:#e1f5ff
    style Application fill:#fff4e1
    style Domain fill:#f0e1ff
    style Infrastructure fill:#e8f5e9
    style States fill:#ffebee
```

## 状態遷移詳細図

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Monitoring: ロックON
    Monitoring --> Correcting: 音量ズレ検知
    Correcting --> Monitoring: 補正完了
    Monitoring --> Unsupported: 非対応デバイス
    Unsupported --> Monitoring: デバイス変更
    Monitoring --> Error: 一時エラー
    Error --> Monitoring: 自動リトライ
    Monitoring --> Idle: ロックOFF
    Unsupported --> Idle: ロックOFF
    Error --> Idle: ロックOFF
```

## コンポーネント構成

### Presentation Layer (SwiftUI)
| コンポーネント | 責務 |
|--------------|------|
| MenuBarController | メニューバーアイコン表示、クイックトグル、設定表示 |
| SettingsViewModel | 目標音量スライダー、監視間隔、epsilon、自動起動トグル |

### Application Layer
| コンポーネント | 責務 |
|--------------|------|
| MicLockEngine | 監視ライフサイクル、ドリフト検知、補正実行 |

### Domain Layer
| コンポーネント | 責務 |
|--------------|------|
| EngineState | 状態管理（Idle/Monitoring/Correcting/Unsupported/Error） |
| RuntimeStatus | 実行時ステータス（デバイス情報、エラー情報など） |
| VolumeDriftDetector | 音量ドリフト判定ロジック |
| MicLockError | エラー分類と回復可能判定 |

### Infrastructure Layer
| コンポーネント | 責務 |
|--------------|------|
| AudioDeviceRepository | デフォルト入力デバイス取得、音量読み書き、対応可否チェック |
| DeviceObserver | CoreAudio プロパティ変更のリスニング |
| PollingGuard | バックアップ用の定期ボリュームチェック |
| ConfigStore | UserDefaults 経由の設定保存/読み込み |
| DiagnosticsLogger | トラブルシューティング用構造化ログ |
| LaunchAtLoginManager | SMAppService 経由のログイン項目有効/無効 |

## データフロー

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant UI as MenuBarController
    participant Engine as MicLockEngine
    participant Repo as AudioDeviceRepository
    participant Obs as DeviceObserver
    participant CoreAudio as CoreAudio

    User->>UI: ロックON
    UI->>Engine: startMonitoring()
    Engine->>Repo: getDefaultInputDevice()
    Repo->>CoreAudio: デバイス取得
    CoreAudio-->>Repo: AudioDeviceID
    Repo-->>Engine: デバイス情報

    Engine->>Repo: canSetVolume()
    Repo-->>Engine: true/false

    alt 対応デバイス
        Engine->>Obs: startListening()
        Engine->>Engine: 状態→Monitoring

        loop ポーリング
            Engine->>Repo: getVolume()
            Repo-->>Engine: currentVolume
            Engine->>Engine: shouldCorrect()?
        end

        Obs->>CoreAudio: PropertyListener登録
        CoreAudio->>Obs: 音量変更イベント
        Obs->>Engine: onChange()
        Engine->>Repo: setVolume(target)
        Repo->>CoreAudio: 音量設定
    else 非対応デバイス
        Engine->>Engine: 状態→Unsupported
        Engine-->>UI: エラー通知
        UI-->>User: 「このマイクは音量固定に未対応」
    end
```

## 設定データモデル

```mermaid
classDiagram
    class AppSettings {
        +Bool isLockEnabled
        +Float targetVolume (0.0-1.0)
        +Double pollingIntervalSec
        +Float epsilon
        +Bool launchAtLogin
        +Date? pauseUntil
    }

    class RuntimeStatus {
        +AudioDeviceID? activeDeviceID
        +String? activeDeviceName
        +EngineState state
        +String? lastErrorCode
        +String? lastErrorMessage
        +Date? lastCorrectionAt
    }

    class EngineState {
        <<enumeration>>
        Idle
        Monitoring
        Correcting
        Unsupported
        Error
    }

    class MicLockError {
        <<enumeration>>
        deviceNotSupported
        permissionDenied
        deviceDisconnected
        unknown(Error)
    }

    AppSettings --> RuntimeStatus : 永続化・読み込み
    RuntimeStatus --> EngineState : 現在の状態
    RuntimeStatus --> MicLockError : エラー情報
```
