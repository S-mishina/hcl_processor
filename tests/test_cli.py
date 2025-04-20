import pytest
from src.hcl_analytics.cli import parse_args
import sys

def test_parse_args(monkeypatch):
    test_args = ['prog', '--config_file', 'config.yaml', '--debug', 'true']
    monkeypatch.setattr(sys, 'argv', test_args)
    args = parse_args()
    assert args.config_file == 'config.yaml'
    assert args.debug == 'true'
