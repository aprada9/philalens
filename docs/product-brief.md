# Product Brief

## Problem

Large stamp collections are hard to inventory manually. Album page photos often contain many stamps, and each stamp may require identification across country, year, denomination, print variant, condition, and market context.

## Goal

Philalens helps convert album photos into a searchable, reviewable stamp inventory with candidate identifications and value estimates.

## Primary User

A collector or inheritor of a stamp collection who wants an initial understanding of what the collection contains and which stamps may deserve expert review.

## Inputs

- Batch album page photos, mostly HEIC for the first user collection.
- Optional manual notes.
- Optional catalog exports or user-provided reference data.

## Outputs

- Page-level detected stamps.
- Stamp-level candidate matches.
- Confidence scores and evidence.
- Estimated value range per stamp.
- Collection-level summary.
- Exportable CSV and JSON inventory.
- Local visualizer for page-by-page and stamp-by-stamp review.

## Core Product Position

Philalens should optimize for triage and evidence. The first valuable product is
not an exact appraisal engine; it is a workflow that separates common low-value
material from possible outliers, explains the evidence, and tells the user when
better images or expert review are needed.

The first implementation is local-first: it stores uploaded page images,
normalized derivatives, crop images, and SQLite project state on the user's
machine. The browser UI should support batch review and correction before later
AI description, matching, and valuation stages are trusted.

## Non-goals

- Replacing a professional philatelic appraisal.
- Guaranteeing exact catalog numbers without human review.
- Scraping or redistributing restricted catalog data without permission.

## Key Risks

- Similar stamp designs can differ by subtle perforation, watermark, paper, or overprint details.
- Cancellations and poor photo quality can hide critical features.
- Catalog and market data may be licensed, incomplete, or region-specific.
- Asking price is not the same as realized sale price.
- A front-side album photo cannot reliably assess gum, watermark, hidden thins,
  regumming, or many repairs.
