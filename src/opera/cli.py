"""Manage OPERA skills from the command line.

Usage
-----
::

    opera install skills [--target DIR] [--only name1,name2]
    opera list   skills
    opera show   skill <name>
"""

from __future__ import annotations

import argparse
import sys
import textwrap

from opera import __version__

# Subcommands


def _cmd_install_skills(args: argparse.Namespace) -> None:
    """Install the selected bundled skills into the requested directory.

    The parsed arguments provide the destination and an optional comma-separated
    list of skill names. The command reports each skill after installation.
    """
    from opera.skills_manager import SKILL_FILES, install_skills

    skills = None
    if args.only:
        skills = [s.strip() for s in args.only.split(",")]

    target = install_skills(target=args.target, skills=skills)

    installed = skills or list(SKILL_FILES)
    print(f"Installed {len(installed)} skill(s) to {target}")
    for name in installed:
        print(f"  - {name}")


def _cmd_list_skills(_args: argparse.Namespace) -> None:
    """Print a table of bundled skills, files, and descriptions."""
    from opera.skills_manager import list_skills

    skills = list_skills()
    header = f"{'Name':<25} {'File':<30} Description"
    sep = f"{'-' * 25} {'-' * 30} {'-' * 50}"
    print(header)
    print(sep)
    for s in skills:
        desc = textwrap.shorten(s["description"], width=50, placeholder="…")
        print(f"{s['name']:<25} {s['filename']:<30} {desc}")


def _cmd_show_skill(args: argparse.Namespace) -> None:
    """Write the named bundled skill to standard output as UTF-8 text.

    An unknown skill name is reported on standard output and causes the command
    to exit with status 1.
    """
    from opera.skills_manager import show_skill

    try:
        text = show_skill(args.name)
        sys.stdout.buffer.write(text.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")
    except KeyError as exc:
        print(str(exc))
        sys.exit(1)


def _cmd_sync_api(_args: argparse.Namespace) -> None:
    """Synchronise generated API sections in the bundled skill files.

    The command reports changed files, or confirms that the generated sections
    are current. Synchronisation errors are written to standard error and cause
    the command to exit with status 1.
    """
    from opera.skill_api import sync_api_sections

    try:
        changed = sync_api_sections()
    except Exception as exc:
        print(f"opera skills sync-api: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    for path in changed:
        print(f"Updated {path}")
    if not changed:
        print("Skill API sections are current.")


# Argument parser


def build_parser() -> argparse.ArgumentParser:
    """Build and return the parser for all OPERA CLI commands.

    The parser registers skill installation, listing, display, and API
    synchronisation commands and attaches each command's handler.
    """
    parser = argparse.ArgumentParser(
        prog="opera",
        description="OPERA ecosystem CLI — manage skills and dependencies.",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # Install skills or dependencies.
    install_parser = sub.add_parser("install", help="Install skills or dependencies")
    install_sub = install_parser.add_subparsers(dest="install_target", required=True)

    # Install skills.
    install_skills_parser = install_sub.add_parser(
        "skills", help="Copy OPERA skill files to a target directory"
    )
    install_skills_parser.add_argument(
        "--target",
        default=None,
        help="Destination directory (default: .claude/skills or .github/skills)",
    )
    install_skills_parser.add_argument(
        "--only",
        default=None,
        help="Comma-separated list of skill names to install (default: all)",
    )
    install_skills_parser.set_defaults(func=_cmd_install_skills)

    # Synchronise generated API sections in the repository checkout.
    skills_command_parser = sub.add_parser(
        "skills", help="Maintain bundled skill resources"
    )
    skills_sub = skills_command_parser.add_subparsers(
        dest="skills_command", required=True
    )
    sync_api_parser = skills_sub.add_parser(
        "sync-api", help="Update generated skill API sections"
    )
    sync_api_parser.set_defaults(func=_cmd_sync_api)

    # List available resources.
    list_parser = sub.add_parser("list", help="List available resources")
    list_sub = list_parser.add_subparsers(dest="list_target", required=True)

    list_skills_parser = list_sub.add_parser("skills", help="List bundled skills")
    list_skills_parser.set_defaults(func=_cmd_list_skills)

    # Show a resource.
    show_parser = sub.add_parser("show", help="Show a resource")
    show_sub = show_parser.add_subparsers(dest="show_target", required=True)

    show_skill_parser = show_sub.add_parser("skill", help="Print a skill file")
    show_skill_parser.add_argument("name", help="Skill short-name (e.g. opera, bvar)")
    show_skill_parser.set_defaults(func=_cmd_show_skill)

    return parser


def main(argv: list[str] | None = None) -> None:
    """Parse arguments and dispatch to the selected OPERA CLI command.

    When ``argv`` is omitted, arguments are read from the process command line.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
