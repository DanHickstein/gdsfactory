from __future__ import annotations

import pathlib
import re
from difflib import unified_diff
from enum import Enum
from typing import Annotated, Optional

import typer
from rich import print as pprint

from gdsfactory import show as _show
from gdsfactory.config import print_version_pdks, print_version_plugins
from gdsfactory.difftest import diff
from gdsfactory.install import install_gdsdiff, install_klayout_package
from gdsfactory.read.from_updk import from_updk
from gdsfactory.watch import watch as _watch

app = typer.Typer()


class Migration(str, Enum):
    upgrade7to8 = "7to8"


@app.command()
def layermap_to_dataclass(
    filepath: str,
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion"),
) -> None:
    """Converts KLayout LYP to a dataclass."""
    from gdsfactory.technology import lyp_to_dataclass

    filepath_lyp = pathlib.Path(filepath)
    filepath_py = filepath_lyp.with_suffix(".py")
    if not filepath_lyp.exists():
        raise FileNotFoundError(f"{filepath_lyp} not found")
    if not force and filepath_py.exists():
        raise FileExistsError(f"found {filepath_py}")
    lyp_to_dataclass(lyp_filepath=filepath_lyp)


@app.command()
def write_cells(gdspath: str, dirpath: str = "") -> None:
    """Write each all level cells into separate GDS files."""
    from gdsfactory.write_cells import write_cells as write_cells_to_separate_gds

    write_cells_to_separate_gds(gdspath=gdspath, dirpath=dirpath)


@app.command()
def merge_gds(dirpath: str = "", gdspath: str = "") -> None:
    """Merges GDS cells from a directory into a single GDS."""
    from gdsfactory.read.from_gdspaths import from_gdsdir

    dirpath = dirpath or pathlib.Path.cwd()
    gdspath = gdspath or pathlib.Path.cwd() / "merged.gds"

    dirpath = pathlib.Path(dirpath)

    c = from_gdsdir(dirpath=dirpath)
    c.write_gds(gdspath=gdspath)
    c.show()


@app.command()
def watch(
    path: str = str(pathlib.Path.cwd()),
    pdk: str = typer.Option(None, "--pdk", "-pdk", help="PDK name"),
) -> None:
    """Filewatch a folder for changes in *.py or *.pic.yml files."""
    path = pathlib.Path(path)
    path = path.parent if path.is_dir() else path
    _watch(str(path), pdk=pdk)


@app.command()
def show(filename: str) -> None:
    """Show a GDS file using klive."""
    _show(filename)


@app.command()
def gds_diff(gdspath1: str, gdspath2: str, xor: bool = False) -> None:
    """Show boolean difference between two GDS files."""
    diff(gdspath1, gdspath2, xor=xor)


@app.command()
def install_klayout_genericpdk() -> None:
    """Install Klayout generic PDK."""
    install_klayout_package()


@app.command()
def install_git_diff() -> None:
    """Install git diff."""
    install_gdsdiff()


@app.command()
def print_plugins() -> None:
    """Show installed plugin versions."""
    print_version_plugins()


@app.command()
def print_pdks() -> None:
    """Show installed PDK versions."""
    print_version_pdks()


@app.command(name="from_updk")
def from_updk_command(filepath: str, filepath_out: str = "") -> None:
    """Writes a PDK in python from uPDK YAML spec."""
    filepath = pathlib.Path(filepath)
    filepath_out = filepath_out or filepath.with_suffix(".py")
    from_updk(filepath, filepath_out=filepath_out)


@app.command(name="text_from_pdf")
def text_from_pdf_command(filepath: str) -> None:
    """Converts a PDF to text."""
    import pdftotext

    with open(filepath, "rb") as f:
        pdf = pdftotext.PDF(f)

    # Read all the text into one string
    text = "\n".join(pdf)
    filepath = pathlib.Path(filepath)
    f = filepath.with_suffix(".md")
    f.write_text(text)


@app.command()
def migrate(
    migration: Annotated[
        Migration, typer.Option(case_sensitive=False, help="Choices of migrations.")
    ],
    input: Annotated[pathlib.Path, typer.Argument(help="Input folder or file.")],
    output: Annotated[
        Optional[pathlib.Path],  # noqa: UP007
        typer.Argument(
            help="Output folder or file. If inplace is set, this argument will be ignored"
        ),
    ] = None,
    inplace: Annotated[
        bool,
        typer.Option(
            "--inplace",
            "-i",
            help="If set, the migration will overwrite the input folder"
            " or file and ignore any given output path.",
        ),
    ] = False,
) -> None:
    to_be_replaced = {
        "center",
        "mirror",
        "move",
        "movex",
        "movey",
        "rotate",
        "size_info",
        "x",
        "xmin",
        "xmax",
        "xsize",
        "y",
        "ymin",
        "ymax",
        "ysize",
    }
    input = input.resolve()
    if output is None:
        if not inplace:
            raise ValueError("If inplace is not set, an output directory must be set.")
        output = input
    output.resolve()
    pattern1 = re.compile(
        r"\b(" + "|".join(r"d\." + _r for _r in to_be_replaced) + r")\b"
    )
    pattern2 = re.compile(r"\b(" + "|".join(to_be_replaced) + r")\b")
    replacement = r"d\1"

    if not input.is_dir():
        if output.is_dir():
            output = output / input.name
        elif output.suffix == ".py":
            output.parent.mkdir(parents=True, exist_ok=True)
        else:
            output = output / input.name
            output.parent.mkdir(parents=True, exist_ok=True)

        with open(input, encoding="utf-8") as file:
            content = file.read()
        new_content = pattern2.sub(replacement, pattern1.sub(replacement, content))
        if output == input:
            if content != new_content:
                with open(output, "w", encoding="utf-8") as file:
                    file.write(new_content)
                pprint(f"Updated [bold violet]{output}[/]")
                pprint(
                    "\n".join(
                        unified_diff(
                            a=content.splitlines(),
                            b=new_content.splitlines(),
                            fromfile=str(input.resolve()),
                            tofile=str(output.resolve()),
                        )
                    )
                )
        else:
            with open(output, "w", encoding="utf-8") as file:
                file.write(new_content)
            if content != new_content:
                pprint(f"Updated [bold violet]{output}[/]")
                pprint(
                    "\n".join(
                        unified_diff(
                            a=content,
                            b=new_content,
                            fromfile=str(input),
                            tofile=str(output),
                        )
                    )
                )
    else:
        if output != input:
            for inp in input.rglob("*.py"):
                with open(inp, encoding="utf-8") as file:
                    content = file.read()
                new_content = pattern2.sub(
                    replacement, pattern1.sub(replacement, content)
                )
                out = output / inp.relative_to(input)
                out.parent.mkdir(parents=True, exist_ok=True)
                with open(out, "w", encoding="utf-8") as file:
                    file.write(new_content)
                if content != new_content:
                    pprint(f"Updated [bold violet]{out}[/]")
                    pprint(
                        "\n".join(
                            unified_diff(
                                a=content.splitlines(),
                                b=new_content.splitlines(),
                                fromfile=str(inp.resolve()),
                                tofile=str(out.resolve()),
                            )
                        )
                    )
        else:
            for inp in input.rglob("*.py"):
                with open(inp, encoding="utf-8") as file:
                    content = file.read()
                new_content = pattern2.sub(
                    replacement, pattern1.sub(replacement, content)
                )
                if content != new_content:
                    out = output / inp.relative_to(input)
                    out.parent.mkdir(parents=True, exist_ok=True)
                    with open(out, "w", encoding="utf-8") as file:
                        file.write(new_content)
                    pprint(f"Updated [bold violet]{out}[/]")
                    pprint(
                        "\n".join(
                            unified_diff(
                                a=content.splitlines(),
                                b=new_content.splitlines(),
                                fromfile=str(inp.resolve()),
                                tofile=str(out.resolve()),
                            )
                        )
                    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:  # No arguments provided
        sys.argv.append("--help")
    app()
