"""Demo：用样例菜单 + 内置 classic 模板渲染成 PDF。

    docker compose exec backend python -m app.menu.demo /app/data/menu_demo.pdf
"""

import sys

from app.menu.render import render_pdf, sample_spec, seed_templates_data


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else "/app/data/menu_demo.pdf"
    src = next(t["html"] for t in seed_templates_data() if t["key"] == "classic")
    data = render_pdf(sample_spec(), src)
    with open(out, "wb") as f:
        f.write(data)
    print(f"wrote {out} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
