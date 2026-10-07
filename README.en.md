# Genesis Hive

A multi-agent reasoning prototype with task decomposition, dependency-aware execution, structured debate and team adjustment.

[中文](README.md) · [Usage](docs/usage.md)

![Project illustration](docs/media/project-hero.png)

Python · FastAPI · LangGraph · React · Apache-2.0

![Recorded walkthrough](docs/media/walkthrough.gif)

Recorded static UI sample; no live agent or provider calls.

## Explore without an API key

```sh
git clone https://github.com/luxiaoyu0731/genesis-hive.git
cd genesis-hive/frontend
npm ci
npm run dev
```

The browser displays a **static sample**, letting you explore five stages without running agents or paying a provider. The sample is not a measured live result. The UI currently does not submit goals to the backend.

## Run the engine

Python 3.11+; frontend Node.js 22.12+.

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cp .env.example .env
.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Configure OpenRouter and role models in the local environment file, then use the documented REST API. Calls cost provider credits and may send input to configured models. Keep the server local: this single-process prototype has no public authentication.

## Engine design

Task graph → specialist roles → dependency-aware execution → council discussion → adjust or summarize. Round summaries bound context; unchanged agents can reuse previous results.

<details><summary>Offline checks and limits</summary>

```sh
python3 -B -m unittest discover -s tests -v
.venv/bin/python test_executor_mock.py
```

Tool adapters include placeholders; HTTP spending is not enforced as a hard provider budget. Role diversity does not establish improved accuracy.

[Code review](docs/code-review.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Asset credits](docs/media/README.md)

</details>

[Apache-2.0](LICENSE)
