# Private processing: plan and reasoning

Written 31 October 2026. This records why Phase 2 of `TODO.md` exists and what is known and unknown. Re-check the Anthropic links before relying on them; policies change.

## The problem

In live mode each image is sent to the Anthropic API. This app stores nothing (no disk, no database, no content in logs), but it cannot control what the reading service keeps. Until Phase 2 is built, the page and the README tell people not to upload sensitive information.

Three places data can be at risk, and which the app controls:

| Place | Controlled by this app? |
|---|---|
| This server and the browser tab | Yes (nothing stored, `no-store` headers, no browser storage) |
| The reading service (Anthropic) | No. Its own policies apply |
| The hosting platform (logs, who can reach the site) | Only partly. See the deployment step |

## What Anthropic's documentation says (checked 31 October 2026)

Source: https://platform.claude.com/docs/en/manage-claude/api-and-data-retention

- Commercial terms say Anthropic does not train models on customer content from its services.
- **Zero data retention (ZDR)** means prompts and responses are not stored at rest after the response is returned. It is arranged per organization through Anthropic's sales team, not switched on in code.
- **HIPAA readiness** (a signed Business Associate Agreement plus safeguards) is available for the Claude API; eligible organizations can enable it in the Console.
- Even with ZDR or HIPAA, data may still be kept where the law requires it or where Anthropic's safety systems flag it, for up to 2 years.
- The page says conversation content is not retained by default, except for "Covered Models" (the Fable and Mythos models at the time of writing), which require 30-day retention. The default model here, `claude-sonnet-5-5`, was not on that list. Third-party sources give other default periods (7 or 30 days), so check Anthropic's commercial data retention policy for the exact standard window.
- On Amazon Bedrock and some Google Cloud offerings the cloud provider, not Anthropic, is the data processor, so that provider's terms apply.

## Options

| Option | Where the image goes | Risk left | Trade-off |
|---|---|---|---|
| A. Anthropic API as built | Anthropic | Provider retention under standard terms | Best accuracy, simplest |
| B. Anthropic API with ZDR or HIPAA readiness | Anthropic, stricter terms | Legal holds, flagged content | Needs an agreement; best accuracy |
| C. Claude through your own cloud account | Your cloud provider | That provider's terms | More setup; same model |
| D. Fully local model | Nowhere; stays on your machine or network | Your own machine and network | Likely weaker on handwriting; needs hardware; more setup |

Only option D guarantees an accidental upload cannot leave your control. Options B and C reduce risk through contracts, not physics.

## Local reading: two approaches

**A. A general local vision model** (for example run through Ollama), given the same instructions as today. Quick to build because the prompt and parsing are reused. Comparison guides place these models in a second tier: good on structured documents and clear photos, weaker on handwriting. The amber flags would depend on the model reporting its own doubt, which a smaller model may do less reliably.

**B. A dedicated local OCR model plus our own structuring code.** Small dedicated OCR models (around 1B parameters) currently top open-source document benchmarks, but those scores are reported by the models' authors, not independent tests, and say little about handwriting specifically. Some models strong on handwriting have licences with limits (for example a revenue cap), so licences must be checked. We would build the row, column, form, and list logic ourselves, and could take real confidence scores from the OCR engine to drive the flags, which may be a better basis than an AI's self-report.

Plan: build A first, measure, then decide whether B is worth building (Phase 2, steps 14 and 15).

## How we will decide: measure, do not guess

A scoring script will run the sample documents (with their answer keys) through each reader and report how many cells are right and whether the wrong ones were flagged. A wrong cell that was flagged costs little; a wrong cell that was not flagged is the real danger. The script runs on the user's own hardware, because the models do not run in the development sandbox.

## Closed deployment

Two containers on a private network with no route to the internet: the app and the model server. Models are downloaded in advance on a connected machine, then the connection is cut. The app container runs with a read-only filesystem. An automated check proves the app container cannot reach outside. The deployment still needs a login or VPN in front of it, because the app has no accounts and anyone who can reach it can use it.

## Design rules for Phase 2

1. **No silent fallback.** If local processing is configured and fails, show an error. Never quietly send the image to the cloud.
2. **The mode is always visible** on the page: private (processed on this server) or cloud (sent to Anthropic).
3. **Strip photo metadata** before any image is sent anywhere. Apply the EXIF rotation first, or photos will turn sideways.
4. **Do not retire the interim warning** until the privacy steps are verified for the actual deployment. In cloud mode without a ZDR or HIPAA arrangement, a warning stays.

## Limits that remain even when this is done

- A downloaded CSV lands in the user's Downloads folder.
- Shared computers, screenshots, and printing are outside the app's control.
- Someone has to own model updates and licence checks.
- Local accuracy on real handwriting is unknown until measured.

## Open questions

- **What hardware will the closed setup run on?** A graphics card and its memory decide whether a general local model is realistic. One guide suggests about 8 to 16 GB of graphics memory for an 11B-parameter model and about 2 GB for a very small one; small dedicated OCR models are lighter. Without a graphics card it will run, but slowly, and how slowly needs measuring.
- Which kinds of sensitive documents matter (health, financial, children's information)? That decides whether a HIPAA arrangement is relevant.
- Is Docker acceptable on the target machines (on Windows it needs WSL2)?
