"""Native standalone Hermes plugin entry point."""
from .guardian.runtime import Guardian


def register(ctx):
    def data_dir():
        from plugins.plugin_storage import plugin_data_dir
        return plugin_data_dir("hermes-guardian")

    guardian = Guardian(ctx, data_dir)
    ctx.register_hook("pre_tool_call", guardian.pre_tool_call)

    from .guardian.cli import setup, handle
    ctx.register_cli_command(
        "guardian", "Propose, simulate, review and explicitly activate Guardian policies",
        setup, lambda args: handle(args, ctx),
    )
