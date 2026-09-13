# Production Safety Gates

Read this before ANY action that modifies production state, is hard to reverse, or affects shared systems.

## Gate 1: Reversibility Check

Before proceeding, answer:
- Can this action be undone in < 5 minutes?
- Is there a backup or snapshot I can restore from?
- Will other people/systems be affected?

If any answer is "no" or "unknown" → **STOP and confirm with user**.

## Gate 2: Blast Radius Assessment

| Action type | Required confirmation |
|---|---|
| Deleting files / dropping tables / rm -rf | Always confirm + show what will be deleted |
| Force push / git reset --hard | Always confirm + show what commits will be lost |
| Server restart / service stop | Always confirm + state expected downtime |
| Credential rotation / key change | Always confirm + list systems that will break |
| Database migration (irreversible) | Always confirm + provide rollback plan |
| Firewall rule changes | Always confirm + state current rule being replaced |
| DNS changes | Always confirm + note propagation time |

## Gate 3: Pre-Action Checklist

- [ ] Current state is documented (git status / current config saved)
- [ ] Backup exists and was verified recently
- [ ] Rollback procedure is written out before starting
- [ ] Validation commands are ready to run after the change
- [ ] Affected parties have been notified if needed

## Gate 4: Forbidden Without Explicit User Approval

These actions require the user to say "yes, proceed" explicitly in this conversation:
- Force push to main/master
- Dropping any database table with data
- Deleting any file not created in this session
- Stopping a production service
- Changing authentication credentials/keys

## Secrets Hygiene

Before generating any credential, env file, or deployment configuration:
- Never hardcode secrets in config files committed to git
- Use environment variables or a secret manager
- Never print secrets in logs or terminal output
- Generated secrets must use cryptographically strong randomness
- Always remind the user to rotate any example/placeholder secrets
