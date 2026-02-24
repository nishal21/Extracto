# Site Architecture & URL Mapping

## Current State
- `/docs/index.html` (Single monolithic page landing)

## Target State (Phase 1 → 5 Expansion)

```
docs/
├── index.html                  [Optimized Landing Page]
├── sitemap.xml                 [NEW: XML sitemap for SEs]
│
├── compare/                    [NEW: Comparison Hub (BoFu)]
│   ├── extracto-vs-apify.html
│   ├── extracto-vs-scrapegraphai.html
│   └── extracto-vs-scrapy.html
│
├── use-cases/                  [NEW: Industry Use Cases]
│   ├── ecommerce-scraping.html
│   ├── real-estate-scraping.html
│   └── news-scraping.html
│
└── blog/                       [NEW: Technical SEO Content]
    ├── index.html
    ├── scrape-javascript-onclick.html
    └── bypass-anti-bot-playwright.html
```

## Internal Linking Strategy
- The homepage `index.html` will contain a "Compare Extracto" footer linking to the `compare/` hub.
- The `use-cases/` will link deeply into the `/compare/` pages to drive bottom-of-funnel decision-making.
- The `index.html` navigation bar will be expanded to include `Use Cases`, `Comparisons`, and `Blog`.
