# FOXORY v0.3.0 — appearance and layout editor

Installed locally at http://localhost:3636. Refresh with Ctrl + Shift + R, then click the palette icon in the header or open **Appearance** in navigation. No reinstall is required.

## What you can customize

- Brand name and browser title.
- Follow your light/dark theme, or choose FOXORY Forest, Midnight Ocean, Electric Violet, Warm Ember or Warm Paper.
- Custom page, sidebar, card, input, text, secondary text, accent and border colors, with pickers and editable hex codes. Low main-text/page contrast produces a warning.
- Left sidebar, right sidebar or desktop top navigation, plus sidebar width.
- Maximum content width, comfortable/compact spacing, card column count and corner rounding.
- Sans-serif, serif or monospace typography, plus reading size.
- Navigation order using drag grips or arrow buttons. Hide pages you do not need; Settings and Appearance remain available.
- Command Center section placement. Drag grips or arrows reorder Services, Metrics, Inventory and Tasks. The rendered section order follows the visual order.

## Preview, save and recovery

Changes preview immediately. **Save appearance** or the floating **Save design** button keeps your changes. **Discard preview** returns to the saved design. A floating save bar stays available when you navigate elsewhere during an unsaved preview.

**Reset design** previews the defaults. **Ctrl + Alt + 0** also previews the default design if a color or layout choice makes the interface difficult to use. Save to keep the reset, or discard to recover your saved design.

Design preferences are stored in this browser, scoped to your account and workspace. They do not change anyone else's layout. Export a design as JSON and import it into another browser when needed. Imports accept known appearance fields, valid colors and bounded layout values; they cannot add scripts or arbitrary CSS. Imported designs remain previews until saved.

Phones keep the mobile navigation menu and layouts that fit the screen, even if desktop top/right navigation or multiple columns are selected.

## Release verification

- Strict TypeScript/Vite production build passed.
- Full browser regression run: 18 passed, 3 optional Computer Mode cases skipped.
- Final appearance checks after drag refinements: 3 passed, covering color/layout persistence, visibility/order, safe discard, bounded imports, dashboard order, mobile navigation, design export/reset, real pointer drag placement and typed branding.
- Desktop and mobile screenshots inspected.
- Actual Docker application image built and tagged `foxory-local-app:0.3.0`. Previous image/source retained for rollback.
- Existing data, accounts, local models and configured business agents are preserved; this release requires no database migration.
- VERSION, frontend badge, backend health version and package metadata synchronized to 0.3.0. The ZIP and checksum are refreshed with a versioned filename.

The app stays hosted on the PC. Fonts use local system fonts and the design editor does not require a cloud service.
