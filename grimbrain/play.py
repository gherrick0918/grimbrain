def run_play(pc, encounter=None, seed=None, script=None, json_mode=False, summary_only=False):
    """Wrapper around the CLI play entry point.

    This helper allows callers to invoke the play CLI directly from Python code
    while still supporting the ``--json`` and ``--summary-only`` flags.
    """
    from . import play_cli

    args = ["--pc", pc]
    if encounter:
        args.extend(["--encounter", str(encounter)])
    if seed is not None:
        args.extend(["--seed", str(seed)])
    if script:
        args.extend(["--script", script])
    if json_mode:
        args.append("--json")
    if summary_only:
        args.append("--summary-only")
    return play_cli.main(args)
