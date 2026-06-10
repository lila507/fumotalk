


# 🎙️ SakuFumo — 让 Fumo 说话的油库里语音合成工具

**SakuFumo** 是一个输入中文（可混合英文、数字）→ 自动转换为日语片假名空耳 → 调用 AquesTalk10 引擎生成油库里（ゆっくり）语音 → 输出 WAV / 直接播放的工具。目标是驱动藏在 Fumo 棉花玩偶里的蓝牙音箱，让灵梦、魔理沙真的开口说话。

> **FumoTalk** は、中国語（英単語・数字混じり可）→ 片仮名の空耳へ自動変換 → AquesTalk10 エンジンでゆっくり音声を合成 → WAV出力 / 再生 するツールです。Fumo ぬいぐるみの中の Bluetooth スピーカーを駆動して、霊夢や魔理沙に本当にしゃべらせるのが目標です。

---

## 🧠 工作原理 / しくみ

```
中文文本（可含英文/数字）
  ↓ pypinyin 分词 + 拼音转换
  ↓ mapping.tsv 拼音→片假名映射
  ↓ 罗马音→片假名（内建贪心匹配）
  ↓ 数字→逐字朗读（イチ・ニ・サン…）
  ↓ 安全过滤（只保留假名+日文标点）
  ↓ AquesTalk_Synthe_Utf8 (DLL)
  ↓ 16kHz 16bit WAV
  ↓ winsound 播放 / 写入 output.wav
```

**示例 / 例：**

| 输入 Input | 空耳 Kana | 
|------------|-----------|
| `你好世界` | `ニーハオシージエ` |
| `fumo 可爱` | `フモコーアイ` |
| `love you 114514` | `ロベヨウイチイチヨンゴイチヨン` |
| `輝夜のトラペゾヘドロン` | (日文原样保留) |

---

## 文件结构 / ファイル構成

```
fumotalk/
├── sakufumo.py          ← 主程序（中文→空耳→合成→播放）
├── mapping.tsv          ← 拼音→片假名映射表 (pinyin-to-kana)
├── lib64/
│   ├── AquesTalk.dll    ← AquesTalk10 64位 DLL（評価版）
│   ├── AquesTalk.h      ← C 头文件
│   └── AquesTalk.lib
├── output.wav           ← 每次运行自动生成
├── aqtk10_win_man.pdf   ← AquesTalk10 使用マニュアル
├── siyo_onseikigou.pdf  ← 音声記号列仕様
└── README.md            ← 本文件
```

---

## 快速开始 / クイックスタート

### 依赖 / 必要なもの

- Python 3.9+ (64bit)
- Windows（AquesTalk DLL 为 Windows 版）

```bash
pip install pypinyin
```

其餘依賴均為 Python 標準庫（`ctypes`, `wave`, `winsound` 等）。

### 运行 / 実行

```bash
cd fumotalk
python sakufumo.py
```

```
可用声種: f1(灵梦) f2(魔理沙) f3(ゆっくり) m1 m2 r1 r2
支持：中文 / 英文(罗马音) / 日文假名 / 数字 混合输入
请输入文本: 你好我是灵梦，赛钱箱里怎么只有5円？
声種 (默认f1):
```

---

## 声種一览 / 音声プリセット

| 代号 | 角色 | bas | spd | vol | pit | acc | lmd | fsc |
|------|------|-----|-----|-----|-----|-----|-----|-----|
| `f1` | 霊夢 | F1E(0) | 100 | 100 | 100 | 100 | 100 | 100 |
| `f2` | 魔理沙 | F2E(1) | 100 | 100 | 77 | 150 | 100 | 100 |
| `f3` | ゆっくり | F1E(0) | 80 | 100 | 100 | 100 | 61 | 148 |
| `m1` | 男声 M1 | M1E(2) | 100 | 100 | 30 | 100 | 100 | 100 |
| `m2` | 男声 M2 | M1E(2) | 105 | 100 | 45 | 130 | 120 | 100 |
| `r1` | ロボット R1 | M1E(2) | 100 | 100 | 30 | 20 | 190 | 100 |
| `r2` | ロボット R2 | F2E(1) | 70 | 100 | 50 | 50 | 50 | 180 |

---

## 评测版限制 / 評価版の制限

本リポジトリに含まれる `AquesTalk.dll` は**評価版**です。  
合成された音声の末尾に「**あくえり**」という評価版であることを示す音声が付加されます。

开发许可证（開発ライセンスキー）を購入することで、この制限は解除されます。  
详见 / 詳細： [AQUEST ライセンスページ](https://www.a-quest.com/license.html)

---

## 许可证 / ライセンス

### AquesTalk10 SDK

AquesTalk10 は (株)アクエストの著作物です。  
本 SDK の評価版は、事前評価の目的に限り複製及び利用できます。

- 本 SDK の全部または一部を、当社の許可なく再配布・公開することを禁じます。
- 本 SDK 内のファイルの改変（ファイル名の変更を含む）を禁じます。

当社製品ライセンスには以下の 3 種類があります：

| ライセンス | 説明 |
|------------|------|
| **開発ライセンス** | 本ライブラリを使うアプリや製品を開発する際に必要 |
| **使用ライセンス** | 本ライブラリを実行する際に必要（エンドユーザー向け） |
| **頒布ライセンス** | 本ライブラリを含むアプリを第三者に配布する際に必要 |

### 本プロジェクトのコード部分

`sakufumo.py` および `mapping.tsv` は、元プロジェクト [Love-Kogasa/zh-yukuuri](https://github.com/Love-Kogasa/zh-yukuuri) および [pinyin-to-kana](https://www.npmjs.com/package/pinyin-to-kana) の派生成果物です。

---

## 関連リンク

| 項目 | URL |
|------|-----|
| AQUEST 公式 | [https://www.a-quest.com/](https://www.a-quest.com/) |
| お問い合わせ | infoaq@a-quest.com |
| pinyin-to-kana | [npmjs.com/package/pinyin-to-kana](https://www.npmjs.com/package/pinyin-to-kana) |

---

## 🗺️ ロードマップ / Roadmap

- [x] 中文→空耳変換エンジン
- [x] 英文（罗马音）→片假名贪心匹配
- [x] 数字逐字朗读
- [x] 长文本自动分块合成
- [x] 7 種声種切换
- [ ] 音声入力（マイク → STT）連携
- [ ] AI 会話生成（DeepSeek API 接続）
- [ ] Android アプリ化（PWA / APK）
- [ ] サーバー構築（API 課金 + ユーザー管理）

---

> *「賽銭箱に 114514 円しか入ってない……これはひどいわね~」* — 霊夢 (f1)


