from __future__ import annotations

import pytest

from adam_v55 import DriftMonitor, NearestCentroidOrgan, ShadowDeployment, TrainingGovernanceError, synthetic_sensor_dataset


def test_governed_training_holdout_ood_and_shadow():
    dataset = synthetic_sensor_dataset()
    organ = NearestCentroidOrgan("sensor")
    receipt = organ.train(dataset, validation_groups=("site-e",), test_groups=("site-f",),
                          authorized_capability="SHADOW", approved_by="independent-role")
    assert receipt.validation_accuracy == 1.0
    assert receipt.test_accuracy == 1.0
    assert organ.predict((1.1, 0.55, 0.1)).label == "NORMAL"
    assert organ.predict((1000.0, -1000.0, 500.0)).abstained

    train, _, _ = dataset.split_by_group(validation_groups=("site-e",), test_groups=("site-f",))
    shadow = ShadowDeployment(organ, DriftMonitor.from_examples(train))
    shadow.observe((1.0, 0.5, 0.1), actual_label="NORMAL")
    summary = shadow.summary()
    assert summary["accuracy"] == 1.0
    assert summary["authority_commits"] == 0


def test_dataset_group_splits_prevent_overlap():
    dataset = synthetic_sensor_dataset()
    with pytest.raises(TrainingGovernanceError):
        dataset.split_by_group(validation_groups=("site-e",), test_groups=("site-e",))


def test_training_receipt_binds_dataset_and_capability():
    dataset = synthetic_sensor_dataset()
    organ = NearestCentroidOrgan("sensor")
    receipt = organ.train(dataset, validation_groups=("site-e",), test_groups=("site-f",),
                          authorized_capability="SHADOW_ONLY", approved_by="reviewer")
    assert receipt.dataset_root == dataset.dataset_root
    assert receipt.authorized_capability == "SHADOW_ONLY"
    assert receipt.approved_by == "reviewer"
