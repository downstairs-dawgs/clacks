import sys
from collections.abc import Sequence

from slack_clacks.cli import generate_cli
from slack_clacks.skill.status import check_skill_install_status


def should_check_skill_warning(argv: Sequence[str]) -> bool:
    """Return whether this invocation should perform stale skill checks."""
    if not argv:
        return False
    return all(flag not in argv for flag in ("-h", "--help", "--version"))


def warn_if_skill_install_is_outdated(argv: Sequence[str]) -> None:
    """Print a warning when the active installed skill is stale."""
    if not should_check_skill_warning(argv):
        return

    status = check_skill_install_status()
    if status is None or not status.is_outdated:
        return

    print(
        "Warning: installed clacks skill is outdated at "
        f"{status.path}. Reinstall with: {status.reinstall_command}",
        file=sys.stderr,
    )


def main(argv: Sequence[str] | None = None) -> None:
    args_list = list(sys.argv[1:] if argv is None else argv)
    warn_if_skill_install_is_outdated(args_list)
    parser = generate_cli()
    args = parser.parse_args(args_list)
    args.func(args)


if __name__ == "__main__":
    main()
