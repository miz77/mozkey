# macOS配布の第三者表示

上流の著作権・ライセンス全文は `LICENSES/MozKey-Mozc.txt`、
完成PKG内の第三者表示は `LICENSES/credits_en.html` にそのまま収録しています。
Zenzとllama.cppの表示は `LICENSES/ZenzRuntime/` に収録しています。
その中の上流文書にあるMSIやDLLの記載は上流文書のまま保存したもので、
このmacOS配布はPKG、`llama-server` とUniversal Mach-Oを使用しています。
モデルとruntimeの正確なrevision・hashは `provenance.json` に記録しています。

## Qt

同梱Qt frameworkは6.9.1です。Qtのライセンス表示は上記creditsに含まれます。
ビルド元はqtbase-everywhere-src-6.9.1.tar.xzで、上流build_qt.pyによる
qyieldcpu.hのパッチを適用する構成です。対応ソース資料は同じReleaseの
`MozKey-macOS-Corresponding-Source-2026.09.06.1.zip` に添付します。
Qtの元アーカイブ、適用後のqyieldcpu.h、ビルドスクリプトを含むMozKeyの採用ソースを収録します。
参照: https://download.qt.io/archive/qt/6.9/6.9.1/submodules/qtbase-everywhere-src-6.9.1.tar.xz

## daily辞書

`LICENSES/UPSTREAM_THIRD_PARTY_NOTICES.md` の辞書別の説明を保存しています。
コードのライセンスが生成辞書データ全体に適用されるとは主張しません。
元workflowは動的入力のrevision・hashを成果物に保存していないため、
今回使用した入力の版は不明です。現在の配布元の版を代入していません。
Nico/Pixiv等の生成データの再配布条件について、上流にも確認を要する旨の記載があります。
このdraftを一般取得可能なpre-releaseにする前に、この未確認点を整理します。

この文書はライセンス表示と既知の確認状況の記録です。
