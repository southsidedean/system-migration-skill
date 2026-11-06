# Sensitive data

Old machines collect things you may not want to carry forward: a former employer's files, customer logs, old logins, and health or financial records. This page explains how the skill handles them. It isn't legal advice; check any agreements you're bound by.

## Two questions for every item

**1. Whose is it?**

| Owner | Examples |
|---|---|
| Personal | Your own files |
| Employer | A current or former employer's code, docs, or notes |
| Client or customer | Support tickets, logs, or config dumps from someone else's systems |
| Regulated | Health, financial, or government ID data |
| Unknown | Anything that can't be placed. Claude asks you. |

**2. Is it a secret?** Passwords, tokens, private keys, cloud logins, and `.env` files all count, no matter who owns them.

They're separate questions because they need different handling. A former employer's training slides and that employer's cloud login are both "employer", but only one is a secret.

## Then you choose an action

| Action | Means |
|---|---|
| Keep | Copy it to the new machine |
| Leave behind | Don't copy it. If the old machine is erased, this means it's gone. |
| Archive | Save a verified copy somewhere else |
| Encrypted archive | Same, encrypted with your own tool |
| Delete | Remove it, by exact path |
| Review later | Decide before the final check |

## How it finds things

Names can mislead. A folder called `Insurance` might hold a customer's gateway configs, so the skill searches contents too:

1. Claude asks what past employers, clients, and regulated work the machine has seen. You can decline.
2. It builds a private list of search terms, such as organization names, products, and email domains.
3. The scan checks file names and contents, and reports only paths and match counts.
4. Claude sorts the results, sets aside obvious false positives, and asks about the rest.

Public learning material that mentions a product isn't the same as customer data, and Claude should treat it that way.

## What the scan can't see

- **Inside PDFs, Office files, and images:** listed as "not searched".
- **Inside archives:** it checks the names of files inside, but not their contents.
- **Credential stores:** skipped on purpose.
- **Blocked folders:** recorded as unreadable.
- **Names you didn't mention:** it can only find terms it's given. A list drawn from one employer's data won't find another's customers.

So "nothing found" means nothing was found in what could be searched. Review anything listed as not searched that matters to you.

## Credentials

- **Think about new ones first.** Often it's simpler and safer to create new credentials than to copy old ones.
- **Sign out of former employers' accounts** before you erase the machine. The accounts belong to them, so only their admins can truly revoke access.
- **Test copies at the destination,** then test again later, since the source's store can keep changing.

## If you keep a copy

Before making a new long-term copy of someone else's data, check your employment agreement, NDA, or any data-protection rules that apply. The choice is yours, and Claude records it.

If you archive sensitive data:

- **Encrypt it with your own tool,** such as an encrypted disk image or `age`. The skill's archives aren't encrypted.
- **Keep the password yourself.** Never give it to Claude. If you lose it, you lose the archive.
- **Remember your backups.** Old backups can still hold data you've deleted, so decide what to do with those too.

## Keeping this private

Your migration folder can name real people and organizations, especially `terms.txt`, `decisions.md`, and scan results. Don't commit it to a repository or share it without checking first.
