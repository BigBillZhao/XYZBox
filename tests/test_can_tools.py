import importlib.util
import itertools
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


up = load("can_up", "tools/can_up.py")
probe = load("can_probe", "tools/can_probe.py")
CONFIG = {"channels": ["can0", "can1"], "bitrate": 1000000, "sample_point": .75}


class CanSetupTests(unittest.TestCase):
    def test_unselected_channel_is_not_touched(self):
        run, output = Mock(), Mock()
        up.configure("can3", CONFIG, run, output)
        run.assert_not_called()
        output.assert_not_called()

    def test_live_different_config_is_rejected(self):
        link = {"flags": ["UP"], "mtu": 72,
                "linkinfo": {"info_kind": "can", "info_data": {"bittiming": {"bitrate": 1000000}}}}
        run = Mock()
        with self.assertRaises(RuntimeError):
            up.configure("can0", CONFIG, run, Mock(return_value=json.dumps([link])))
        run.assert_not_called()

    def test_down_can_configured_without_cansend(self):
        link = {"flags": [], "mtu": 16, "linkinfo": {"info_kind": "can"}}
        run = Mock()
        up.configure("can0", CONFIG, run, Mock(return_value=json.dumps([link])))
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0][-2:], ["fd", "off"])
        self.assertEqual(run.call_args_list[1].args[0][-1], "up")

    def test_invalid_bitrate_rejected_before_ip(self):
        with self.assertRaises(ValueError):
            up.validate_config({**CONFIG, "bitrate": 500000})

    def test_rx_separated_from_errors_and_echo(self):
        messages = iter([
            SimpleNamespace(is_error_frame=False, is_rx=False),
            SimpleNamespace(is_error_frame=True, arbitration_id=0x88, data=bytes(8)),
            SimpleNamespace(is_error_frame=False, is_rx=True, arbitration_id=0x2A1, data=bytes(8)),
        ])
        bus = Mock()
        bus.recv.side_effect = lambda **kwargs: next(messages, None)
        bus.__enter__ = Mock(return_value=bus)
        bus.__exit__ = Mock(return_value=False)
        with patch.object(probe.can, "Bus", return_value=bus), patch.object(probe.time, "monotonic", side_effect=itertools.count(0, .03)):
            result = probe.probe("can0", seconds=1.5)
        self.assertEqual(result["real_rx_frames"], 1)
        self.assertEqual(result["local_tx_echoes_excluded"], 1)
        self.assertEqual(result["error_frames"], 1)
        bus.send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
