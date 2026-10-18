"""The windowed loop's pure parts: logical screen size, viewport/projection, key merging."""

import pytest

from jenesboat_v2 import app, events, touch
from jenesboat_v2.game import TIME_SCALES


class FakeRL:
    """Records the rlgl calls and answers the size queries like a native window."""

    def __init__(self, screen=(960, 540), render=None, pressed=(), down=()):
        self.screen = screen
        self.render = render or screen
        self.calls: list[tuple] = []
        self.pressed = set(pressed)
        self.down = set(down)
        self.KeyboardKey = type("K", (), {attr: attr for attr in app.KEYBOARD.values()})

    def get_screen_width(self):
        return self.screen[0]

    def get_screen_height(self):
        return self.screen[1]

    def get_render_width(self):
        return self.render[0]

    def get_render_height(self):
        return self.render[1]

    def is_key_pressed(self, key):
        return key in self.pressed

    def is_key_down(self, key):
        return key in self.down

    def __getattr__(self, name):
        if name.startswith("rl_"):

            def record(*args):
                self.calls.append((name, *args))

            return record
        raise AttributeError(name)


class FakeCanvas:
    def __init__(self, css, buffer):
        self.clientWidth, self.clientHeight = css  # noqa: N815 - DOM names
        self.width, self.height = buffer


class FakeWindow:
    def __init__(self, css, buffer):
        self.canvas = FakeCanvas(css, buffer)


@pytest.mark.parametrize(
    ("css", "expected"),
    [
        ((960, 540), (960, 540)),  # a 16:9 desktop window: unchanged
        ((1920, 1080), (960, 540)),  # bigger 16:9: same logical size, just scaled
        ((1280, 540), (1280, 540)),  # a wide window: more map, same text size
        ((852, 393), (976, 450)),  # iPhone 16 sideways: 450 tall for bigger text, wider map
        ((640, 360), (960, 540)),  # a small 16:9 phone: keep 960 across, text gets smaller
        ((700, 400), (945, 540)),  # a small desktop window
        ((0, 0), (960, 540)),  # nothing known yet
    ],
)
def test_logical_size(css, expected):
    assert app.logical_size(*css) == expected


def test_logical_size_keeps_the_aspect_ratio():
    for css in ((852, 393), (1280, 540), (2560, 1080), (1180, 664)):
        w, h = app.logical_size(*css)
        assert w / h == pytest.approx(css[0] / css[1], abs=0.01)
        assert app.MIN_HEIGHT <= h <= app.HEIGHT
        assert w >= app.MIN_WIDTH - 1


def test_measure_prefers_the_page_canvas_and_falls_back_to_raylib():
    rl = FakeRL(screen=(960, 540), render=(1920, 1080))
    native = app.measure(rl, None)
    assert (native.width, native.height) == (960, 540)
    assert native.buffer == (1920, 1080) and native.scale == 1.0
    phone = app.measure(rl, FakeWindow((852, 393), (2556, 1179)))
    assert (phone.width, phone.height) == (976, 450)
    assert phone.buffer == (2556, 1179)
    assert phone.scale == pytest.approx(450 / 393)
    assert phone.snapshot() == {
        "width": 2556,
        "height": 1179,
        "logical": [976, 450],
        "css": [852, 393],
    }
    unready = app.measure(rl, FakeWindow((0, 0), (1, 1)))  # the page has no canvas size yet
    assert (unready.width, unready.height) == (960, 540)


def test_apply_layout_sets_viewport_and_projection():
    rl = FakeRL()
    layout = app.Layout(976, 450, 852, 393, (2556, 1179))
    app.apply_layout(rl, layout)
    assert rl.calls[0] == ("rl_viewport", 0, 0, 2556, 1179)
    assert ("rl_matrix_mode", app.RL_PROJECTION) in rl.calls
    assert ("rl_ortho", 0.0, 976.0, 450.0, 0.0, 0.0, 1.0) in rl.calls
    assert rl.calls[-2:] == [("rl_matrix_mode", app.RL_MODELVIEW), ("rl_load_identity",)]


def test_controls_from_keys_covers_every_key():
    c = app.controls_from_keys(set(app.KEYBOARD) | {"TIME"}, {"A", "D"}, 1)
    assert c.throttle_up and c.throttle_down and c.port and c.starboard and c.rudder_center
    assert c.dive_toggle and c.deep and c.fire and c.zoom_in and c.zoom_out and c.next_target
    assert c.legend and c.pause and c.restart and c.confirm and c.cancel
    assert c.time_scale == 2  # TIME cycles 1 -> 2 (and wins over the digit keys)
    assert app.controls_from_keys(set(), set(), 1) == app.controls_from_keys(set(), set(), 8)


def test_time_button_cycles_through_the_compressions_and_digits_pick_one():
    scale = 1
    seen = []
    for _ in range(len(TIME_SCALES) + 1):
        scale = app.controls_from_keys({"TIME"}, set(), scale).time_scale
        seen.append(scale)
    assert seen == [2, 4, 8, 16, 32, 1, 2]
    assert app.controls_from_keys({"3"}, set(), 1).time_scale == 4
    assert app.controls_from_keys({"6"}, set(), 1).time_scale == 32
    assert app.controls_from_keys({"TIME"}, set(), 99).time_scale == 2  # unknown scale: restart


def test_read_controls_merges_keyboard_and_touch_and_logs_both():
    log = []
    events.set_sink(log.append)
    try:
        rl = FakeRL(pressed={"KEY_W"}, down={"KEY_A"})
        pad = touch.TouchState(active=True, held={"D"}, pressed={"F", "T"})
        c = app.read_controls(rl, pad, 1)
    finally:
        events.set_sink(None)
    assert c.throttle_up and c.port and c.starboard and c.fire and c.next_target
    logged = [events.parse(line) for line in log]
    assert {"event": "input", "key": "W"} in logged
    assert {"event": "input", "key": "F", "source": "touch"} in logged
    assert {"event": "input", "key": "T", "source": "touch"} in logged


class FakeBridge:
    def __init__(self):
        self.calls = []

    def get(self, name):
        return None

    def call(self, name, *args):
        self.calls.append((name, *args))


def test_buffer_fit_asks_for_css_times_dpr_and_gives_up_after_a_few_tries():
    bridge = FakeBridge()
    fit = app.BufferFit(bridge)
    phone = app.Layout(976, 450, 852, 393, (852, 393))
    assert fit.update(phone, 3.0)
    assert bridge.calls == [("jb_fit", 2556, 1179)]
    sharp = app.Layout(976, 450, 852, 393, (2556, 1179))
    assert not fit.update(sharp, 3.0)  # already right
    for _ in range(5):
        fit.update(phone, 3.0)  # the page keeps resetting it: stop asking
    assert len(bridge.calls) == app.BufferFit.ATTEMPTS
    rotated = app.Layout(960, 540, 393, 852, (393, 852))
    assert fit.update(rotated, 3.0)  # a new size gets new tries
    assert not fit.update(phone, None) and not fit.update(phone, 0)
    assert not app.BufferFit(None).update(phone, 2.0)
