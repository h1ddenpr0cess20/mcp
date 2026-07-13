FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/opt/agent-venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        autoconf automake bash bat bc binutils build-essential bzip2 ca-certificates \
        clang cmake colordiff coreutils curl default-jdk diffutils dnsutils entr \
        expect fd-find ffmpeg file findutils fzf gawk gdb gh git git-lfs gnupg \
        golang-go graphviz imagemagick iproute2 iputils-ping jq less libmagic1 \
        libreoffice lsof lua5.4 make mariadb-client moreutils nano net-tools \
        netcat-openbsd nmap openssh-client openssl p7zip-full pandoc \
        parallel patch php-cli pkg-config poppler-utils postgresql-client procps \
        pv python3 python3-dev python3-pip python3-venv qpdf redis-tools ripgrep \
        rsync ruby-full rustc cargo shellcheck socat sqlite3 strace sysstat tar \
        tcpdump tesseract-ocr tmux traceroute tree unzip vim wget whois xz-utils \
        zip \
    && curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && python3 -m venv /opt/agent-venv \
    && /opt/agent-venv/bin/pip install --no-cache-dir \
        aiohttp beautifulsoup4 black chardet click cryptography csvkit dateparser \
        ebooklib fastapi gitpython httpx humanize hypothesis jinja2 loguru lxml \
        matplotlib mypy numpy openpyxl orjson pandas pdf2image pdfplumber pillow \
        plotly psutil pydantic pygments pymupdf pypdf pytest python-docx \
        python-dotenv python-pptx pyyaml reportlab requests rich ruff scipy \
        seaborn sqlalchemy tabulate tenacity tiktoken tqdm typer uvicorn watchdog \
    && npm install --global eslint prettier ts-node typescript \
    && rm -rf /var/lib/apt/lists/*

# Ubuntu packages expose these tools under collision-free names.
RUN ln -s /usr/bin/batcat /usr/local/bin/bat \
    && ln -s /usr/bin/fdfind /usr/local/bin/fd

WORKDIR /workspace

CMD ["sleep", "infinity"]
