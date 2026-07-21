# Usage Examples

Practical workflows showing how to use the Colab Shell MCP server. Every tool
call runs against the Google Colab runtime the server is bound to.

---

## Table of Contents

- [Running Commands](#running-commands)
- [Using the GPU](#using-the-gpu)
- [File Operations](#file-operations)
- [Transferring Files](#transferring-files)
- [System Monitoring](#system-monitoring)
- [Fetching Generated Files](#fetching-generated-files)
- [Sample Questions for an AI Assistant](#sample-questions-for-an-ai-assistant)

---

## Running Commands

**Goal:** Execute shell commands in the Colab runtime.

**Install a Python package:**

```
execute_command("pip install -q transformers accelerate")
```

**Install a system package:**

```
execute_command("apt-get install -y ffmpeg")
```

**Multi-statement:**

```
execute_command("cd /content && git clone https://github.com/example/repo && cd repo && pip install -e .")
```

**Sample prompts to an AI assistant:**

> Clone my repo into `/content` and install its dependencies.

> Run the test suite and show me any failures.

> Check the CUDA version available in this runtime.

---

## Using the GPU

**Goal:** Confirm and use the attached accelerator.

**Check the GPU:**

```
execute_command("nvidia-smi")
```

**Confirm PyTorch sees it:**

```
execute_command("python3 -c 'import torch; print(torch.cuda.get_device_name(0))'")
```

**Sample prompts to an AI assistant:**

> What GPU is attached to this runtime and how much VRAM does it have?

> Fine-tune the model in `/content/train.py` and report the final loss.

---

## File Operations

**Goal:** Read, write, and list files in the runtime without transferring them.

**List a directory:**

```
list_directory("/content")
```

**Read a file:**

```
read_file("/content/config.yaml")
```

**Write a script:**

```
write_file("/content/run.sh", "#!/bin/bash\npython3 train.py --epochs 3\n")
```

**Sample prompts to an AI assistant:**

> List everything under `/content`.

> Read `/content/config.yaml` and summarise the settings.

> Write a training script to `/content/run.sh`.

---

## Transferring Files

**Goal:** Move files between the MCP server host and the runtime.

**Upload a local file:**

```
upload_file("/home/user/data.csv", "/content/data.csv")
```

**Download a file from the runtime:**

```
download_file("/content/results.json", "/tmp/results.json")
```

**Sample prompts to an AI assistant:**

> Upload my local `/tmp/input.csv` into `/content`.

> Download the trained checkpoint at `/content/model.safetensors` to my machine.

---

## System Monitoring

**Goal:** Check the health, resources, and accelerator of the runtime.

**Tool call:**

```
get_system_info()
```

Returns hostname, uptime, kernel, Python version, attached GPU, memory usage,
and disk usage in one call.

**Sample prompts to an AI assistant:**

> What are the memory and disk usage right now, and is a GPU attached?

> How long has this runtime been running?

---

## Fetching Generated Files

**Goal:** Retrieve a file generated in the runtime and get a URL to download it.

**Typical sequence:**

1. Generate the file:

    ```
    execute_command("cd /content && python3 export_report.py")
    ```

2. Fetch it via HTTP:

    ```
    fetch_file("/content/report.pdf")
    ```

Returns a URL like `http://127.0.0.1:9631/files/<file_id>/content` that the
client can open directly.

**Sample prompts to an AI assistant:**

> Run my report generator and give me a link to download the output PDF.

> Zip up `/content/exports/` and fetch it so I can download it.

> Save the trained model and fetch it so I can grab the weights.

---

## Sample Questions for an AI Assistant

**Development**
- Clone my project into `/content`, install dependencies, and run the tests.
- Build the package and tell me about any errors.
- Check the git log for the last 10 commits in `/content/repo`.

**Machine learning**
- Confirm the GPU, then fine-tune the model in `/content/train.py`.
- Run inference on the sample inputs and fetch the results.
- Convert the checkpoint to GGUF and give me a download link.

**Data processing**
- Run my ETL script and fetch the output CSV when it's done.
- Convert the video to MP4 with ffmpeg and fetch it.
- Generate a PDF report from the data and give me a download link.

**System**
- What's the disk and memory usage, and what GPU is attached?
- Show the last 20 lines of the training log.
