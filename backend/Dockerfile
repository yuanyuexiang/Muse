FROM python:3.12-slim-bookworm

WORKDIR /app

# WeasyPrint 原生依赖：libpango 会自动带上 cairo/gdk-pixbuf/harfbuzz。
# 另加中文字体 + poppler。用 `|| true` 兜底：某些构建网络取不到 Debian 主索引时
# 也不让镜像构建失败——此时仅 PDF 导出不可用(HTML 预览/提取/审校不受影响)，
# 正常网络会装上、PDF 即可用。
RUN (apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 \
      fonts-noto-cjk fonts-dejavu-core poppler-utils) \
    || echo "WARN: 渲染系统库未安装，PDF 导出将不可用（HTML 预览仍可）" \
 ; rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
