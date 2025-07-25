import sys

from hcl_processor.cli import parse_args


def test_parse_args_with_debug(monkeypatch):
    """Test parse_args with debug flag enabled"""
    test_args = ["prog", "--config_file", "config.yaml", "--debug"]
    monkeypatch.setattr(sys, "argv", test_args)
    args = parse_args()
    assert args.config_file == "config.yaml"
    assert args.debug is True


def test_parse_args_without_debug(monkeypatch):
    """Test parse_args without debug flag"""
    test_args = ["prog", "--config_file", "config.yaml"]
    monkeypatch.setattr(sys, "argv", test_args)
    args = parse_args()
    assert args.config_file == "config.yaml"
    assert args.debug is False
