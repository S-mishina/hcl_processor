import sys

from hcl_processor.cli import parse_args


def test_parse_args(monkeypatch):
    test_args = ["prog", "--config_file", "config.yaml", "--debug", "true"]
    monkeypatch.setattr(sys, "argv", test_args)
    args = parse_args()
    assert args.config_file == "config.yaml"
    assert args.debug == "true"
