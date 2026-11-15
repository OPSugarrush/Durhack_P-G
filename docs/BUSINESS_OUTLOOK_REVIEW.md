# Business outlook review

## Brand analysis placement

Brand comparisons now live in Business outlook's Brands & companies subview, with a category selector. Category opportunities and individual findings contain only a contextual link when at least two brands have adequate comparable histories and brand coverage. Mixed baskets and missions do not receive those links. Findings no longer repeat generic action briefs; they focus on the selected observation, products and receipts. The business outlook retains category-level suggested actions. Shopper profiles retain individual summaries with links to histories. No new main navigation item or duplicate analysis pipeline was introduced.

## Visual hierarchy revision

Leading categories now ranks distinct recent buyers across all identified recent shoppers, including those without an earlier history. The following diverging chart separately shows paired purchase-frequency changes, with red decreases left of zero and green increases right. Both link to one selected category detail area.

Brand context uses one movement track per entity: grey earlier marker, coloured recent marker and connecting segment. The default highlights at most three movements of at least two percentage points, with five comparable category buyers and at least 70% recognised-brand row coverage. These are display gates, not statistical significance claims. Company comparisons require 70% owner coverage. Full comparisons and methodology are secondary links/expanders.

Category findings receive a separate Brand context section. Mixed baskets and shopping missions no longer automatically display every category's brands. Shopper profiles show individual behaviour summaries and contextual history links, with goals separated below. Dedicated history routes provide behaviour filters, shopper search, 12-per-page pagination and a contextual back link; they do not appear in main navigation. History counts match the changed-history or individual selection, not the complete category cohort.

The new reach test checks deduplication and inclusion of recent-only shoppers. `scripts/verify_outlook.cjs` checks the browser journey using the built-in sample, including mobile overflow. Earlier review details below describe the initial implementation where superseded by this section.

Changes remain local on `audit/hackathon-brief-gap-review`; no push requested.

The existing import, findings, exploratory observations and receipt drill-down remain. Import now opens Business outlook. Category bars show signed changes in trips per 100 across comparable buyers, not an invented investment score. Priority labels require 20 comparable buyers, 10 category buyers and the existing corrected directional and interval evidence. Monthly charts are descriptive and label their trip denominators.

Brand movements appear inside category details and existing finding evidence. Shopper profiles reuses this analysis for individual histories. Brands and owners are separate. Within-category comparisons use the same buyers with two category trips in both periods, equal buyer weights and distinct receipt counts. Multiple brands can appear in one trip, so these rates are not additive market shares. Known-brand and owner row coverage is visible.

A possible switch requires two category trips per period, full brand recognition and exactly one different repeatedly bought brand in each period. Same-owner changes are distinguished from different-owner changes. Unknown ownership remains unresolved. Retailer changes are flagged. Other histories are consistent purchasing, first observed trial, repeated trial, mixed buying or insufficient history. These labels describe observations, not proven preference or abandonment. The global midpoint is a comparison boundary, not an estimated switch date; dated receipt histories are shown.

Business actions remain investigation/experiment priorities. No monetary returns, causal promotion effects, seasonality adjustments or optimal budgets are estimated. Short histories and synthetic data cannot establish realised business impact. No new taxonomy/brand ownership claims were added.

Spending & goals is renamed Shopper profiles, headed Understanding the individual. Goals are collapsed under Explore a shopper goal. Existing category spending and price coverage remain available.

Verification: focused tests cover same-owner transitions, duplicate same-owner brands in a basket, unknown-brand abstention and spending arithmetic. JavaScript syntax checks cover all three browser modules. The previous full-workbook HTTP timeout remains a separate unresolved limitation; this change does not claim to fix it.
