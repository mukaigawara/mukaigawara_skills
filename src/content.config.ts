import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const documents = defineCollection({
  loader: glob({
    pattern: [
      'principles/**/*.md',
      'beliefs/**/*.md',
      'frameworks/**/*.md',
      'essays/**/*.md',
      'decisions/**/*.md',
      'influences/**/*.md',
      'changelog/**/*.md',
      'knowledge/daily/**/*.md',
    ],
    base: '.',
  }),
  schema: z.object({
    title: z.string().optional(),
    description: z.string().optional(),
    order: z.number().int().nonnegative().optional(),
    status: z.enum(['draft', 'evolving', 'published']).default('published'),
    date: z.coerce.date().optional(),
    updated: z.coerce.date().optional(),
    visibility: z.literal('public').optional(),
  }),
});

export const collections = { documents };
