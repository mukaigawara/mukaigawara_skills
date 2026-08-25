import type { CollectionEntry } from 'astro:content';

export type DocumentEntry = CollectionEntry<'documents'>;

export const categories = [
  {
    id: 'principles',
    label: 'Principles',
    title: '判断を導く原則',
    description: '状況が変わっても持ち越したい、判断の基準。',
  },
  {
    id: 'beliefs',
    label: 'Beliefs',
    title: '世界をどう捉えるか',
    description: 'AI、組織、技術、お金について現在信じていること。',
  },
  {
    id: 'frameworks',
    label: 'Frameworks',
    title: '考えるための型',
    description: '意思決定、優先順位、問題設定、学習に使う考え方。',
  },
  {
    id: 'essays',
    label: 'Essays',
    title: 'まとまった考察',
    description: '一つの問いを、背景と理由を含めて考えた文章。',
  },
  {
    id: 'decisions',
    label: 'Decisions',
    title: '選択と理由',
    description: '何を選び、何をやめ、どの条件で判断したか。',
  },
  {
    id: 'influences',
    label: 'Influences',
    title: '考え方への影響',
    description: '本、人、言葉から受け取ったもの。',
  },
  {
    id: 'changelog',
    label: 'Changelog',
    title: '思想の変化',
    description: '考えを変えた箇所と、その理由。',
  },
  {
    id: 'daily',
    label: 'Daily notes',
    title: '日々の根拠',
    description: '会話から抽出した、まだ分類前の思想と知識。',
  },
] as const;

export type CategoryId = (typeof categories)[number]['id'];

export function categoryIdFromEntry(entry: DocumentEntry): CategoryId {
  if (entry.id.startsWith('knowledge/daily/')) return 'daily';
  return entry.id.split('/')[0] as CategoryId;
}

export function entrySlug(entry: DocumentEntry): string {
  if (entry.id.startsWith('knowledge/daily/')) {
    return entry.id.replace('knowledge/daily/', 'daily/');
  }
  return entry.id;
}

export function entryTitle(entry: DocumentEntry): string {
  if (entry.data.title) return entry.data.title;
  return entry.id
    .split('/')
    .at(-1)!
    .replace(/^\d+[_-]/, '')
    .replaceAll('_', ' ');
}

export function entryDate(entry: DocumentEntry): Date | undefined {
  return entry.data.updated ?? entry.data.date;
}

export function sortEntries(entries: DocumentEntry[]): DocumentEntry[] {
  return [...entries].sort((left, right) => {
    const orderDifference = (left.data.order ?? 999) - (right.data.order ?? 999);
    if (orderDifference !== 0) return orderDifference;
    const leftDate = entryDate(left)?.getTime() ?? 0;
    const rightDate = entryDate(right)?.getTime() ?? 0;
    if (leftDate !== rightDate) return rightDate - leftDate;
    return entryTitle(left).localeCompare(entryTitle(right), 'ja');
  });
}

export function withBase(path = ''): string {
  const base = import.meta.env.BASE_URL.endsWith('/')
    ? import.meta.env.BASE_URL
    : `${import.meta.env.BASE_URL}/`;
  return `${base}${path.replace(/^\/+/, '')}`;
}
