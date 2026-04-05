# Business Brief for Claude Code
## Owner: Adam Mowafi | Company: Story Unheard LTD

---

## Who You Are Working With

Adam runs two e-commerce brands out of the UK, both fulfilled via a 3PL warehouse under **Story Unheard LTD**. He also runs a video production agency with a large editing team. Adam's wife is involved in the creative direction of both brands. His working style is exploratory before committing — he asks questions first, corrects errors directly, and prefers copy-paste ready outputs he can action immediately. He is based in Giza/Cairo but operating UK-facing brands.

---

## BRAND 1: CAICO COTTON

### What It Is
- **Website:** caicocotton.com (Shopify)
- **Also selling on:** Amazon UK (pending), Etsy (being set up)
- **Shopify store ID:** caico-cotton.myshopify.com
- **Product:** Premium baby and children's clothing, 100% GOTS-certified organic Egyptian cotton (extra-long staple fibres). Sizes from Newborn to Kids (approx 0–6 years).
- **USP:** 100% Egyptian cotton — genuinely superior to competitors like MORI who use 70% bamboo viscose blend. GOTS certified. Hypoallergenic.
- **Price range:** ~£22–£65 per piece
- **Positioning:** UK DTC brand, affordable premium. Compete with MORI but at a comparable price point. Do NOT undercut — price signals quality.
- **Fulfilment:** 3PL warehouse (Story Unheard LTD), UK stock
- **History:** Adam purchased the brand from previous Egyptian owners who sold direct from Egypt. He repositioned it as a UK DTC brand with UK stock.

### Products & SKUs
- ~80–100 active SKUs across Shopify and warehouse
- 192 total in the Amazon catalogue file (parent-child relationships)
- **Colour range:** Alabaster (white), Dusky Blue, Dusty Blush, Sage, Cotton Bloom (print), Rocky (grey)
- **Product types:** Crossover (wrapover) bodysuits, short sleeve bodysuits, long sleeve bodysuits, leggings, bloomers, kimono jumpsuits, pyjama sets, lounge tees, lounge blouse, muslin dress, baby bonnet, mittens, baby blanket
- **Key SKU note:** Bonnets and mittens are ONE-SIZE in the warehouse but split into size variants on Shopify

### Inventory & Warehouse
- Warehouse file: Story_Unheard_Stock_Report (regularly updated .xlsx)
- 8 Shopify corrections previously identified (zero-stock items set to 0):
  - Crossover Bodysuit Dusky Blue NB → 0
  - Crossover Bodysuit Dusky Blue 1-3M → 0
  - Crossover Bodysuit Dusty Blush NB → 0
  - Crossover Bodysuit Dusty Blush 1-3M → 0
  - Bonnet Cotton Bloom 3-6M → 0
  - Mittens Cotton Bloom 3-6M → 0
  - Muslin Dress Grey 18-24M → 0
  - Lounge Tee Dusty Blush 4-5Y → 0
- Warehouse is the source of truth for stock, not Shopify

### SEO & Metadata Strategy (Finalised)
- **Title tag pattern:** "World's Softest [Product] — Organic Egyptian Cotton | Caico Cotton"
- **Meta description pattern:** Opens with "UK brand," closes with "Free UK delivery over £50"
- **Six pages covered:** Homepage, Newborn Collection, Baby Collection, Toddler Collection, Kids Collection, Why Organic Egyptian page
- Shopify Sidekick prompt has been prepared for implementation

### Shopify MCP Connection
- Connected via terminal: `npx shopify-mcp --accessToken [TOKEN] --domain caico-cotton.myshopify.com`
- MCP server name: `shopify`
- Shopify Admin API scopes: read/write products, themes, content

### Amazon UK Status
- Attempted launch with 192-SKU flat file (UK apparel template)
- Issues resolved: template validation errors, browse nodes, brand name (was showing "Generic"), EAN barcodes
- **Brand Registry block:** "Caico Cotton" was registered by previous owner on Amazon. Resolution: trademark application via Amazon IP Accelerator
- Amazon listing work is paused pending trademark/brand registry resolution
- EANs: GS1 UK barcodes acquired for products that have them. One-size variants (bonnets/mittens) corrected from phantom stock figures to real quantities

### Etsy (Caico Cotton)
- Being set up — bulk CSV upload workflow agreed
- Adam will share existing listings for style reference first, then Claude generates full Etsy CSV from Shopify product export
- Photos need to be added manually (can't be included in CSV)
- Categories expected to be consistent across the range

### Gift Sets (Priority Revenue Opportunity)
- No gift sets currently exist — this is the single biggest missed revenue opportunity
- Agreed sets to create (using existing stock):
  - Set 1: Newborn Essentials (~£22–35)
  - Set 2: 2-piece gift (~£40–50)
  - Sets 3–4: Mid-range 3-4 piece sets (~£50–60)
  - Set 5: The Caico Collection Premium Set (~£65, wicker hamper packaging)
- Packaging: Card hamper box with wicker print from Gadsby for Sets 1–4; real wicker hamper for Set 5
- These should be priority listings on Shopify and Etsy

### Competitors
- **Primary:** MORI (mori.com) — bamboo viscose blend, not pure cotton. 4,000+ SKUs. Gift sets, multipacks, licensed collabs.
- **Others:** Under the Nile, Cotton Baby UK, Prima Cotton
- **Caico advantage:** 100% Egyptian cotton vs MORI's 70% bamboo viscose. This is the core differentiation to hammer in all messaging.

### Strategy Notes
- Target: £10k/month revenue. At current price points that's ~200–400 orders.
- Meta ads target: UK women 25–38 following MORI, The White Company Baby, Scandiborn
- Creative angle: fabric close-ups, the Egyptian cotton story, UGC-style video
- Micro-influencer gifting (2k–15k followers) as a low-cost content strategy
- Amazon: get top 10–15 SKUs live first, not all 192
- Etsy: use for gifting channel, keyword-rich titles, bundles exclusive to Etsy

---

## BRAND 2: BEKYABEKYA

### What It Is
- **Etsy:** etsy.com/shop/BekyaBekya (established, performing well)
- **Website:** bekyabekya.myshopify.com (Shopify — being built)
- **Product:** Egyptian artisan homeware — Fayoum pottery (bowls, plates, mugs, espresso cups, jugs, trays), hand-blown glassware (tumblers in multiple colours), Egyptian alabaster pieces (candle holders, vases), table linen
- **Founded by:** Gabriela Asquith — diplomat's daughter, 15 years in Egypt, curates directly from artisan workshops
- **Positioning:** Limited edition, one-of-a-kind pieces. "Egyptian craftsmanship, chosen for discerning British homes."
- **Competitor:** Issy Granger (issygranger.com) — primary benchmark for design and pricing
- **Price range:** £15.95 (glass tumblers) to £135 (large bowls/plates 37–48cm)
- **Fulfilment:** 3PL warehouse (Story Unheard LTD), UK stock

### Etsy Performance
- 138 sales, 5.0 rating (31 reviews), Star Seller badge, 105 admirers
- 62 active listings
- Strong basket activity on: dark blue tumblers, green tumblers, hexagonal sage green plate, blue dot mezze dishes, large bowls

### Product Categories
- **Ceramics (Fayoum pottery):** Small bowls, serving bowls, statement bowls, plates & platters, mugs & cups, jugs & vases, trays
- **Glassware:** Hand-blown glass tumblers (5 colours — dark blue, green, clear, turquoise, cobalt)
- **Alabaster:** Candle holders, vases, lamps
- **Table Linen:** Napkins, runners

### Shopify Website Status
- Homepage architecture agreed and largely built
- **Navigation:** Mega menu under "Shop" — 3 columns: By Material, By Space, By Price
- **Homepage section order:** Hero → Shop by Collection (4 cards: Ceramics, Glassware, Alabaster, Table Linen) → Editorial Trust Strip (review quote) → Bestsellers/Most Loved (8 products) → Brand Story → Gift Sets "The Gift Edit" → Style by Space (3 cards) → Journal/Editorial → New Arrivals → Email Signup → Footer
- Smart collections built using product tags (not title-based rules — too unreliable in Shopify)
- Tags used: small-bowls, serving-bowls, statement-bowls, plates-platters, mugs-cups
- All 62 products imported from Etsy but initially arrived with no product types or tags — CSV fix applied

### Shopify MCP Connection
- Connected via terminal: `npx shopify-mcp --accessToken [TOKEN] --domain bekyabekya.myshopify.com`
- MCP server name: `shopify-bekya`

### Inventory
- Warehouse file: Story Unheard stock report (same 3PL as Caico)
- Alabaster SKUs use "A" suffix on Etsy (1A, 2A etc.) but numeric-only prefixes in warehouse
- 6 stock discrepancies previously identified and corrected (warehouse is source of truth)
- Duplicate Etsy listings (identical titles for 18cm bowls, 21cm bowls, espresso cups) caused Shopify merge issues — resolved by renaming on Etsy before re-importing

### Design & Brand Notes
- Premium, editorial aesthetic — NOT generic e-commerce
- Reviews displayed as 3 static editorial quotes (no stars, no carousel)
- 4-image lifestyle grid (magazine-style, not scrollable)
- Tagline: "Egyptian craftsmanship, chosen for discerning British homes"
- Brand story centres on Gabriela's connection to Egypt and direct artisan relationships
- Adam's wife influences keeping both the "Why Bekya" section and customer reviews sections

### Gift Sets (Priority)
- Currently no gift sets despite Etsy audience being heavily gift-buyers
- Needed: 4 tumblers boxed set, bowl + mug pairing, table linen + ceramics combinations
- Target price: £50–75 and £100+ tiers
- Issy Granger has 12 gift sets ranging £72–£133

---

## SHARED INFRASTRUCTURE

### Company
- **Legal entity:** Story Unheard LTD
- **3PL warehouse:** Fulfils both brands — single warehouse, separate SKU ranges
- **Shopify:** Two separate Shopify stores (one per brand)
- **Sidekick tip:** Works best with focused single-task prompts, not large batches

### Tools & Workflow
- **Image generation:** Nano Banana Pro via Google AI Studio Pro (Imagen 3 Pro model)
  - Note: Quality regression identified after Feb 2026 backend update — spatial/scale handling degraded
  - Alternatives being explored: GPT Image, Ideogram 3 for scale-sensitive work
- **Image pipeline planned (not yet built):** Auto-matching system for product + scene pairings, batch generation, two-stage pipeline for Caico Cotton (garment placement first, then AI baby face replacement second with manual approval pause)
- **Claude Code:** Connected to both Shopify stores via MCP. Terminal setup with shopify and shopify-bekya servers.
- **Adam's Claude subscription:** Max plan

### Video Production Agency
- Adam also runs a separate video production agency with a large editing team
- Post-production automation (proxy workflows, AI-assisted clip search, template-driven assembly) is a long-term interest but not the current focus

---

## HOW TO WORK WITH ADAM

- He prefers **copy-paste ready outputs** — prompts, CSVs, code snippets he can action immediately
- He works **exploratorily** before committing to build — don't assume he wants to execute immediately
- He corrects errors directly and briefly — respond by fixing without over-explaining
- **Shopify Sidekick:** Prefers receiving prompts he can paste directly rather than doing it himself via Claude Code
- **Token efficiency:** Focused, single-topic sessions work best
- **Source of truth:** Always use uploaded warehouse files for stock; never reconstruct quantities from memory
- His wife handles lifestyle image selection and creative direction — factor her into decisions affecting brand aesthetics
