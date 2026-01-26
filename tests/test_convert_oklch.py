import importlib.util
import os
import re


def load_module():
    here = os.path.dirname(__file__)
    repo_root = os.path.abspath(os.path.join(here, '..'))
    path = os.path.join(repo_root, 'scripts', 'convert_css_colors_to_oklch.py')
    spec = importlib.util.spec_from_file_location('convert_oklch', path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_hex_and_alpha():
    mod = load_module()
    out = mod.make_replacement_for_match('#fff')
    assert out.startswith('oklch(')
    assert '/' not in out

    out2 = mod.make_replacement_for_match('#ff000080')
    assert out2.startswith('oklch(')
    assert ' / ' in out2


def test_rgb_and_rgba():
    mod = load_module()
    o1 = mod.make_replacement_for_match('rgb(255,0,0)')
    assert o1.startswith('oklch(')
    assert '/' not in o1

    o2 = mod.make_replacement_for_match('rgba(255,0,0,0.5)')
    assert o2.startswith('oklch(')
    assert ' / 0.5' in o2


def test_rgb_percent_and_slash_alpha():
    mod = load_module()
    o = mod.make_replacement_for_match('rgb(100% 0% 0% / 50%)')
    assert o.startswith('oklch(')
    assert ' / ' in o


def test_hsl_variants():
    mod = load_module()
    o = mod.make_replacement_for_match('hsl(240 100% 50%)')
    assert o.startswith('oklch(')
    o2 = mod.make_replacement_for_match('hsla(240,100%,50%,0.25)')
    assert ' / 0.25' in o2


def test_named_and_transparent():
    mod = load_module()
    o = mod.make_replacement_for_match('rebeccapurple')
    assert o.startswith('oklch(')
    t = mod.make_replacement_for_match('transparent')
    assert ' / 0.0' in t


def test_output_format_regex():
    mod = load_module()
    sample = mod.make_replacement_for_match('#123456')
    pat = re.compile(r"^oklch\(\d{1,3}(?:\.\d+)?% \d+(?:\.\d+)? \d+deg(?: / \d+(?:\.\d+)?)?\)$")
    assert pat.match(sample)


def test_process_file_fixture(tmp_path):
    mod = load_module()
    fixture = os.path.join(os.path.dirname(__file__), 'fixtures', 'colors_fixture.css')
    # read fixture and run process_file
    changed, _tot, new, _changes = mod.process_file(fixture)
    assert changed == 1
    assert isinstance(new, str)
    # must have replaced tokens
    assert 'oklch(' in new
