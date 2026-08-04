# clasp互換性と環境準備

## 原則

- コマンド名を記憶で決めず、実際の`clasp --help`を調べる。
- グローバルインストールに依存せず、プロジェクトローカルの`@google/clasp`とlockfileで版を固定する。
- Node.jsは利用するclasp版の要件を満たすことを確認する。clasp v3はNode.js 20以降を必要とする。
- `.clasprc.json`は認証情報なので表示・コミットしない。`.clasp.json`はプロジェクト対応情報だが、意図したScript IDか必ず確認する。

## グローバルとローカルの使い分け

- Node.js本体とnpmはシステムPATH上のグローバル環境を使ってよい。
- npmのグローバルパッケージは、グローバルbinがPATHにあればCLIとして実行できる。ただしNode.jsの`import`/`require`は通常、グローバル`node_modules`を自動検索しない。
- `NODE_PATH`でグローバルモジュールを参照させる方法はあるが、PC固有のPATHと版に依存するため、このスキルでは使わない。
- `@google/clasp`はプロジェクトローカルの`devDependencies`へ固定し、`npm exec clasp -- ...`またはpackage scriptsから実行する。これによりlockfileから同じ版を再現できる。
- 既存プロジェクトが明示的にグローバルclaspを管理している場合は勝手に構成を変えず、事前診断で版とコマンド体系を確認して利用する。

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

## 指定フォルダへ直接作成する

`--parentId`は保存先Driveフォルダではない。作成するApps Scriptを既存のGoogle Sheets、Docs、Slides、FormsファイルへバインドするためのファイルIDである。

- Drive API `files.create`で`name`、`mimeType: application/vnd.google-apps.spreadsheet`、`parents: [<作業フォルダID>]`を同時に指定し、作業フォルダ直下へSheetを直接作る。
- 作成結果の`parents`を検証してから、`--parentId <作成したスプレッドシートID> --title "<アプリ名>"`でScriptをバインドする。`--type`は付けない。
- DriveフォルダIDを`--parentId`へ渡さない。
- `clasp create --type sheets`で別場所へ作ってから移動しない。直接作成できなければ停止する。

`scripts/create_bound_sheet_in_folder.mjs`はローカルclaspの認証を再利用して、この作成・親検証・バインドを連続実行する。作成前に`.clasp.json`、対象フォルダ、同名ファイルを確認する。作成後はScript ID、Sheet ID、親フォルダIDを記録する。

## 認可と起動確認

1. ログイン状態を読み取り専用コマンドで確認する。
2. 最小構成をpushする。
3. 参照シート読取に必要なUI非依存の認可関数をApps Scriptエディタから実行する。この関数には`getUi()`、`alert()`、ダイアログ表示を含めず、結果はreturn値やログで確認する。メニュー通知は別のラッパー関数へ分離する。
4. OAuth同意画面や未確認アプリの警告が出たらユーザー本人に引き継ぐ。
5. 認可後に設定関数を再実行し、名前と先頭タブ名を確認する。親フォルダは作成直後のDrive APIメタデータで確認する。
6. コンテナを再読み込みしてメニューとUIを実機確認する。

`onOpen()`はメニュー登録だけに限定し、認可が必要なサービスやファイル書き込みを呼ばない。再読み込み後もメニューが出ない場合は、対象スプレッドシートの「拡張機能 → Apps Script」から開いたエディタでScript IDを照合し、そのコンテナ文脈から`onOpen()`を一度実行する。

ブラウザ自動操作は既定で使わない。OAuth、Apps Scriptエディタでの関数実行、スプレッドシートUIの確認は正しいURLと手順をユーザーへ渡し、完了報告を待つ。ユーザーがその依頼でブラウザ自動操作を明示した場合だけ、操作直前にアドレスバーのファイルIDと記録済みIDが完全一致することを確認する。
