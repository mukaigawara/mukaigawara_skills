#!/usr/bin/env node
// 公開している思想の文書が、結論・適用条件・理由を伴っているかを測る。
// 判定は文体の良し悪しではなく、思想として再利用できる形かどうかだけを見る。

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/\/$/, '');

// 思想を蓄積するカテゴリ。changelog と daily は記録であり、同じ基準で測らない。
const THOUGHT_DIRS = ['principles', 'beliefs', 'frameworks', 'essays', 'decisions', 'influences'];
const RECORD_DIRS = ['changelog', 'knowledge/daily'];

const CONDITION_MARKERS = ['とき', 'なら', '場合', 'かぎり', '限り', 'ただし', '一方', 'に対して', '以外'];
// 「会話から抽出」のような単なる起点を理由と数えないため、助詞の「から」単体は含めない。
const REASON_MARKERS = ['ため', 'なぜ', '理由', 'ではなく', 'によって', 'ことで', 'からである', 'だから'];

// カテゴリごとに、公開に足ると言える形が違う。
// 原則・信念・型は別の場面へ持ち出すものなので適用条件を要る。
// 決定と影響は一つの出来事を記録するものなので、選択と理由が揃えばよい。
const THRESHOLDS = {
  principles: { claims: 6, conditions: 1, reasons: 1 },
  beliefs: { claims: 6, conditions: 1, reasons: 1 },
  frameworks: { claims: 6, conditions: 1, reasons: 1 },
  essays: { claims: 10, conditions: 1, reasons: 1 },
  decisions: { claims: 3, conditions: 0, reasons: 1 },
  influences: { claims: 3, conditions: 0, reasons: 1 },
};

const VERDICTS = {
  空: { level: 0, note: '主張がほぼない。公開しても読む理由がない。' },
  骨組み: { level: 1, note: '結論はあるが、適用条件か理由が足りない。' },
  育成中: { level: 2, note: '結論と、条件または理由が揃っている。' },
  公開に足る: { level: 3, note: '結論・適用条件・理由が揃っている。' },
};

const STATUS_REQUIRES = { draft: 0, evolving: 2, published: 3 };

function walk(dir) {
  const absolute = join(ROOT, dir);
  let entries;
  try {
    entries = readdirSync(absolute);
  } catch {
    return [];
  }
  return entries.flatMap((name) => {
    const path = join(absolute, name);
    if (statSync(path).isDirectory()) return walk(join(dir, name));
    return name.endsWith('.md') ? [join(dir, name)] : [];
  });
}

function parseFrontmatter(raw) {
  const match = raw.match(/^---\n([\s\S]*?)\n---\n?/);
  if (!match) return { data: {}, body: raw };
  const data = {};
  for (const line of match[1].split('\n')) {
    const pair = line.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (pair) data[pair[1]] = pair[2].trim().replace(/^["']|["']$/g, '');
  }
  return { data, body: raw.slice(match[0].length) };
}

// 見出し、コードブロック、リンク記法は主張の本体ではないため落とす。
function proseOf(body) {
  return body
    .replace(/```[\s\S]*?```/g, '')
    .split('\n')
    .filter((line) => !/^\s*#{1,6}\s/.test(line))
    .map((line) => line.replace(/^\s*(?:[-*+]|\d+\.)\s+/, '').replace(/^\s*>\s?/, ''))
    .join('\n')
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1');
}

function measure(body) {
  const sentences = proseOf(body)
    .split(/[。\n]/)
    .map((sentence) => sentence.trim())
    .filter((sentence) => sentence.length >= 12);

  const claims = sentences.filter((sentence) => !/[かカ]$/.test(sentence));
  const questions = sentences.filter((sentence) => /[かカ]$/.test(sentence));
  const text = claims.join('。');

  const conditions = CONDITION_MARKERS.filter((marker) => text.includes(marker)).length;
  const reasons = REASON_MARKERS.filter((marker) => text.includes(marker)).length;

  return { claims: claims.length, questions: questions.length, conditions, reasons };
}

function verdictOf({ claims, conditions, reasons }, category) {
  const threshold = THRESHOLDS[category] ?? THRESHOLDS.principles;
  if (claims <= 1) return '空';
  if (claims >= threshold.claims && conditions >= threshold.conditions && reasons >= threshold.reasons) {
    return '公開に足る';
  }
  if (claims >= Math.max(2, Math.ceil(threshold.claims / 2)) && conditions + reasons >= 1) return '育成中';
  return '骨組み';
}

// タイトルから、日次ノートを引くための語幹を作る。
function stemOf(title) {
  return title
    .replace(/^\d+[_-]/, '')
    .replace(/(について|とは何か|とは|の仕方|の付け方|の捉え方|の基準|の選び方)$/, '')
    .trim();
}

function main() {
  const asJson = process.argv.includes('--json');

  const dailyNotes = walk('knowledge/daily').map((path) => ({
    path,
    text: readFileSync(join(ROOT, path), 'utf8'),
  }));

  const pages = THOUGHT_DIRS.flatMap(walk).map((path) => {
    const { data, body } = parseFrontmatter(readFileSync(join(ROOT, path), 'utf8'));
    const title = data.title ?? path.split('/').at(-1).replace(/\.md$/, '');
    const category = path.split('/')[0];
    const metrics = measure(body);
    const verdict = verdictOf(metrics, category);
    const status = data.status ?? 'published';
    const stem = stemOf(title);
    const evidence = stem.length >= 2 ? dailyNotes.filter((note) => note.text.includes(stem)).length : 0;

    const required = STATUS_REQUIRES[status] ?? 3;
    const level = VERDICTS[verdict].level;

    return {
      path,
      title,
      category,
      status,
      verdict,
      ...metrics,
      evidence,
      // 公開状態が実質を上回っている状態だけを失敗として扱う。
      overstated: level < required,
      promotable: level > required && level >= 2,
    };
  });

  const records = RECORD_DIRS.flatMap(walk);
  const overstated = pages.filter((page) => page.overstated);
  const promotable = pages.filter((page) => page.promotable);
  const growable = pages
    .filter((page) => page.verdict === '空' || page.verdict === '骨組み')
    .sort((left, right) => right.evidence - left.evidence || left.path.localeCompare(right.path));

  if (asJson) {
    console.log(JSON.stringify({ pages, records: records.length, overstated, promotable, growable }, null, 2));
    return process.exit(overstated.length > 0 ? 1 : 0);
  }

  const width = Math.max(...pages.map((page) => page.path.length));
  console.log(`思想の文書 ${pages.length} 件 / 記録 ${records.length} 件\n`);
  console.log(
    `${'ファイル'.padEnd(width)}  ${'状態'.padEnd(10)} ${'判定'.padEnd(10)} 主張 問い 条件 理由 根拠`,
  );
  console.log('-'.repeat(width + 46));
  for (const page of [...pages].sort((left, right) => left.path.localeCompare(right.path))) {
    const flag = page.overstated ? ' ← 過大' : page.promotable ? ' ← 昇格可' : '';
    console.log(
      `${page.path.padEnd(width)}  ${page.status.padEnd(10)} ${page.verdict.padEnd(8)} ` +
        `${String(page.claims).padStart(3)} ${String(page.questions).padStart(4)} ` +
        `${String(page.conditions).padStart(4)} ${String(page.reasons).padStart(4)} ` +
        `${String(page.evidence).padStart(4)}${flag}`,
    );
  }

  if (growable.length > 0) {
    console.log('\n## 今回育てる候補（根拠の多い順）\n');
    for (const page of growable.slice(0, 5)) {
      console.log(`- ${page.title}（${page.path}）根拠 ${page.evidence} 件 / ${VERDICTS[page.verdict].note}`);
    }
  }

  if (promotable.length > 0) {
    console.log('\n## 昇格を検討できるページ\n');
    for (const page of promotable) {
      console.log(`- ${page.title}（${page.path}）status: ${page.status} → 実質は「${page.verdict}」`);
    }
  }

  if (overstated.length > 0) {
    console.log('\n## 公開状態が実質を上回っている（要修正）\n');
    for (const page of overstated) {
      console.log(`- ${page.path}：status: ${page.status} だが実質は「${page.verdict}」。${VERDICTS[page.verdict].note}`);
    }
    console.log('\nstatus を下げるか、結論・適用条件・理由を書き足す。');
    return process.exit(1);
  }

  console.log('\n公開状態が実質を上回っているページはない。');
  return process.exit(0);
}

main();
