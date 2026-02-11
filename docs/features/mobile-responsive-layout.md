# Feature: Mobile-Responsive Layout

## Why This Comes First

The core use cases — checking who's in a group before a meeting, reading last week's notes in the car, marking a commitment done — happen on a phone. A layout that breaks on small screens means users bounce before they ever consider paying. Every other feature in this list depends on users actually staying.

This is not a new feature so much as **unblocking every other feature from being useful**.

---

## What Needs to Change

The app currently uses a fixed-width layout with no media queries. On a phone it renders as a shrunken desktop view. The changes are entirely in `base.html` and the content templates — no Python or database work required.

### Viewport meta tag

`base.html` needs this in `<head>` if it isn't already there:

```html
<meta name="viewport" content="width=device-width, initial-scale=1">
```

Without it, mobile browsers render at desktop width and zoom out.

### Navigation

The current header has a horizontal nav bar (title + About + auth controls). On mobile this needs to:
- Stack vertically, or
- Collapse into a hamburger menu (simpler: just stack, no JS required)

Minimum viable approach: wrap nav items in a flex container that switches from `row` to `column` below 600px.

### Cards and lists

The junto cards on the homepage and the member list on the show page should go from a multi-column grid to a single column on narrow screens.

### Forms

Input fields should be `width: 100%` on mobile so they don't clip. Buttons should be large enough to tap (minimum 44px height per Apple HIG).

### Action buttons on the show page

The Edit / Delete / Add Member buttons sit in a row on desktop. On mobile they should stack. The delete button in particular — a `<form>` with a submit button — needs enough tap area to avoid accidental presses.

---

## Breakpoints

Keep it simple. One breakpoint handles most cases:

| Breakpoint | Layout |
|---|---|
| `> 640px` | Current desktop layout |
| `≤ 640px` | Single column, stacked nav, full-width inputs |

A second breakpoint at `960px` can handle tablets if needed later, but don't build it until there's a reason to.

---

## Implementation Approach

Since all styling is inline in `base.html` and per-template `<style>` blocks, add a `<style>` block in `base.html` with mobile overrides:

```css
@media (max-width: 640px) {
  .nav { flex-direction: column; }
  .junto-grid { grid-template-columns: 1fr; }
  .action-row { flex-direction: column; gap: 8px; }
  input, textarea { width: 100%; box-sizing: border-box; }
  button, .btn { min-height: 44px; width: 100%; }
}
```

The exact class names depend on the current markup in `base.html` and each template. Read the templates before writing the CSS.

---

## Testing

Use browser dev tools (F12 → device toolbar) to preview at 375px (iPhone SE) and 390px (iPhone 14) widths. Check:

- [ ] Homepage: junto cards don't overflow
- [ ] Junto show page: member list readable, action buttons tappable
- [ ] New/edit forms: inputs fill the screen, submit button is large
- [ ] Navigation: doesn't clip or overlap content
- [ ] Flash messages: don't get cut off

No new tests are needed — the existing 31 tests cover behavior, not layout.

---

## Acceptance Criteria

- All pages render without horizontal scrolling at 375px width
- All tap targets (buttons, links) are at least 44px tall on mobile
- Forms are usable without zooming in
- No JavaScript required
