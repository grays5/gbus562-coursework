# gbus562-coursework

## About

This repository contains my weekly coursework and AI-assisted coding projects for GBUS 562 at the University of Mary Washington.

## Weekly Work

1. Week 1: An AI-coded Connect 4 game built with HTML, CSS, and JavaScript.
2. Week 2: A Prompt Lab web app that calls the Anthropic API, used to run four Wildframe Coffee Roasters prompting exercises (zero-shot, one-shot, few-shot, and chain-of-thought). The Prompt Lab exports are in `week-02/runs` and the writeup is in `week-02/writeup.md`.
3. Week 3: A Python RAG (retrieval-augmented generation) tool, `week-03/ask.py`, that uses a Chroma vector database and the Anthropic API to answer staff questions about the Larkfield Credit Union documents in `week-03/larkfield-docs`, citing its sources. The writeup is in `week-03/writeup.md`. The saved question runs (`week-03/runs/`) are not done yet because no API key was available.
4. Week 4: An HR email agent built on an MCP (Model Context Protocol) server. `week-04/hr_mcp_server.py` exposes an organization's HR policies (searched with a per-organization Chroma database), and the sender's own leave balances from `employees.csv`, as MCP tools. `week-04/agent.py` uses Claude Sonnet 5 and those tools to draft replies to the organization's sample emails, printing the tool steps, the draft, and whether it needs human review. It supports `--org` (default `hartwell-hr`), `--email`, and `--save`. Status and the files still needed are in `week-04/STATUS.md`.
