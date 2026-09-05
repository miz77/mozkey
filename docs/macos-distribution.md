# MozKey macOS 個人配布

本人と身内向けの非公式・試験配布です。元作者による配布ではありません。
daily辞書とZenzを含む上流のPKGを変更せず配布します。
Developer ID署名・Appleの公証は行いません。

## インストール（公開後）

```sh
brew tap miz77/mozkey
brew install --cask miz77/mozkey/mozkey
```

管理者認証が必要です。既存Mozcは置き換わります。
システム設定の「キーボード」→「テキスト入力」→「編集」で日本語のMozcを追加してください。
表示されない場合や更新後は、作業を保存してログアウト・ログインしてください。
未署名のためmacOSで許可操作が必要になる場合があります。実機での操作手順は未検証です。
この配布では隔離属性の自動除去やGatekeeper設定の変更はしません。

## 更新・削除

```sh
brew update
brew upgrade --cask miz77/mozkey/mozkey
brew uninstall --cask miz77/mozkey/mozkey
```

更新・削除の前に入力ソースをABCなどへ切り替えてください。
削除はPKGのreceiptに対応するファイルを対象とし、ユーザー辞書・学習・設定の削除は指示しません。
`--zap` によるユーザーデータ削除は用意しません。
初回は旧版からの更新・削除・ユーザーデータ保持の実機試験が未実施です。

## 上流インストーラの挙動

- `/Applications/Mozc` と `/Library/Input Methods/Mozc.app` を削除して置き換えます。
- ログイン中ユーザーのMozc関連プロセスと `llama-server` を名前で終了します。
  別用途の同名プロセスも対象になる可能性があります。
- 既存Mozcとの同時利用を前提にしないでください。

## 検証状況と来歴

対応宣言はmacOS 12以降、Apple SiliconとIntelです。
上流由来のCIで、同じPKGに対する両CPUの検証とZenz scorerの動作試験を実行しています。
GUIでの日本語入力、通常の取得経路でのGatekeeper挙動、更新・削除は未検証です。
実行runとhashは `provenance.json`、記録は `audit/` を参照してください。
ライセンス類は `LICENSES/` と `THIRD_PARTY_NOTICES.md` に収録しています。

## 次版の準備

ビルドは `miz77/mozkey` の `macos_zenz_formal_package_dual_native.yml` を手動実行します。
元リポジトリのActionsは実行しません。再実行attemptの混在を避け、新しいrunを作成します。
成功したrunからPKGと両CPUの検証記録を取得し、APIのrun・jobs・artifacts情報を
成果物フォルダの `metadata/{run,jobs,artifacts}.json` に保存します。

```sh
python3 tools/packaging/prepare_macos_release.py \
  --artifacts /absolute/path/to/run-artifacts \
  --version 2026.09.06.1 --output /absolute/path/to/release
```

ソースcheckoutは採用ビルドのcommitに合わせます。
新しい配布番号でdraft Releaseを作り、公開後に個人tapを更新します。
PKGを再ビルド・再署名して同じ版のassetを置き換えません。
