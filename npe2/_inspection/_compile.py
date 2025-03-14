from pathlib import Path
from typing import Iterator, List, Sequence, Tuple, Union, cast

from ..manifest import PluginManifest, contributions
from ..manifest.utils import merge_contributions
from ._setuputils import get_package_dir_info
from ._visitors import find_npe2_module_contributions


def find_packages(where: Union[str, Path] = ".") -> List[Path]:
    """Return all folders that have an __init__.py file"""
    return [p.parent for p in Path(where).resolve().rglob("**/__init__.py")]


def get_package_name(where: Union[str, Path] = ".") -> str:
    return get_package_dir_info(where).package_name


def compile(
    src_dir: Union[str, Path],
    dest: Union[str, Path, None] = None,
    packages: Sequence[str] = (),
    plugin_name: str = "",
) -> PluginManifest:
    """Compile plugin manifest from `src_dir`, where is a top-level repo.

    This will discover all the contribution points in the repo and output a manifest
    object

    Parameters
    ----------
    src_dir : Union[str, Path]
        Repo root. Should contain a pyproject or setup.cfg file.

    Returns
    -------
    PluginManifest
        Manifest including all discovered contribution points, combined with any
        existing contributions explicitly stated in the manifest.
    """

    src_path = Path(src_dir)
    assert src_path.exists(), f"src_dir {src_dir} does not exist"

    if dest is not None:
        pdest = Path(dest)
        suffix = pdest.suffix.lstrip(".")
        if suffix not in {"json", "yaml", "toml"}:
            raise ValueError(
                f"dest {dest!r} must have an extension of .json, .yaml, or .toml"
            )

    _packages = find_packages(src_path)
    if packages:
        _packages = [p for p in _packages if p.name in packages]

    if not plugin_name:
        plugin_name = get_package_name(src_path)

    contribs: List[contributions.ContributionPoints] = []
    for pkg_path in _packages:
        top_mod = pkg_path.name
        # TODO: add more tests with more complicated package structures
        # make sure we're not double detecting and/or missing stuff.
        for mod_path, mod_name in _iter_modules(pkg_path):
            contrib = find_npe2_module_contributions(
                mod_path,
                plugin_name=plugin_name,
                module_name=f"{top_mod}.{mod_name}" if mod_name else top_mod,
            )
            contribs.append(contrib)

    mf = PluginManifest(
        name=plugin_name,
        contributions=merge_contributions(contribs),
    )

    if dest is not None:
        manifest_string = getattr(mf, cast(str, suffix))(indent=2)
        pdest.write_text(manifest_string)

    return mf


def _iter_modules(path: Path) -> Iterator[Tuple[Path, str]]:
    """Return all python modules in path"""
    for p in path.glob("*.py"):
        yield p, "" if p.name == "__init__.py" else p.stem
