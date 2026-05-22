# Stitch UI Design Brief — DisasterSight Dashboard

Copy the **Master prompt** into Google Stitch first (Medium: **Web**). Then run the **Screen prompts** one at a time, pasting the **Design system** block into each so styles stay consistent.

When you have outputs, send back: exported PNGs (or Stitch share links), chosen light/dark theme, spacing notes, and any `DESIGN.md` Stitch generated.

---

## Design system (paste into every Stitch prompt)

```
DESIGN SYSTEM (REQUIRED — use exactly)

Product: DisasterSight — academic satellite damage triage dashboard
Platform: Web desktop dashboard (1440×900 primary frame; must also read well at 1280×720 for laptop demo)
Implementation target: Streamlit (Python) — favor simple layouts: left sidebar, main content columns, metric cards, data tables, tabs. No custom React animations.

Theme: Dark professional operations dashboard (not playful, not consumer SaaS marketing)
Mood: Calm, credible, humanitarian-tech, suitable for university industry-night demo in under 2 minutes

Typography:
- Headings: Inter or IBM Plex Sans, semibold
- Body/UI: Inter regular 14–16px
- Monospace for IDs/scores: IBM Plex Mono 12px

Colors:
- App background: #0F1419 (near-black blue-gray)
- Surface/card: #1A2332
- Surface elevated: #243044
- Border subtle: #2D3A4F
- Text primary: #E8EDF4
- Text secondary: #9AA8BC
- Text muted: #6B7A90
- Primary accent (CTA, selected nav): #3B82F6
- Warning/review accent: #42A5F5

Damage severity palette (MUST use for legends, chips, map overlays):
- No damage: #4CAF50
- Minor damage: #FFC107
- Major damage: #FF7043
- Destroyed: #C62828
- Human review required: #42A5F5

Semantic:
- Success/confirmed: #4CAF50
- Caution: #FFC107
- Danger: #C62828
- Info banner background: #1E3A5F at 40% opacity, border #42A5F5

Spacing: 8px grid (8, 16, 24, 32)
Radius: cards 12px, buttons 8px, chips 999px
Shadows: minimal; prefer borders over heavy drop shadows

Accessibility: WCAG 2.1 AA contrast for text on dark surfaces; never rely on color alone — pair chips with text labels and icons
```

---

## Master prompt (context — run once or prepend to Screen 1)

```
Design a web analytics dashboard for "DisasterSight", an AI-assisted satellite building-damage triage tool for post-disaster human review (academic prototype, NOT an emergency dispatch system).

TARGET USERS: Emergency-management analysts, humanitarian mapping teams, and geospatial AI evaluators reviewing pre/post satellite imagery at a desk during a 2-minute live demo.

CORE USER GOAL: Quickly answer — Where is damage concentrated? How severe? Which zones need human review? How confident is the model?

CONSTRAINTS:
- Desktop web only (no mobile-first)
- Information-dense but uncluttered; scannable in under 2 minutes
- Always show a persistent responsible-AI disclaimer strip (decision-support only, not operational deployment)
- Building damage uses exactly 4 severity classes + a separate "review required" state
- Priority score is a transparent demo metric (0–100), separate from model confidence
- Imagery is the hero: large before/after satellite pair with optional semi-transparent polygon overlays

DELIVERABLE: One primary dashboard screen layout with clear visual hierarchy. Use the DESIGN SYSTEM block above.
```

---

## Screen 1 — Main triage dashboard (primary)

```
[Paste DESIGN SYSTEM block here]

Screen: DisasterSight — Main Triage Dashboard (single web page)

Layout hierarchy (top to bottom, left to right):

1) TOP BAR (full width)
- Product wordmark "DisasterSight" + subtitle "Satellite Damage Triage · Decision Support Prototype"
- Right side: pill badge "Demo mode · Cached predictions" and subtle status dot "Ready"

2) RESPONSIBLE-AI BANNER (full width, always visible, not dismissible)
- Icon: shield or info
- Copy: "Academic prototype for human review only. Not for autonomous emergency response or operational dispatch."
- Secondary line: "Low-confidence predictions are flagged for human review."

3) LEFT SIDEBAR (fixed width ~280px)
- Section "Scene"
  - Searchable dropdown: disaster scene ID (e.g. pinery-bushfire_00000000)
  - Metadata chips: disaster type (wildfire), split (test)
- Section "View controls"
  - Toggle: Show damage overlays (on by default)
  - Toggle: Show building bounding boxes
  - Toggle: Show confidence labels on buildings
- Section "Legend"
  - Horizontal or vertical color swatches with labels for: No damage, Minor, Major, Destroyed, Review required
- Footer mini-link: "Model & limitations"

4) MAIN CONTENT — ROW 1: KPI METRIC CARDS (4 cards)
- Card 1: Total buildings assessed (large number, e.g. 142)
- Card 2: Priority score (large number 0–100 with label "Demo priority score" and info tooltip icon explaining formula)
- Card 3: Buildings flagged for review (number + amber/blue accent if > 0)
- Card 4: Dominant damage class (e.g. "Major damage" with colored chip)

5) MAIN CONTENT — ROW 2: SCENE EXPLORER (hero, ~60% viewport height)
- Two equal columns: "Pre-disaster" | "Post-disaster"
- Each column: large satellite image placeholder (16:9), subtle grid overlay hinting geospatial context
- On post-disaster image: semi-transparent colored building polygons (use damage palette)
- Floating toolbar on image: zoom icon, fit icon, overlay opacity slider
- Below images: caption with scene ID and image dimensions

6) MAIN CONTENT — ROW 3: SEVERITY BREAKDOWN (two columns)
- Left: Donut or horizontal bar chart — class counts (No / Minor / Major / Destroyed)
- Right: Compact table "Top buildings by severity" with columns: Building ID, Predicted class (chip), Confidence %, Review flag (icon)

7) OPTIONAL RIGHT RAIL or bottom strip: "Zone priority at a glance" mini leaderboard (3 rows)

Visual style: Dark ops dashboard, crisp cards, thin borders, no gratuitous gradients. Charts use damage palette only. Empty states should look intentional (skeleton placeholders).

Include realistic placeholder numbers and one scene name. Make overlay colors match the design system exactly.
```

---

## Screen 2 — Priority ranking & review queue

```
[Paste DESIGN SYSTEM block here]

Screen: DisasterSight — Priority Ranking & Review Queue

Purpose: Compare multiple disaster scenes/zones and decide which to inspect first during triage.

Layout:

1) Same top bar and responsible-AI banner as Screen 1 (for consistency)

2) PAGE HEADER
- Title: "Priority ranking"
- Subtitle: "Zones ordered by demo priority score · higher = more attention for human review"

3) FILTER ROW
- Segmented control: All scenes | Review required only | Test split
- Sort dropdown: Priority score (desc) | Review count (desc) | Destroyed share (desc)

4) MAIN TABLE (full width, card container)
Columns:
- Rank (#1, #2, …)
- Scene ID (monospace)
- Disaster name
- Priority score (bold, color-coded: 80+ high, 50–79 medium, <50 low)
- Destroyed share %
- Major damage share %
- Damage density %
- Review flags (count badge, blue if > 0)
- Action: "Open scene" text button

Show 5–8 example rows with varied scores. Row with review flags > 0 should have subtle left border accent in #42A5F5.

5) BELOW TABLE: two insight cards side by side
- Card A: "Highest priority scene" with scene ID, score, one-line rationale
- Card B: "Scenes needing human review" with count and bullet list of scene IDs

Keep dark theme and same typography/colors as Screen 1.
```

---

## Screen 3 — Model review & limitations

```
[Paste DESIGN SYSTEM block here]

Screen: DisasterSight — Model Review & Limitations

Purpose: Build evaluator credibility — show metrics, confusion matrix, and honest limitations (not marketing hype).

Layout:

1) Same top bar and responsible-AI banner

2) TWO-COLUMN LAYOUT

LEFT COLUMN (60%):
- Section title: "Evaluation summary"
- Metric row (4 small cards): Macro F1, Precision (macro), Recall (macro), Held-out events
- Large card: Confusion matrix heatmap image placeholder (4×4 classes: no_damage, minor_damage, major_damage, destroyed)
- Caption: "xBD subset · cached inference · not live model"

RIGHT COLUMN (40%):
- Section title: "Known limitations"
- Bulleted list with icons:
  - Trained on historical xBD events; may not generalize to new disaster types
  - Building localisation uses dataset polygons in MVP (segmentation is optional)
  - 4-class damage may be collapsed for demo stability
  - Priority score is illustrative, not an official emergency metric
- Section title: "Failure cases"
- Card with thumbnail grid (2×2) labeled "False negative example", "Confusion minor/major", etc.
- CTA style link: "View qualitative examples" (secondary, not primary button)

3) FOOTER STRIP
- Text: "Human-in-the-loop required for all operational decisions."

Tone: Transparent, academic, slightly muted saturation on evaluation charts so imagery screens remain the hero elsewhere.
```

---

## Follow-up prompts (use after first generation)

**Tighten hierarchy**
```
Keep the layout but increase whitespace between the KPI row and the scene explorer. Make the before/after images 15% taller. Reduce visual noise in the sidebar.
```

**Streamlit realism**
```
Simplify custom components so this could be built in Streamlit: replace complex chart widgets with st.metric cards, st.columns, st.dataframe, and st.tabs. Show which sections map to Streamlit tabs: Overview | Scene | Priority | Model review.
```

**Light mode variant (optional second pass)**
```
Duplicate the main dashboard in a light theme variant: background #F4F6F9, cards white #FFFFFF, text #1A2332. Keep damage colors identical.
```

**Accessibility pass**
```
Audit contrast ratios on dark cards. Add icons beside every damage-class color in the legend. Ensure review-required state is visible for deuteranopia.
```

---

## What to send back to Evan (for Streamlit build)

1. Stitch export links or PNGs for all 3 screens  
2. Final chosen theme (dark required; light optional)  
3. Hex values if Stitch changed any colors  
4. Typography choices (font names, sizes for H1/H2/body/metric)  
5. Component specs: card padding, sidebar width, image aspect ratio  
6. Any `DESIGN.md` from Stitch project  
7. Notes on tab vs single-page navigation preference  

---

## Stitch settings checklist

| Setting | Value |
|---------|--------|
| Medium | Web |
| Model | Latest available (e.g. Gemini 3 Pro) |
| Approach | One screen per prompt; paste design system each time |
| Iterations | 3–5 follow-ups per screen before locking |
