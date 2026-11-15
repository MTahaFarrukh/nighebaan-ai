"""Report figures are generated from published JSON only."""

from pathlib import Path

from ml.make_figures import generate


def test_make_figures_writes_svg(tmp_path: Path) -> None:
    written = generate(output_dir=tmp_path)
    names = {path.name for path in written}
    assert "fig1_architecture.svg" in names
    assert "fig5_text_test_ml_confusion.svg" in names
    for path in written:
        text = path.read_text(encoding="utf-8")
        assert "<svg" in text
        assert "xmlns" in text
