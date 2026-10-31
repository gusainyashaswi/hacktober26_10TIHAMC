# HACKATHON.md

## Team name

10 Things I Hate About My Code

## Team members

| Name | GitHub username |
| --- | --- |
| Gurmehar Singh | @Gurmehar-git |
| Yashaswi Gusain | @gusainyashaswi |
| Devishi Grover | @devishigro13 |
| Yogye Berry | @YogyeBerry |

## Selected problem statement

**Problem 02: Evidence-Based Open Source Issue and Pull Request Triage**

## Project

**No Bluff**: helps open-source maintainers check the technical claims in issues and pull requests. It breaks a report into individual claims, checks each against the repository's source code and documentation, and produces an evidence-linked assessment (supported, contradicted, or inconclusive). A failure to reproduce a report is not treated as proof that it is false.

## Models we use and why

**Qwen3-8B** (`qwen3:8b` via Ollama, Apache-2.0)

- Role: extract technical claims, interpret relevant code and documentation, propose verification steps, and explain the collected evidence.
- Why: an open-weight model that runs locally on a laptop, strong enough for text-and-code reasoning, with no closed-model API needed.
- Model output is not treated as execution evidence. Source references are validated and real verification results are recorded.

## Implementation status

Qwen3-8B is integrated for structured claim extraction through local Ollama.
The standalone command and an actual recorded response are documented in
`docs/model-integration.md` and `examples/claim-extraction/`. This does not yet
implement evidence retrieval, truth assessment or reproduction execution.

## AI development assistance

Codex/ChatGPT and Claude were used for project planning and this document. Each later PR discloses the assistants and models involved.
