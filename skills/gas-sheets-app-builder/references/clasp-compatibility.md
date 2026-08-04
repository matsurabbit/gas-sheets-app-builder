# clasp互換性と環境準備

## 原則

- コマンド名を記憶で決めず、実際の`clasp --help`を調べる。
- グローバルインストールに依存せず、プロジェクトローカルの`@google/clasp`とlockfileで版を固定する。
- Node.jsは利用するclasp版の要件を満たすことを確認する。clasp v3はNode.js 20以降を必要とする。
- `.clasprc.json`は認証情報なので表示・コミットしない。`.clasp.json`はプロジェクト対応情報だが、意図したScript IDか必ず確認する。

既存プロジェクトにローカルclaspがなければ、既存のパッケージ構成を壊さないことを確認してから次を使う。

```text
npm install --save-dev @google/clasp
npm exec clasp -- --version
```

`scripts/clasp_preflight.py`へ実際の実行ファイルまたはランナーを渡す。

```text
python scripts/clasp_preflight.py -- node_modules/.bin/clasp
python scripts/clasp_preflight.py -- npm exec clasp --
```

Windowsでは`node_modules\.bin\clasp.cmd`を指定できる。出力されるJSONの`authenticated`と`commands`を以降の操作に使う。

## 主なコマンド差

| 目的 | clasp v3 | clasp v2 |
|---|---|---|
| ログイン確認 | `show-authorized-user` | `login --status` |
| 新規作成 | `create-script`（`create`別名もあり） | `create` |
| push対象確認 | `show-file-status` | `status` |
| Scriptを開く | `open-script` | `open` |
| コンテナを開く | `open-container` | `open --addon` |
| プロジェクト一覧 | `list-scripts` | `list` |

同じメジャー版でも別名やオプションが変わり得るため、表より事前診断結果を優先する。

## `--parentId`の正しい意味

`--parentId`は保存先Driveフォルダではない。作成するApps Scriptを既存のGoogle Sheets、Docs、Slides、FormsファイルへバインドするためのファイルIDである。

- 新規スプレッドシートも作る: `--type sheets --title "<アプリ名>"`を使う。作成後、Drive APIなどで指定フォルダへ移動する。
- 既存スプレッドシートへバインドする: `--parentId <既存スプレッドシートID> --title "<アプリ名>"`を使い、`--type`は付けない。
- DriveフォルダIDを`--parentId`へ渡さない。

作成前に`.clasp.json`、対象フォルダ、同名ファイルを確認する。作成後は出力からScript IDとコンテナIDを記録し、Driveの親フォルダをメタデータで確認する。

## 認可と起動確認

1. ログイン状態を読み取り専用コマンドで確認する。
2. 最小構成をpushする。
3. Drive移動・リネーム・参照シート読取に必要な専用の初期設定関数をApps Scriptエディタから実行する。
4. OAuth同意画面や未確認アプリの警告が出たらユーザー本人に引き継ぐ。
5. 認可後に初期設定関数を再実行し、Driveの親、名前、先頭タブ名を確認する。
6. コンテナを再読み込みしてメニューとUIを実機確認する。

ブラウザ操作では、直前にアドレスバーのファイルIDと記録済みIDが完全一致することを確認する。別タブや同名ファイルが見えている場合は操作を中止し、正しいURLを開き直す。
