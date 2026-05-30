# AI Usage Log

This log documents where AI tools were used in this project and what the team verified independently.

---

## Tools Used

- Claude (Anthropic) — primary AI assistant used throughout the project
- ChatGPT (OpenAI) — debugging, modelling discussion, deployment and documentation assistance
- GitHub Copilot — minor code completion assistance

---

## How AI Was Used

| Task | AI Used | What We Verified Ourselves |
|---|---|---|
| Writing and refining `CHARTER.md` | Claude / ChatGPT | All project framing, metrics, modelling descriptions, and repository details reviewed manually |
| Drafting and restructuring `README.md` | Claude / ChatGPT | All run commands tested manually; repository structure and output paths verified locally |
| Writing milestone outputs (`outputs/*.json`) | ChatGPT | Metric values checked against actual project runs and repository outputs |
| Debugging deployment and repository structure | ChatGPT | Streamlit deployment and GitHub repository tested manually |
| Debugging simulation logic | Claude / ChatGPT | Match logic, scorecards, and cricket-rule behaviour verified manually through repeated simulations |
| Data-cleaning and feature-engineering suggestions | ChatGPT | Cleaning logic and modelling choices reviewed before implementation |
| General debugging support | Claude / ChatGPT | All fixes tested manually before commit |
| UI and frontend iteration brainstorming | ChatGPT | Final UI decisions made by the team |
| General GitHub guidance | Claude / ChatGPT | All git operations performed and verified manually |

---

## What We Did Not Use AI For

- The original project idea and overall simulator concept
- Dataset selection and overall project direction
- Final modelling decisions and evaluation criteria
- Actual model training runs and artefact generation
- Interpretation of results and identification of modelling limitations
- Final deployment and repository management decisions

---

## Verification Statement

All AI-generated content was reviewed by at least one team member before inclusion in the repository. No AI-generated code, documentation, or metric values were committed blindly. Repository outputs, JSON metrics, saved artefacts, and deployed application behaviour reflect actual local project runs and repository contents.

AI tools were used as development assistants for debugging, drafting, implementation guidance, and iteration support, not as substitutes for understanding or independent work.

*Signed: Annay De, Tanmay Singh, Siddhant Mukherjee*
