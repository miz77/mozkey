# MozKey macOS 個人配布

本人と身内向けの非公式・試験配布です。元作者による配布ではありません。
上流の変更と個人向けの調整を取り込んだforkから、daily辞書とZenzを含むPKGをビルドして配布します。
同梱llama-serverのprompt cacheは `--cache-ram 128` で128MiBに制限しています。
Developer ID署名・Appleの公証は行いません。

## インストール（公開後）

```sh
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
更新前には設定・ユーザー辞書・学習データをバックアップし、旧版パッケージを保持してください。

## 上流インストーラの挙動

- `/Applications/Mozc` と `/Library/Input Methods/Mozc.app` を削除して置き換えます。
- ログイン中ユーザーのMozc関連プロセスと `llama-server` を名前で終了します。
  別用途の同名プロセスも対象になる可能性があります。
- 既存Mozcとの同時利用を前提にしないでください。

## 検証状況と来歴

対応宣言はmacOS 12以降、Apple SiliconとIntelです。
上流由来のCIで、同じPKGに対する両CPUの検証とZenz scorerの動作試験を実行しています。
2026.09.06.1ではApple Siliconで日本語入力、削除・再導入、設定保持を確認しました。
2026.09.08.1では旧版からの更新、日本語入力、128MiBのcache設定と短時間のZenz動作を確認しました。
これらは過去版の限定的な検証です。各新版の結果は、そのReleaseの説明に記録します。
IntelでのGUI入力、Gatekeeperの許可手順、多日間のメモリ安定性は未検証です。
実行runとhashは `provenance.json`、記録は `audit/` を参照してください。
ライセンス類は `LICENSES/` と `THIRD_PARTY_NOTICES.md` に収録しています。

## 次版の準備

上流の採用commitを固定して同期用ブランチへマージし、fork内のPRでテストと両CPUのPKG検証を通します。
配布用ビルドには、マージ後の `main` で成功した `macos_zenz_formal_package_dual_native.yml` のrunを使います。
mainへのpushで成功したrunを利用できない場合は、新しいworkflow_dispatch runを作成します。
元リポジトリのActionsは実行しません。再実行attemptの混在を避け、新しいrunを作成します。
成功したrunからPKGと両CPUの検証記録を取得し、APIのrun・jobs・artifacts情報を
成果物フォルダの `metadata/{run,jobs,artifacts}.json` に保存します。

```sh
python3 tools/packaging/prepare_macos_release.py \
  --artifacts /absolute/path/to/run-artifacts \
  --upstream-commit e9b464f6c4f7c9705617af653237bbb25f97310d \
  --version 2026.09.22.1 --output /absolute/path/to/release
```

ソースcheckoutは採用ビルドのcommitに合わせます。
`--upstream-commit` はそのビルドに取り込んだ上流の完全なSHAに置き換えてください。
上流のSHAとforkのビルドSHAは `provenance.json` に別々に記録されます。
新しい配布番号でdraft Releaseを作り、公開後に個人tapを更新します。
PKGを再ビルド・再署名して同じ版のassetを置き換えません。
