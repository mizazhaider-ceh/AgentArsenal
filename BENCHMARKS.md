# AgentArsenal static benchmarks

Generated: 2026-10-23
Skills checked: 356 (top-level skills and sub-skills)

> These are STATIC scenario checks on the shape of the
> markdown files, not live tests. No tool was executed and
> no technique was verified against a real target. A passing
> score means the skill looks complete on the page; it says
> nothing about whether the commands work. Live verification
> remains a human job, recorded in each skill's
> `last_verified` frontmatter field.

## Scenarios

- **S1**: primary tool mentioned in body
- **S2**: example command block
- **S3**: description has 3+ trigger phrases

Scenario S1 is skipped (not counted) for skills that pin no
tools in frontmatter. `None` results never count as passes.

## Per-domain pass rates

| Domain | Skills | S1 % | S2 % | S3 % | Domain avg |
| --- | --- | --- | --- | --- | --- |
| ad | 18 | 94.4% | 100.0% | 11.1% | 68.5% |
| ai-security | 8 | 87.5% | 100.0% | 0.0% | 62.5% |
| api | 7 | 57.1% | 100.0% | 71.4% | 76.2% |
| auth | 12 | 50.0% | 100.0% | 58.3% | 69.4% |
| automotive | 8 | 100.0% | 100.0% | 0.0% | 66.7% |
| binary | 11 | 100.0% | 100.0% | 54.5% | 84.8% |
| blockchain | 8 | 87.5% | 100.0% | 12.5% | 66.7% |
| bugbounty | 4 | 50.0% | 100.0% | 75.0% | 75.0% |
| c2 | 4 | 75.0% | 100.0% | 100.0% | 91.7% |
| cloud | 22 | 50.0% | 100.0% | 50.0% | 66.7% |
| crypto | 15 | 100.0% | 100.0% | 53.3% | 84.4% |
| defensive | 10 | 60.0% | 100.0% | 20.0% | 60.0% |
| engineering | 49 | 91.8% | 100.0% | 12.2% | 68.0% |
| forensics | 16 | 81.2% | 100.0% | 68.8% | 83.3% |
| hardware | 8 | 87.5% | 100.0% | 0.0% | 62.5% |
| ics-scada | 8 | 100.0% | 100.0% | 12.5% | 70.8% |
| incident | 7 | 57.1% | 100.0% | 85.7% | 81.0% |
| linux | 7 | 28.6% | 100.0% | 57.1% | 61.9% |
| malware | 4 | 100.0% | 100.0% | 0.0% | 66.7% |
| memory | 5 | 100.0% | 100.0% | 40.0% | 80.0% |
| mobile | 5 | 60.0% | 100.0% | 60.0% | 73.3% |
| network | 27 | 92.6% | 100.0% | 37.0% | 76.5% |
| osint | 9 | 100.0% | 100.0% | 55.6% | 85.2% |
| privacy | 8 | 100.0% | 100.0% | 0.0% | 66.7% |
| privesc | 11 | 72.7% | 100.0% | 54.5% | 75.8% |
| recon | 6 | 100.0% | 100.0% | 0.0% | 66.7% |
| soc | 17 | 88.2% | 100.0% | 52.9% | 80.4% |
| web | 42 | 50.0% | 100.0% | 42.9% | 64.3% |

## Overall

- S1 (primary tool mentioned in body): 280/356 pass (78.7%)
- S2 (example command block): 356/356 pass (100.0%)
- S3 (description has 3+ trigger phrases): 130/356 pass (36.5%)

**Overall static pass rate: 71.7%** (766 of 1068 scenario checks passed)

## Reading these numbers honestly

- A domain at 100% is well-formatted, not well-tested.
- S3 failures are the most actionable: the description is
  the discovery surface for agents, so add trigger phrases
  first when fixing a low score.
- S1 failures usually mean the body never names its pinned
  tool; add the tool name where the workflow uses it.
- S2 failures mean the skill has no copy-pasteable example;
  add at least one fenced command block.

