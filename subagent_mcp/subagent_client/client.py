import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx


class SubagentClient:
    def __init__(self):
        self.base_url = os.getenv("SUBAGENT_BASE_URL", "http://localhost:1234/v1")
        self.api_key = os.getenv("SUBAGENT_API_KEY", "lm-studio")
        self.default_model = os.getenv("SUBAGENT_DEFAULT_MODEL", "")
        self.max_tokens = int(os.getenv("SUBAGENT_MAX_TOKENS", "4000"))
        self.timeout = int(os.getenv("SUBAGENT_TIMEOUT", "120"))
        self.temperature = float(os.getenv("SUBAGENT_TEMPERATURE", "0.7"))
        self._optimal_workers = None
        env_workers = os.getenv("SUBAGENT_MAX_WORKERS")
        if env_workers:
            self._optimal_workers = int(env_workers)

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _resolve_model(self, model=None):
        """Resolve which model to use: explicit > env default > first loaded."""
        if model:
            return model
        if self.default_model:
            return self.default_model
        models = self.list_models()
        if not models:
            raise RuntimeError("No models available on the endpoint")
        return models[0]

    def ask(self, prompt, model=None, system_prompt=None, max_tokens=None,
            temperature=None, mcp_servers=None, mcp_pool=None):
        """Send a prompt to a local LLM and return the response.

        If mcp_servers and mcp_pool are provided, the LLM can call tools
        from those MCP servers in an agentic loop.
        """
        tools = None
        if mcp_servers and mcp_pool:
            tools = mcp_pool.get_tools_for_servers(mcp_servers)
        return self._respond(
            input=prompt,
            instructions=system_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools or None,
            mcp_pool=mcp_pool,
        )

    def ask_with_context(self, prompt, history, model=None, system_prompt=None,
                         max_tokens=None, temperature=None):
        """Send a prompt with conversation history to a local LLM."""
        input_items = []
        for msg in history:
            input_items.append({
                "type": "message",
                "role": msg["role"],
                "content": msg["content"],
            })
        input_items.append({
            "type": "message",
            "role": "user",
            "content": prompt,
        })
        return self._respond(
            input=input_items,
            instructions=system_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def ask_vision(self, prompt, image_url, model=None):
        """Send a prompt with an image to a vision-capable local model."""
        input_items = [{
            "type": "message",
            "role": "user",
            "content": [
                {"type": "input_image", "image_url": image_url},
                {"type": "input_text", "text": prompt},
            ],
        }]
        return self._respond(input=input_items, model=model)

    def list_models(self):
        """List available models on the local endpoint."""
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{self.base_url}/models",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return [m["id"] for m in resp.json().get("data", [])]

    def _respond(self, input, model=None, instructions=None, max_tokens=None,
                 temperature=None, tools=None, mcp_pool=None, max_turns=10):
        """Send a request to the Responses API and parse the result.

        If tools and mcp_pool are provided, runs an agentic loop: the LLM
        can call MCP tools and receive results until it produces a final
        text response or max_turns is reached.
        """
        resolved = self._resolve_model(model)
        body = {
            "model": resolved,
            "input": input,
            "temperature": temperature if temperature is not None else self.temperature,
        }
        if instructions:
            body["instructions"] = instructions
        if max_tokens or self.max_tokens:
            body["max_output_tokens"] = max_tokens or self.max_tokens
        if tools:
            body["tools"] = tools

        with httpx.Client(timeout=self.timeout) as http:
            for _ in range(max_turns):
                resp = http.post(
                    f"{self.base_url}/responses",
                    headers=self._headers(),
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()

                tool_calls = [
                    item for item in data.get("output", [])
                    if item.get("type") == "function_call"
                ]

                if not tool_calls or not mcp_pool:
                    return self._parse_response(data, resolved)

                # Execute tool calls and build follow-up input
                body["input"] = data["output"]
                for tc in tool_calls:
                    server_name, tool_name = mcp_pool.resolve_tool_call(tc["name"])
                    if server_name:
                        try:
                            import json
                            args = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
                            result = mcp_pool.call_tool(server_name, tool_name, args)
                        except Exception as e:
                            result = f"Error: {e}"
                    else:
                        result = f"Error: unknown tool '{tc['name']}'"
                    body["input"].append({
                        "type": "function_call_output",
                        "call_id": tc["call_id"],
                        "output": str(result),
                    })

        return self._parse_response(data, resolved)

    @property
    def optimal_workers(self):
        """Return the optimal worker count, auto-calibrating on first access."""
        if self._optimal_workers is None:
            result = self.benchmark_concurrency()
            self._optimal_workers = result["recommended"]
        return self._optimal_workers

    def ask_parallel(self, tasks, max_workers=None):
        """Run multiple ask() calls in parallel.

        Args:
            tasks: List of dicts, each with 'prompt' and optional 'model',
                   'system_prompt', 'max_tokens', 'temperature', 'label'.
            max_workers: Max concurrent requests (None = auto-detected optimal).

        Returns:
            Dict keyed by label (or index) with each task's result or error.
        """
        if max_workers is None:
            max_workers = self.optimal_workers
        results = {}

        def _run(task, label):
            return label, self.ask(
                task["prompt"],
                model=task.get("model"),
                system_prompt=task.get("system_prompt"),
                max_tokens=task.get("max_tokens"),
                temperature=task.get("temperature"),
            )

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {}
            for i, task in enumerate(tasks):
                label = task.get("label", str(i))
                futures[pool.submit(_run, task, label)] = label
            for future in as_completed(futures):
                label = futures[future]
                try:
                    _, result = future.result()
                    results[label] = result
                except Exception as e:
                    results[label] = {"error": str(e)}
        return results

    def benchmark_concurrency(self, model=None, max_level=4, prompt="Say hello in one word."):
        """Benchmark different concurrency levels to find the optimal worker count.

        Runs a short prompt at concurrency 1, 2, ..., max_level and measures
        total wall time and per-request average. Returns the level with the
        best throughput (requests/sec).

        Args:
            model: Model to benchmark (None = uses default/first available).
            max_level: Highest concurrency level to test.
            prompt: Short prompt used for each test request.

        Returns:
            Dict with 'results' (per-level stats), 'recommended' worker count,
            and 'benchmark_model' used.
        """
        resolved = self._resolve_model(model)
        bench_results = []
        for workers in range(1, max_level + 1):
            tasks = [
                {"prompt": prompt, "model": resolved, "label": str(i)}
                for i in range(workers)
            ]
            start = time.time()
            self.ask_parallel(tasks, max_workers=workers)
            elapsed = time.time() - start
            rps = workers / elapsed
            bench_results.append({
                "workers": workers,
                "requests": workers,
                "wall_time": round(elapsed, 1),
                "req_per_sec": round(rps, 3),
            })

        best = max(bench_results, key=lambda r: r["req_per_sec"])
        return {
            "results": bench_results,
            "recommended": best["workers"],
            "benchmark_model": resolved,
        }

    @staticmethod
    def _parse_response(data, requested_model=None):
        """Extract content and reasoning from a Responses API result."""
        content = ""
        reasoning = ""
        for item in data.get("output", []):
            if item.get("type") == "message":
                for block in item.get("content", []):
                    if block.get("type") == "output_text":
                        content += block.get("text", "")
            elif item.get("type") == "reasoning":
                for block in item.get("content", []):
                    if block.get("type") == "reasoning_text":
                        reasoning += block.get("text", "")
        return {
            "content": content.strip(),
            "reasoning": reasoning.strip(),
            "model": data.get("model", requested_model or ""),
            "usage": data.get("usage", {}),
        }
