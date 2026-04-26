from app.core.labels import multiverse_label, tick_label


def test_labels():
    assert multiverse_label(None, None) == "M1"
    assert multiverse_label("M1", 2) == "M1.2"
    assert tick_label("M1.2", 7) == "M1.2:T7"
