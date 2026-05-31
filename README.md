<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=6366f1&height=120&section=header&text=COGNOS&fontSize=48&fontColor=ffffff&fontAlignY=38&desc=Cognitive%20AI%20Assistant%20with%20Memory%20%20Reasoning&descAlignY=60&descSize=15&descColor=a5b4fc" width="100%"/>

[![License: MIT](https://img.shields.io/badge/License-MIT-6366f1?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=flat-square&logo=langchain&logoColor=white)](https://langchain.com)

</div>

---

## Overview

COGNOS is a cognitive AI assistant designed for long-horizon task completion. Unlike stateless chatbots that forget context between turns, COGNOS maintains persistent memory across sessions and applies multi-step reasoning chains to decompose and solve complex tasks.

The core research question driving this build: *how do we design LLM-based assistants that reason like a person - remembering context, planning ahead, and recovering from partial failures?*

---

## Architecture

```
User Input
    │
    ▼
┌──────────────────┐
│  Memory Module   │  Episodic + semantic memory
│                  │  Persistent across sessions
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Reasoning Chain │  Multi-step task decomposition
│                  │  Goal-subgoal planning
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  LLM Core        │  Context-aware generation
│                  │  Memory-augmented prompting
└────────┬─────────┘
         │
         ▼
   Response + Updated Memory State
```

---

## Key Features

| Feature | Description |
|---|---|
| **Persistent Memory** | Episodic and semantic memory across conversation sessions |
| **Multi-Step Reasoning** | Decomposes complex tasks into traceable reasoning steps |
| **Context Awareness** | Retrieves relevant past context before each generation |
| **Memory Management** | Automatic pruning and consolidation of long-term memory |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **LLM Orchestration** | LangChain |
| **Memory** | Custom episodic store + vector retrieval |
| **Backend** | Python |
| **Language** | Python 3.10+ |

---

## Getting Started

```bash
git clone https://github.com/royxlead/cognos-python.git
cd cognos-python
pip install -r requirements.txt
python main.py
```

---

## Research Context

COGNOS explores the boundary between stateless LLM inference and stateful cognitive architectures. The memory design draws from cognitive science models of episodic and semantic memory, applied to practical LLM system design. Key challenge: maintaining coherent long-term context without exceeding context window limits.

---

<div align="center">

**[Portfolio](https://royxlead.netlify.app) · [LinkedIn](https://linkedin.com/in/royxlead) · [ORCID](https://orcid.org/0009-0009-6582-2295)**

<img src="https://capsule-render.vercel.app/api?type=waving&color=6366f1&height=80&section=footer" width="100%"/>

</div>
