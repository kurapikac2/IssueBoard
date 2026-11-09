# Browser QA checklist and current evidence

## Executed 2026-11-09

The existing Chromium workflow passed locally against the current application in a separate SQLite database. It exercised registration, login, project/issue creation, combined filters, changing status, two persisted history entries, counts and logout. Screenshots at 1440×900 and 390×844 were inspected: content is readable, mobile layout has no document overflow and no personal data appears. The capture waits for the application's actual notification to dismiss; no DOM content or image pixels are altered for screenshots.

33 pytest tests also passed, including authorization, CSRF and database rollback. This is not a claim of full accessibility, cross-browser coverage or completion of every manual scenario below. There is no previous visual-regression baseline. [Capture provenance](images/README.md) records reproduction.

## Further manual checks

Use only a dedicated `ISSUEBOARD_DB` and fictional accounts.

1. Check desktop, 390 px and 320 px layouts, readable controls and horizontal overflow.
2. Try duplicate registration and an incorrect password; verify useful errors.
3. Create two projects, switch between them and reload.
4. Create bug/task issues across all priorities and statuses.
5. Search Cyrillic titles, combine filters and verify both sort directions.
6. Edit a title without changing status; ensure history does not grow. Then change status and verify actor, transition and time.
7. Cancel deletion, then confirm deletion of a disposable issue.
8. Check empty search results and filter reset.
9. Navigate with Tab, Shift+Tab, Enter and Escape; assess focus visibility and dialog focus return.
10. Check connection errors with only the disposable server stopped.
11. Use a separate browser profile and confirm another account cannot read a private project.
12. Log out and reload; access must remain revoked.

Do not include real usernames, cookies, tokens, browser tabs or private projects in published evidence. Screen-reader, Firefox/WebKit and real-device checks remain future work.
