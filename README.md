# Fictional SOP Knowledge Assistant

A beginner-friendly Python command-line MVP. It searches local Markdown SOPs,
then optionally asks OpenAI to answer using only retrieved passages. All three
sample SOPs describe an imaginary company and are not real operating policies.

## Start with offline search

Open PowerShell in this project directory. With Python 3.10 or later installed,
run this first (no dependencies, API key, or network needed):

```powershell
python main.py --search-only "How do I reset a forgotten password?"
```

You should see matching passages with document titles, sections, original file
paths, and inclusive line numbers. Scores measure keyword overlap, not confidence.
For another example, try `"report technology incident"`. An unrelated question
such as `"What is the cafeteria menu?"` should return no relevant passages.
Omit the question to receive a one-question interactive prompt.

## Enable generated answers

These setup commands install packages and require network access on your computer:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and put your own key after `OPENAI_API_KEY=`. Keep this file private;
it is excluded by `.gitignore`. Set `OPENAI_MODEL` to a model available to your
account that supports Responses API structured outputs. The supplied starting
value is `gpt-4.1-mini`; account availability must be checked by you.

```powershell
.\.venv\Scripts\python.exe main.py "How do I reset a forgotten password?"
```

Generation sends your question and retrieved excerpts to OpenAI and may incur
API charges. Search-only remains local. This application calls the official
Python SDK's `client.responses.create()` with a structured JSON output schema.
See the [official text generation guide](https://developers.openai.com/api/docs/guides/text).
Environment variables already set in your shell take precedence over `.env`.
`SOP_DIR` can select another Markdown folder; relative paths resolve from the
project root. Only immediate `.md` files are loaded.

## How the code fits together

| File | Responsibility |
| --- | --- |
| `main.py` | Parse CLI arguments, ask one question, display results, handle errors. |
| `assistant/__init__.py` | Define the Python package. |
| `assistant/config.py` | Load optional `.env` and environment settings. |
| `assistant/models.py` | Shared passage, search result, and answer dataclasses. |
| `assistant/loader.py` | Read Markdown and split at headings; preserve source line ranges. |
| `assistant/search.py` | Tokenize and rank passages with weighted keyword overlap. |
| `assistant/generator.py` | Build the grounded prompt and call the Responses API. |
| `assistant/service.py` | Coordinate retrieval, abstention, and citation validation. |
| `tests/test_retrieval.py` | Check topics, unrelated queries, and original line ranges. |
| `tests/test_answer_behavior.py` | Check abstention, citation rejection, fake API calls, and offline CLI. |

At startup, the loader creates passages in memory. The CLI calls the service;
the service searches passages and, only when matches exist, calls the generator.
The generator returns structured claims with source IDs. The service validates
each claim's IDs and renders citations such as `[S1]`. The CLI resolves each ID
to the original document metadata. Search-only calls search directly.

No matches means immediate abstention without an API call. The model is also
instructed to abstain for insufficient, partial, or conflicting evidence. Missing
or unknown citation IDs and malformed responses are rejected. API failures are
reported as errors, rather than presented as knowledge gaps.

## Run offline tests

```powershell
python -m unittest discover -s tests -v
```

Tests use standard-library `unittest`, fake generators, and a fake SDK client;
they require no API key, installed SDK, or network. They do not test a real
OpenAI response or guarantee that every generated claim is factually supported.

## Limits and next steps

Keyword search requires shared words and can miss synonyms. Its conservative
overlap rule is deliberately simple and can still retrieve irrelevant passages.
Citation validation verifies identifiers, not whether the passage proves the
claim. Review answers against cited text, especially when adding real documents.
The loader keeps whole sections, so large documents will need smaller chunks
and a context-size limit before use. This MVP has no authentication or permission
filtering and is intended for local fictional examples.

Future Slack and Teams adapters can call `AssistantService.answer_question()`
and format its returned `Answer`. A Confluence importer can produce the same
passage records with original URLs and version metadata. Before exposing real
internal content, add user identity and source permission filtering. Semantic
retrieval can later replace `search.py` while retaining the service interface.
