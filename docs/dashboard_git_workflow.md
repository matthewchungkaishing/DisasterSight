# Dashboard Git Workflow

Work on branch `feature/dashboard` (from `origin/feature/ML-baseline`).

## Commits without Cursor co-author

1. Disable Cursor co-author in Settings (Git / co-author).
2. Commit only from your terminal: `git commit -m "..."`.
3. Before push: `git log -1 --format=full` — ensure no `Co-authored-by: Cursor` line.

## Suggested commit sequence

1. `Add design system, theme, and Streamlit app shell`
2. `Add data loaders, label normalization, and demo fixtures`
3. `Implement Dashboard page matching Stitch triage layout`
4. `Implement Map Explorer priority ranking page`
5. `Implement Analytics evaluation and limitations page`
6. `Wire real artifact paths with fixture fallback`
7. `Add dashboard run docs and demo polish`

You may squash or adjust messages; keep commits reviewable.

## Optional commit-msg hook

```bash
cat > .git/hooks/commit-msg << 'EOF'
#!/bin/sh
grep -qi 'co-authored-by:.*cursor' "$1" && { echo 'Remove Cursor co-author trailer'; exit 1; } || true
EOF
chmod +x .git/hooks/commit-msg
```
