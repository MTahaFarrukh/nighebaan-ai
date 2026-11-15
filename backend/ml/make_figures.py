"""Write report figures from published aggregate JSON. No inference or text."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
OUT = ROOT / "report" / "figures"


def _esc(text: str) -> str:
    """Escape XML text."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _write(name: str, svg: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(svg, encoding="utf-8")


def _bar_chart(title: str, rows: list[tuple[str, float]], y_label: str) -> str:
    width, height = 820, 420
    left, right, top, bottom = 90, 24, 48, 90
    plot_w = width - left - right
    plot_h = height - top - bottom
    ymax = max(1.0, max(v for _, v in rows) * 1.12)
    gap = 18
    bar_w = (plot_w - gap * (len(rows) + 1)) / max(len(rows), 1)
    bars = []
    labels = []
    values = []
    for i, (name, value) in enumerate(rows):
        x = left + gap + i * (bar_w + gap)
        h = plot_h * (value / ymax)
        y = top + plot_h - h
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
            f'fill="#1f4e79"/>'
        )
        labels.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{height - 36}" text-anchor="middle" '
            f'font-size="12" font-family="Segoe UI, Arial">{_esc(name)}</text>'
        )
        values.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" '
            f'font-size="11" font-family="Segoe UI, Arial">{value:.3f}</text>'
        )
    axis = (
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" '
        f'stroke="#333"/>'
        f'<line x1="{left}" y1="{top + plot_h}" x2="{width - right}" '
        f'y2="{top + plot_h}" stroke="#333"/>'
        f'<text x="18" y="{top + plot_h / 2}" transform='
        f'"rotate(-90 18 {top + plot_h / 2})" font-size="12" '
        f'font-family="Segoe UI, Arial">{_esc(y_label)}</text>'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<rect width="100%" height="100%" fill="white"/>'
        f'<text x="{width / 2}" y="28" text-anchor="middle" font-size="16" '
        f'font-family="Segoe UI, Arial" font-weight="600">{_esc(title)}</text>'
        f"{axis}{''.join(bars)}{''.join(labels)}{''.join(values)}</svg>\n"
    )


def _heatmap(
    title: str,
    matrix: list[list[int]],
    labels: list[str],
) -> str:
    n = len(labels)
    cell = 72
    left, top = 120, 70
    width = left + cell * n + 40
    height = top + cell * n + 50
    mx = max(max(row) for row in matrix) or 1
    cells = []
    for i, row in enumerate(matrix):
        cells.append(
            f'<text x="{left - 10}" y="{top + i * cell + cell / 2 + 4}" '
            f'text-anchor="end" font-size="12" font-family="Segoe UI, Arial">'
            f"{_esc(labels[i])}</text>"
        )
        cells.append(
            f'<text x="{left + i * cell + cell / 2}" y="{top - 12}" '
            f'text-anchor="middle" font-size="12" font-family="Segoe UI, Arial">'
            f"{_esc(labels[i])}</text>"
        )
        for j, value in enumerate(row):
            t = value / mx
            fill = f"rgb({int(255 - 140 * t)},{int(255 - 90 * t)},{int(255 - 30 * t)})"
            x = left + j * cell
            y = top + i * cell
            cells.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{fill}" '
                f'stroke="#fff"/>'
                f'<text x="{x + cell / 2}" y="{y + cell / 2 + 4}" text-anchor="middle" '
                f'font-size="13" font-family="Segoe UI, Arial">{value}</text>'
            )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<rect width="100%" height="100%" fill="white"/>'
        f'<text x="{width / 2}" y="28" text-anchor="middle" font-size="16" '
        f'font-family="Segoe UI, Arial" font-weight="600">{_esc(title)}</text>'
        f'<text x="{left + cell * n / 2}" y="{height - 12}" text-anchor="middle" '
        f'font-size="11">Predicted</text>'
        f'<text x="18" y="{top + cell * n / 2}" transform="rotate(-90 18 '
        f'{top + cell * n / 2})" font-size="11">True</text>'
        f"{''.join(cells)}</svg>\n"
    )


def _architecture() -> str:
    boxes = [
        (40, 40, 160, 48, "React web app"),
        (40, 120, 160, 48, "WhatsApp bridge"),
        (280, 80, 170, 48, "FastAPI backend"),
        (520, 20, 180, 44, "Extractors"),
        (520, 76, 180, 44, "Preprocess"),
        (520, 132, 180, 44, "Text ensemble"),
        (520, 188, 180, 44, "Expert rules"),
        (520, 244, 180, 44, "Static URL model"),
        (760, 132, 170, 56, "Risk engine"),
    ]
    rects = []
    for x, y, w, h, label in boxes:
        rects.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#f4f7fb" '
            f'stroke="#1f4e79"/>'
            f'<text x="{x + w / 2}" y="{y + h / 2 + 4}" text-anchor="middle" '
            f'font-size="13" font-family="Segoe UI, Arial">{_esc(label)}</text>'
        )
    arrows = [
        (200, 64, 280, 96),
        (200, 144, 280, 112),
        (450, 104, 520, 42),
        (450, 104, 520, 98),
        (450, 104, 520, 154),
        (450, 104, 520, 210),
        (450, 104, 520, 266),
        (700, 154, 760, 160),
        (700, 210, 760, 160),
        (700, 266, 760, 160),
    ]
    lines = []
    for x1, y1, x2, y2 in arrows:
        lines.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#1f4e79" '
            f'marker-end="url(#arrow)"/>'
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="320" '
        'viewBox="0 0 960 320">'
        "<defs><marker id=\"arrow\" markerWidth=\"8\" markerHeight=\"8\" "
        'refX="8" refY="4" orient="auto">'
        '<path d="M0,0 L8,4 L0,8 z" fill="#1f4e79"/></marker></defs>'
        '<rect width="100%" height="100%" fill="white"/>'
        '<text x="480" y="16" text-anchor="middle" font-size="16" '
        'font-family="Segoe UI, Arial" font-weight="600">'
        "Nigehbaan AI architecture</text>"
        f"{''.join(rects)}{''.join(lines)}</svg>\n"
    )


def generate(output_dir: Path | None = None) -> list[Path]:
    """Read published JSON and write SVG figures. Returns written paths."""
    global OUT
    previous = OUT
    if output_dir is not None:
        OUT = output_dir
    written: list[Path] = []
    try:
        comparison = json.loads((DOCS / "MODEL_COMPARISON_RESULTS.json").read_text())
        hybrid = json.loads((DOCS / "HYBRID_RESULTS.json").read_text())
        ablations = json.loads((DOCS / "ABLATION_RESULTS.json").read_text())
        final = json.loads((DOCS / "FINAL_RESULTS.json").read_text())

        def save(name: str, svg: str) -> None:
            _write(name, svg)
            written.append(OUT / name)

        save("fig1_architecture.svg", _architecture())
        save(
            "fig2_text_val_macro_f1.svg",
            _bar_chart(
                "Validation macro-F1 (text models)",
                [(row["name"], float(row["macro_f1"])) for row in comparison["models"]],
                "Macro-F1",
            ),
        )
        save(
            "fig3_hybrid_val_macro_f1.svg",
            _bar_chart(
                "Validation macro-F1 (ML / rules / hybrid)",
                [(row["name"], float(row["macro_f1"])) for row in hybrid["rows"]],
                "Macro-F1",
            ),
        )
        save(
            "fig4_ablation_val_macro_f1.svg",
            _bar_chart(
                "Validation macro-F1 (fixed LR ablations)",
                [(row["name"], float(row["macro_f1"])) for row in ablations["rows"]],
                "Macro-F1",
            ),
        )
        labels = list(final["text_test"]["ml"]["label_order"])
        save(
            "fig5_text_test_ml_confusion.svg",
            _heatmap(
                "Text test confusion (ML only)",
                final["text_test"]["ml"]["confusion_matrix"],
                labels,
            ),
        )
        save(
            "fig6_text_test_hybrid_confusion.svg",
            _heatmap(
                "Text test confusion (hybrid)",
                final["text_test"]["hybrid"]["confusion_matrix"],
                labels,
            ),
        )
        save(
            "fig7_url_test_confusion.svg",
            _heatmap(
                "URL test confusion (deployed GB)",
                final["url_test"]["confusion_matrix"],
                ["benign", "phishing"],
            ),
        )
        counts = final["text_splits"]["train"]["class_counts"]
        save(
            "fig8_train_class_counts.svg",
            _bar_chart(
                "Training class counts (frozen text split)",
                [(name, float(counts[name])) for name in ("normal", "abusive", "scam")],
                "Rows",
            ),
        )
        return written
    finally:
        OUT = previous


if __name__ == "__main__":
    paths = generate()
    for path in paths:
        print(path.relative_to(ROOT).as_posix())
