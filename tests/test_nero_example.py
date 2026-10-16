import importlib.util
from pathlib import Path
from types import SimpleNamespace
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("nero_example", ROOT / "examples/nero_joint_control.py")
example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example)


class FakeArm:
    def __init__(self, firmware="1.12", fault=0, enable_ok=True):
        self.firmware, self.fault, self.enable_ok = firmware, fault, enable_ok
        self.calls = []
        self.q = [0.0] * 7

    def connect(self): self.calls.append("connect")
    def disconnect(self): self.calls.append("disconnect")
    def get_firmware(self, **kwargs):
        self.calls.append("firmware_query")
        return {"software_version": self.firmware} if self.firmware else None
    def get_joint_angles(self): return SimpleNamespace(msg=list(self.q), timestamp=time.time())
    def get_arm_status(self): return SimpleNamespace(msg=SimpleNamespace(arm_status=self.fault, ctrl_mode=1))
    def enable(self):
        self.calls.append("enable")
        return self.enable_ok
    def set_speed_percent(self, speed): self.calls.append(("speed", speed))
    def move_j(self, target):
        self.calls.append(("move_j", list(target)))
        self.q = list(target)


class NeroExampleTests(unittest.TestCase):
    def test_read_does_not_enable_or_move(self):
        probe, arm = FakeArm(), FakeArm()
        with patch.object(example.AgxArmFactory, "create_arm", side_effect=[probe, arm]):
            report = example.run(["virtual"])
        self.assertEqual(report["virtual"]["profile"], "v112")
        for instance in (probe, arm):
            self.assertNotIn("enable", instance.calls)
            self.assertFalse(any(isinstance(c, tuple) for c in instance.calls))
            self.assertEqual(instance.calls[-1], "disconnect")

    def test_motion_requires_valid_target_and_normal_status(self):
        probe, arm = FakeArm(), FakeArm()
        with patch.object(example.AgxArmFactory, "create_arm", side_effect=[probe, arm]):
            errors = example.run(["virtual"], example.HOME)
        self.assertEqual(errors, {"virtual": 0.0})
        self.assertNotIn("enable", probe.calls)
        self.assertLess(arm.calls.index("enable"), arm.calls.index(("move_j", example.HOME)))

    def test_invalid_target_never_enables(self):
        probe = FakeArm()
        with patch.object(example.AgxArmFactory, "create_arm", return_value=probe):
            with self.assertRaises(ValueError):
                example.run(["virtual"], [99.0] * 7)
        self.assertNotIn("enable", probe.calls)

    def test_second_arm_fault_prevents_both_enables(self):
        arms = [FakeArm(), FakeArm(), FakeArm(), FakeArm(fault=1)]
        with patch.object(example.AgxArmFactory, "create_arm", side_effect=arms):
            with self.assertRaises(RuntimeError):
                example.run(["left", "right"], example.HOME)
        self.assertTrue(all("enable" not in arm.calls for arm in arms))

    def test_enable_failure_never_sends_joint_target(self):
        probe, arm = FakeArm(), FakeArm(enable_ok=False)
        with patch.object(example.AgxArmFactory, "create_arm", side_effect=[probe, arm]):
            with self.assertRaises(RuntimeError): example.run(["virtual"], example.HOME)
        self.assertFalse(any(isinstance(c, tuple) and c[0] == "move_j" for c in arm.calls))

    def test_three_queries_then_timeout_without_enable(self):
        probe = FakeArm(firmware=None)
        with patch.object(example.AgxArmFactory, "create_arm", return_value=probe):
            with self.assertRaises(TimeoutError): example.discover_firmware("virtual")
        self.assertEqual(probe.calls.count("firmware_query"), 3)
        self.assertNotIn("enable", probe.calls)

    def test_absent_passive_feedback_sends_no_query(self):
        probe = FakeArm()
        probe.get_joint_angles = lambda: None
        probe.get_arm_status = lambda: None
        with patch.object(example.AgxArmFactory, "create_arm", return_value=probe), patch.object(example.time, "monotonic", side_effect=[0, 2]):
            with self.assertRaises(TimeoutError): example.discover_firmware("virtual")
        self.assertNotIn("firmware_query", probe.calls)
        self.assertNotIn("enable", probe.calls)

    def test_invalid_speed_rejected_before_open(self):
        with patch.object(example.AgxArmFactory, "create_arm") as factory:
            with self.assertRaises(ValueError): example.run(["can0"], example.HOME, speed=21)
            factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
