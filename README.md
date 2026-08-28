# skills

Claude Code、Codex、Cursor で使うスキルを保管するリポジトリです。

## 収録しているスキル

- [`daily-conversation-knowledge`](skills/daily-conversation-knowledge/)：ローカルのAI会話履歴から、公開できる思想の断片と再利用可能な知識だけを日次ノートへ整理する。
- [`human-thought`](skills/human-thought/)：人の思想を、世界観、信念、価値観、前提、原則、実践の関係として整理する知識スキル。
- [`ponytail`](skills/ponytail/)：怠惰なシニア開発者として、書かないことを最優先し、既存実装と最小差分で済ませる実装スキル。

## 構成

各スキルは `skills/<name>/` に置き、次の形をとります。

```
skills/<name>/
  SKILL.md              # 名前、説明、手順
  references/           # 判断が必要なときだけ読む詳細
  scripts/              # 決まった処理を行うスクリプト
  agents/openai.yaml    # 他エージェントから呼ぶときの表示設定
```

`SKILL.md` の frontmatter には `name` と `description` を書きます。
`description` には、何をするかに加えて、**どういうときに使い、どういうときに使わないか**を書きます。

詳細は `SKILL.md` に全部書かず、判断が必要な場面で読むものを `references/` へ分けます。

## 使い方

利用側のリポジトリから、必要なスキルのディレクトリを `.claude/skills/` へ配置するか、シンボリックリンクを張ります。

```bash
ln -s /path/to/mukaigawara_skills/skills/human-thought .claude/skills/human-thought
```

## 保存先について

スキルが生成する成果物は、このリポジトリではなく、用途ごとの別リポジトリへ保存します。

このリポジトリはスキルの定義だけを持ちます。
