# Notes for next sprint

Observations recorded during work on this demo repo that were noticed but deliberately not fixed in the current sprint.

## Keepalive standing gap (2026-05-25)

The keepalive workflow added in commit f460150 resets GitHub's scheduled-workflow 60-day inactivity timer monthly. However, its own failure modes are silent and uncovered:

- If Actions is disabled org-wide, the cron silently stops
- If the repo is archived, the cron silently stops
- If the default branch is renamed, the cron silently fails
- The workflow itself can pass while the underlying assumption fails

Fix when next touching this repo:
- Add an external heartbeat check (e.g., healthchecks.io ping inside the keepalive job that alerts if the cron doesn't fire monthly), OR
- Add a status badge in README.md that an external agent can poll

The keepalive's own health needs to be observable. This is a meta-principle violation — HO's whole product is fail-closed signed attestations of state, but the keepalive workflow protecting HO's demo asset fails open silently.

Calendar reminder set for 2026-08-25 to revisit.
