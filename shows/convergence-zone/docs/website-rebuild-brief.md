# Convergence Zone Website Rebuild — Project Brief

**Prepared:** June 20, 2026
**Purpose:** Reference document capturing analysis, decisions, and open questions from initial planning conversations. Intended to be portable into another chat, design session, or handed to a collaborator.

---

## 1. Background

Jim Causey hosts *Convergence Zone*, a weekly radio show airing Tuesday nights at 8:30 PM PT on 90.7 KSER-FM (Everett, WA) and 89.9 KXIR-FM (Freeland, WA), also streaming at kser.org and on TuneIn. The show is co-hosted with MichaelG and focuses on ambient, atmospheric, and space music — spotlighting Pacific Northwest artists alongside the contemporary and legendary musicians who inspire them.

The current site, **convergencezone.fm**, is built on WordPress, hosted through Porkbun (Jim's domain registrar). Jim wants to rebuild it because:

- He doesn't enjoy maintaining WordPress (plugin upkeep, security patching, general overhead for a site this size)
- He doesn't find the current visual design attractive
- He wants something **simpler to maintain** and **easier to add new content to**
- He wants a more **elegant, evocative visual identity** that reflects the show's atmospheric, ambient character

---

## 2. Current Site — Content Inventory

Based on research into the existing WordPress site (direct fetch was blocked in-session; gathered via search), convergencezone.fm contains:

- **Show Playlists** — 61+ episodes, each with tracklists/timestamps
- **Interviews** — long-form artist interviews (e.g., a two-part interview with 5-time Grammy winner David Arkenstone, Forrest Fang)
- **Music Reviews / "Best Of"** — editorial write-ups, year-end best-of lists
- **Specials** — guest-hosted or themed episodes
- **About page** — show description, host bios (Jim Causey + MichaelG)
- **Contact page** and a **music submission** mechanism for artists wanting airplay consideration
- **Mixcloud archive links** (archives live at mixcloud.com/farpointer)
- **Social links** — Instagram, Facebook, YouTube, Twitter/X

This content inventory should be treated as the **migration checklist** — every piece needs a home in the new structure (see Section 5).

---

## 3. Hosting & Domain Strategy

**Decision: Keep the domain at Porkbun. Host the built site elsewhere.**

Domain registration and web hosting are separable. Porkbun continues to register `convergencezone.fm`; DNS records get pointed at whichever static host we choose. This is a one-time, ~5-minute DNS change.

### Hosting platform research

We initially considered **Netlify**, but research surfaced a significant concern:

- In September 2025, Netlify moved new accounts to **credit-based pricing**. The free tier now allows roughly **20 deploys/month** (down from a much more generous build-minutes model).
- A widely-circulated incident involved a user receiving a **$104,000 bill** for a simple static site due to a traffic spike (Netlify has since added spend caps, but trust was damaged).
- Accounts created before Sept 4, 2025 can keep legacy pricing; new accounts cannot.

**Current recommendation: Cloudflare Pages.**

- Free tier includes **unlimited bandwidth and unlimited builds/deploys** — no credit system, no surprise bills
- 330+ global edge locations (vs. Netlify's smaller CDN footprint) — faster load times
- Same Git-based workflow: push to GitHub, site rebuilds and redeploys automatically
- Porkbun's infrastructure already has ties to Cloudflare, making the DNS handoff clean
- Vercel remains a solid fallback if Cloudflare Pages ever feels limiting, though it carries some usage-based billing risk for dynamic features (not a concern for a static site)

**If using Jekyll (see Section 4), GitHub Pages is also a valid zero-extra-account option** — Jekyll has first-class native support there. Cloudflare Pages is still preferable for speed and flexibility, but GitHub Pages removes even the need for a separate hosting account.

---

## 4. Static Site Generator: Jekyll vs. Astro

We evaluated two static site generator approaches. A static site generator converts simple content files (Markdown + metadata) into a fast, plain HTML/CSS/JS site — no database, no PHP, no WordPress-style attack surface, and (per Section 3) free hosting.

### Astro (initial recommendation)
- Modern, JavaScript/Node-based, very actively developed
- More natural fit if the site ever needs interactive features: audio players, dynamic search/filtering, live waveform displays
- Steeper learning curve if Jim or a collaborator ever wants to touch the underlying code directly
- Smaller theme ecosystem (newer project)

### Jekyll (current leaning recommendation)
- The original "blog-aware" static site generator (created 2008, GitHub Pages is built around it)
- **Collections** feature maps almost exactly onto Convergence Zone's content model — you can define `_playlists`, `_interviews`, `_reviews`, `_specials` as distinct content types, each with its own fields and templates
- Massive, mature theme ecosystem — 15+ years of blog/media-site themes to draw from rather than hand-building every style rule
- Templating language (Liquid) is simpler and less "programming-like" than Astro's component syntax
- Native, zero-config GitHub Pages hosting if desired
- Downside: runs on Ruby, not JavaScript. Ruby setup on a Mac can be mildly fussy the first time. This mostly only matters if Jim wants to preview the site locally before publishing — with a browser-based CMS + Git + auto-deploy pipeline, that step may never be necessary
- "Boring technology" in the best sense: extremely stable, unlikely to need migration, huge community for troubleshooting

### Comparison table

| | Jekyll | Astro |
|---|---|---|
| Built for | Blogs/content sites specifically | General-purpose, any site type |
| Templating | Liquid (simpler) | Components (more like programming) |
| Content model fit | Collections map directly to playlists/interviews/reviews | Good, slightly more config |
| Theme ecosystem | Huge, mature | Smaller, growing |
| Local dev dependency | Ruby (mildly fussy first install) | Node.js |
| Future interactivity | Possible via plugins, less native | More natural fit |
| Hosting | Native GitHub Pages, or Cloudflare Pages | Cloudflare Pages, Vercel, Netlify |
| Stability/maturity | Extremely stable, 15+ years | Stable, younger, faster-moving |

**Current leaning: Jekyll**, given Jim's strong and consistent preference for simplicity over flexibility, and a content model (playlists/interviews/reviews/specials) that fits Jekyll's collections feature almost exactly. Astro remains the right call only if interactive features (embedded players, dynamic filtering, search) become a near-term priority — this is an open question, see Section 8.

---

## 5. Content Management: Browser-Based Editing

Jim's stated preference: a **browser-based editor** — log in at a URL, fill out a form, click publish, no code or terminal required.

**Recommendation: Decap CMS** (formerly Netlify CMS, now community-maintained and platform-agnostic despite the legacy name).

- Works equally well with Jekyll or Astro — official integration guides and starter templates exist for both
- Provides a form-based editing UI layered on top of the Git repository — non-technical content entry, technical version-control underneath
- Free and open source

This satisfies the "simple to maintain, easy to add content" requirement directly: adding a new playlist becomes filling out a form (episode number, date, tracklist, Mixcloud link), not touching a database or a CMS admin panel bloated with plugins.

---

## 6. Recommended Stack (Summary)

```
Content editing  →  Decap CMS (browser-based, no code)
Site generator   →  Jekyll (leaning choice; Astro remains an option)
Version control  →  GitHub (free, stores all content + code)
Hosting          →  Cloudflare Pages (free, unlimited bandwidth/builds)
Domain           →  Stays registered at Porkbun; DNS points to Cloudflare Pages
```

Cost: Effectively just the existing Porkbun domain renewal. Hosting and CMS are both free at this scale. Jim's current Porkbun *hosting* plan (separate from domain registration) could likely be cancelled once the new site is live — worth checking what that's currently costing him.

---

## 7. Visual Design Direction

### Design process so far

**First mockup attempt** (file: `site-mockup-homepage.html`) — a dark, atmospheric, editorial-style design with deep navy backgrounds, glassmorphism-style cards, Cormorant Garamond + Inter + Space Mono typography, atmospheric glow gradients, and grain texture overlays. **Feedback: too complex/elaborate.** Jim asked for something much simpler and pointed to a reference site.

### Reference site: Dead Electric (deadelectricfm.com)

Dead Electric is *another* KSER show ("America's only vintage synth radio show," Fridays 10:30 PM on 90.7 KSER) — built on WordPress.com, but with a notably clean, simple structure worth borrowing from:

- Warm cream/pale-yellow background
- Simple circular logo mark (three colored circles) + show name in a clean serif, centered
- Minimal 4-item centered nav (About / Playlists / Blog / Contact)
- **One large custom illustration** as the entire visual centerpiece — does all the personality/atmosphere work, then everything else gets out of the way
- Centered bold tagline + italic broadcast info below the hero image
- Simple 3-column blog-post grid (image, title, excerpt, date) for content listing
- Dark band with email signup before the footer
- No complex CSS effects, no layered dark-mode treatments — confidence through simplicity

**Key takeaway adopted:** let one strong visual element (in Convergence Zone's case, a photograph Jim already has — he's also a photographer) carry the atmosphere, and keep everything else clean, light, and typographically simple.

### Second mockup (file: `site-mockup-v2.html`) — current direction

Built directly on the Dead Electric structural logic, adapted for Convergence Zone:

**Background:** Cool, slightly moody mist tone (`#edf0f3`) rather than Dead Electric's warm cream — chosen specifically to evoke "convergence" / Pacific fog rather than retro warmth.

**Typography:**
- Headings: Playfair Display (elegant serif)
- Body: Source Sans 3 (clean, readable sans-serif)
- No monospace/label fonts this time — simplified from the first mockup's three-typeface system

**Color palette:**
```
--bg:       #edf0f3   (cool mist background)
--bg-dark:  #2b3547   (deep slate, used for footer/CTA band)
--text:     #1c2535   (deep navy, primary text)
--text-2:   #4e5a6e   (mid slate, secondary text)
--text-3:   #8a95a3   (muted, tertiary/labels)
--accent:   #4a7f8e   (Pacific teal, links/highlights)
--rule:     rgba(28, 37, 53, 0.12)  (hairline borders)
```

**Structure (top to bottom):**
1. Centered header — show name, tagline, 5-item nav (About / Playlists / Interviews / Reviews / Contact)
2. Full-width hero photo (placeholder — awaiting Jim's actual photograph)
3. Centered show description + broadcast info row (station, schedule, stream, archive)
4. "Recent Playlists" — 3-column simple card grid
5. "Interviews & Features" — 3-column card grid with image placeholders
6. Dark "Submit Your Music" call-to-action band
7. Footer — brand blurb, social links, three link columns, copyright bar

**Open design item:** the hero photo is currently a gradient placeholder. The real photograph Jim selects will significantly affect the final feel — this should be one of the first things resolved in the next design session.

---

## 8. Open Questions / Next Steps

1. **Generator decision:** Confirm Jekyll vs. Astro. Leaning Jekyll, but worth revisiting if interactive features (embedded audio players, dynamic search/filter across 60+ episodes, tag-based browsing) turn out to matter more than expected.
2. **Hero photograph:** Jim has said he has a photograph in mind — need the actual image to finalize the homepage design and confirm the color palette still works against it.
3. **Visual feedback on `site-mockup-v2.html`:** awaiting Jim's reaction to the simplified direction before iterating further.
4. **Content migration plan:** WordPress has an XML export tool. Once the platform is settled, this export needs to be parsed and converted into the new structure (Jekyll collections or Astro content collections) — playlists, interviews, and reviews all transfer with some reformatting.
5. **Asset audit:** Jim mentioned existing photos/artwork "need work" — worth a follow-up pass to identify what's usable as-is vs. needs editing vs. needs to be created fresh.
6. **Mixcloud integration approach:** decide whether episode pages embed Mixcloud players directly or simply link out — embedding would be a nicer UX and is achievable in both Jekyll and Astro.
7. **Music submission form:** needs a form-handling solution since there's no backend. Both Cloudflare Pages and Netlify offer built-in form handling; Cloudflare Pages' approach should be confirmed it covers this use case (e.g., via Cloudflare Workers or a lightweight third-party form service like Formspree).
8. **Porkbun hosting cancellation:** once the new site is live, check what the current WordPress hosting plan costs and cancel it to capture the savings.

---

## 9. Files Produced So Far

- `site-mockup-homepage.html` — first design pass (dark/atmospheric; superseded)
- `site-mockup-v2.html` — current design direction (light/simplified, Dead Electric-inspired)

Both are static HTML/CSS mockups for visual review only — not built on the final Jekyll/Astro stack, no real data or functionality.
