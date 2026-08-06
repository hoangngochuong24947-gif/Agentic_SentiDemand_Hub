"""Memory-footprint regression tests for the Hub server.

Importing ``comment_analyzer.visualization.gallery`` must NOT pull in the heavy
analysis stack (pandas, scikit-learn, gensim, jieba, snownlp). That eager
import chain was the root cause of the deployed Hub server's ~640 MB RSS on a
1.6 GB host. These tests run in a fresh subprocess because the main pytest
process already imports those libraries via other test modules.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
_HEAVY_MODULES = ("pandas", "numpy", "sklearn", "gensim", "jieba", "snownlp")


def _run_in_fresh_python(code: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_SRC)
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        env=env,
    )


def test_gallery_import_does_not_load_heavy_stack():
    """The gallery server process must stay light at import time."""
    result = _run_in_fresh_python(
        """
        import sys
        import comment_analyzer.visualization.gallery  # noqa: F401

        loaded = [m for m in {!r} if m in sys.modules]
        print("loaded:", loaded)
        assert not loaded, f"gallery import pulled heavy modules: {{loaded}}"
        """.format(_HEAVY_MODULES)
    )
    assert result.returncode == 0, f"subprocess failed:\n{result.stdout}\n{result.stderr}"
    assert "loaded: []" in result.stdout


def test_gallery_comment_pipeline_is_lazy_and_monkeypatchable():
    """CommentPipeline is reachable via the gallery module but imported lazily.

    Tests monkeypatch ``gallery.CommentPipeline`` to fake out uploads; that
    attribute must take precedence over the lazy import.
    """
    result = _run_in_fresh_python(
        """
        import sys
        import comment_analyzer.visualization.gallery as gallery

        class Fake:
            pass

        gallery.CommentPipeline = Fake
        from comment_analyzer.visualization.gallery import _pipeline_class
        assert _pipeline_class() is Fake, "monkeypatched pipeline should win"

        del gallery.CommentPipeline
        pipeline_cls = gallery.CommentPipeline
        assert pipeline_cls is not Fake, "lazy import should resolve the real class"
        assert "pandas" in sys.modules, "resolving the pipeline should load pandas"
        print("lazy + monkeypatch OK")
        """
    )
    assert result.returncode == 0, f"subprocess failed:\n{result.stdout}\n{result.stderr}"
    assert "lazy + monkeypatch OK" in result.stdout


def test_runtime_limits_set_thread_caps_before_numeric_libs():
    """Importing comment_analyzer._limits caps BLAS/OpenMP threads."""
    result = _run_in_fresh_python(
        """
        import os
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
            os.environ.pop(name, None)

        import comment_analyzer._limits  # noqa: F401

        assert os.environ.get("OMP_NUM_THREADS") == "1"
        import numpy  # noqa: F401
        print("limits OK")
        """
    )
    assert result.returncode == 0, f"subprocess failed:\n{result.stdout}\n{result.stderr}"
    assert "limits OK" in result.stdout
