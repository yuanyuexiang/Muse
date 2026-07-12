FROM python:3.12-slim-bookworm

WORKDIR /app

# WeasyPrint 原生依赖：libpango（自动带 cairo/gdk-pixbuf/harfbuzz）+ 中文字体 + poppler。
# 部分构建网络取不到 Debian 官方源(deb.debian.org)，故先把 apt 源换成阿里云镜像
# （与 LLM 同一可达网络）。仍用 `|| echo` 兜底：万一装不上也不让镜像构建失败，
# 此时仅 PDF 导出不可用(HTML 预览/提取/审校不受影响)。
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g; s|security.debian.org|mirrors.aliyun.com|g' \
        /etc/apt/sources.list.d/debian.sources 2>/dev/null || true; \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g; s|security.debian.org|mirrors.aliyun.com|g' \
        /etc/apt/sources.list 2>/dev/null || true; \
    ( apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 fonts-noto-cjk fonts-dejavu-core poppler-utils ) \
      || echo "WARN: 渲染系统库未安装，PDF 导出将不可用（HTML 预览仍可）"; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
