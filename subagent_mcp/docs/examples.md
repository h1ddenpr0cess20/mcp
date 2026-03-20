# Usage Examples

Practical workflows showing how to use the Subagent MCP server. Each scenario includes sample questions you can ask an AI assistant connected to this server.

---

## Table of Contents

- [Basic Question](#basic-question)
- [Using a System Prompt](#using-a-system-prompt)
- [Multi-Turn Conversation](#multi-turn-conversation)
- [Agent with Web Search](#agent-with-web-search)
- [Agent with Shell Access](#agent-with-shell-access)
- [Multiple Specialist Agents](#multiple-specialist-agents)
- [Model Comparison](#model-comparison)
- [Concurrency Benchmarking](#concurrency-benchmarking)
- [Sample Questions for an AI Assistant](#sample-questions-for-an-ai-assistant)

---

## Basic Question

**Goal:** Ask a local LLM a simple question.

**Tool call:**

```
ask_subagent("What is the Model Context Protocol?")
```

Returns the LLM's response with content, reasoning (if applicable), model used, and token usage.

---

## Using a System Prompt

**Goal:** Control the agent's behavior with a system prompt.

**Tool call:**

```
ask_subagent(
    "Explain Python decorators",
    system_prompt="You are a Python tutor. Use simple language and short examples."
)
```

---

## Multi-Turn Conversation

**Goal:** Have a back-and-forth conversation where the LLM remembers previous messages.

**First turn:**

```
ask_subagent_with_context(
    "What are the three laws of thermodynamics?",
    conversation_id="thermo-101"
)
```

**Follow-up:**

```
ask_subagent_with_context(
    "Explain the second one in more detail.",
    conversation_id="thermo-101"
)
```

The server tracks the full conversation history for each ID.

---

## Agent with Web Search

**Goal:** Create an agent that can search the web and read pages.

**Setup:**

```
create_agent(
    name="researcher",
    system_prompt="You are a research assistant. Search the web to find accurate, up-to-date information. Cite your sources.",
    mcp_servers=["web"]
)
```

**Use:**

```
ask_agent("researcher", "What are the latest developments in quantum computing?")
```

The agent will call `web_search`, optionally `fetch_url` to read full pages, and synthesize an answer.

---

## Agent with Shell Access

**Goal:** Create an agent that can run commands in a sandbox.

**Setup:**

```
create_agent(
    name="devops",
    system_prompt="You are a systems administrator. Use shell commands to investigate and solve problems. Be careful with destructive operations.",
    mcp_servers=["shell"]
)
```

**Use:**

```
ask_agent("devops", "Check disk usage and find the largest files in /var/log")
```

The agent will call `execute_command` with appropriate shell commands and report findings.

---

## Multiple Specialist Agents

**Goal:** Get different perspectives on the same question from differently-configured agents.

**Setup:**

```
create_agent(name="optimist", system_prompt="You are optimistic. Focus on opportunities and positive outcomes.", mcp_servers=["web"])
create_agent(name="critic", system_prompt="You are a critical thinker. Focus on risks, downsides, and what could go wrong.", mcp_servers=["web"])
create_agent(name="pragmatist", system_prompt="You are practical. Focus on actionable steps and realistic expectations.", mcp_servers=["web"])
```

**Use:**

```
ask_agents_parallel(
    "Should a startup adopt AI-generated code in production?",
    agent_names=["optimist", "critic", "pragmatist"]
)
```

All three agents respond in parallel with their different perspectives.

---

## Model Comparison

**Goal:** Compare how different loaded models answer the same question.

**Tool call:**

```
ask_multiple("Write a haiku about programming.")
```

Queries all loaded models in parallel and returns each model's response side by side.

**With specific models:**

```
ask_multiple(
    "Explain recursion in one sentence.",
    models=["mistral-7b", "llama-3-8b", "phi-3-mini"]
)
```

---

## Concurrency Benchmarking

**Goal:** Find the optimal number of parallel workers for your hardware.

**Tool call:**

```
benchmark_concurrency(max_level=6)
```

Tests concurrency levels 1 through 6 and returns throughput stats and a recommendation.

---

## Sample Questions for an AI Assistant

**Basic delegation**
- Ask the local LLM to summarize this text: [paste text]
- Have the subagent write a Python function that validates email addresses.
- Ask the local model what it knows about the Rust programming language.

**Research with web tools**
- Create a researcher agent with web access and have it find the latest news about SpaceX.
- Search the web for Python packaging best practices and summarize what you find.
- Find and read the FastMCP documentation, then explain how to create a server.

**DevOps with shell tools**
- Create a devops agent and have it check system resource usage in the sandbox.
- Run a shell command to list all running processes sorted by memory usage.
- Write a bash script in the sandbox that monitors disk usage and save it.

**Analysis and comparison**
- Ask three different models to explain quantum entanglement and compare their answers.
- Create specialist agents (security reviewer, performance analyst, UX designer) and get their take on a product feature.
- Benchmark concurrency to find the best parallel setting for my hardware.
