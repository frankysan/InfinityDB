from infinity_army_data.cli import build_parser


def test_cli_build_parses() -> None:
    args = build_parser().parse_args(["build", "army.zip", "--compact"])
    assert args.command == "build"
    assert args.compact is True
