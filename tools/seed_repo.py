#!/usr/bin/env python3
"""Create the fictional `trailnet` git repository for the LabRoom demo.

Builds a small, runnable Python/C repo and commits it 25 times over the seed
week (Mon Oct 26 to Fri Oct 30, 2026) with five fictional authors, so the
Reporter agent has a real `git log` to read.

All people are invented. Emails are at example.edu.

Usage:
    python tools/seed_repo.py                 # creates ../trailnet next to tools/
    python tools/seed_repo.py --out PATH      # elsewhere
    python tools/seed_repo.py --force         # delete and rebuild
"""

import argparse
import csv
import io
import os
import random
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

PEOPLE = {
    "priya": ("Priya Nair", "priya.nair@example.edu"),
    "lucas": ("Lucas Moreno", "lucas.moreno@example.edu"),
    "sofia": ("Sofia Alvarez", "sofia.alvarez@example.edu"),
    "omar": ("Omar Haddad", "omar.haddad@example.edu"),
    "wei": ("Wei Zhang", "wei.zhang@example.edu"),
}

CLASSES = ["empty", "deer", "elk", "coyote", "other"]
SITES = ["river_a", "river_b", "meadow", "creek", "bench", "ridge"]
SPLIT_OF_SITE = {
    "river_a": "train", "river_b": "train", "meadow": "train", "creek": "train",
    "bench": "val", "ridge": "test",
}
TZ = "-06:00"  # Mountain Daylight Time during the seed week


def dedent(s):
    return textwrap.dedent(s).lstrip("\n")


# --------------------------------------------------------------------------
# Manifest generator (frames themselves are never in the repo)
# --------------------------------------------------------------------------

def build_manifest(counts, seed, partial_counts=None, frozen=False, ridge_night=0):
    """Return CSV text for a manifest with exact per-class counts.

    counts: dict class -> number of frames
    partial_counts: dict class -> how many of that class get partial=1
    frozen: assign splits by site (v0.3 freeze)
    ridge_night: force this many ridge-site frames to be night frames
    """
    rng = random.Random(seed)
    rows = []
    for cls in CLASSES:
        for _ in range(counts.get(cls, 0)):
            rows.append({"class": cls})
    rng.shuffle(rows)
    partial_left = dict(partial_counts or {})
    ridge_seen = 0
    for i, r in enumerate(rows):
        site = rng.choice(SITES)
        r["frame_id"] = f"f{i + 1:05d}"
        r["site"] = site
        r["path"] = f"frames/{site}/{r['frame_id']}.jpg"
        night = 1 if rng.random() < 0.12 else 0
        if site == "ridge" and ridge_night:
            # exactly ridge_night night frames at the test site
            night = 1 if ridge_seen < ridge_night else 0
            ridge_seen += night
        r["night"] = night
        p = 0
        if partial_left.get(r["class"], 0) > 0 and r["class"] != "empty":
            p = 1
            partial_left[r["class"]] -= 1
        r["partial"] = p
        r["split"] = SPLIT_OF_SITE[site] if frozen else ""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["frame_id", "path", "site", "class", "partial", "night", "split"],
                       lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


COUNTS_MON = {"empty": 1900, "deer": 620, "elk": 180, "coyote": 70, "other": 130}        # 2,900
COUNTS_TUE = {"empty": 2060, "deer": 690, "elk": 190, "coyote": 75, "other": 85}         # 3,100
COUNTS_TUE_FIX = {"empty": 2070, "deer": 694, "elk": 191, "coyote": 75, "other": 85}     # 3,115
COUNTS_V03 = {"empty": 2640, "deer": 870, "elk": 260, "coyote": 110, "other": 240}       # 4,120
PARTIALS = {"deer": 140, "coyote": 12, "elk": 28}                                        # 180


def hard_negatives_csv(seed):
    rng = random.Random(seed)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["frame_id", "path", "site", "class", "partial", "night", "reason"])
    for i in range(200):
        site = rng.choice(["river_a", "river_b"])
        fid = f"hn{i + 1:04d}"
        w.writerow([fid, f"frames/{site}/{fid}.jpg", site, "empty", 0, 1 if rng.random() < 0.3 else 0,
                    rng.choice(["grass_wind", "grass_wind", "heat_shimmer", "branch"])])
    return buf.getvalue()


# --------------------------------------------------------------------------
# File contents
# --------------------------------------------------------------------------

README_V1 = dedent("""
    # TrailNet

    Low-power smart camera trap that counts wildlife on the device.

    A PIR motion sensor wakes a microcontroller, which captures a frame and runs a
    small image classifier. The node uploads only the class and count, never the image.

    Layout:

    - `firmware/` camera node trigger loop, power budget
    - `data/` frame manifest, labeling guideline, placeholder frame generator
    - `model/` training and quantization
    - `eval/` weekly accuracy and confusion matrix plots
    - `paper/` workshop paper notes

    Classes: empty, deer, elk, coyote, other. Model budget: 250 KB after int8.
    """)

README_V2 = README_V1 + dedent("""

    ## Dataset v0.3 (frozen Oct 28, 2026 for the workshop paper)

    | class | frames |
    | --- | --- |
    | empty | 2,640 |
    | deer | 870 |
    | elk | 260 |
    | coyote | 110 |
    | other | 240 |
    | total | 4,120 |

    Splits are by site: river_a, river_b, meadow, creek train; bench validation; ridge test.
    The frames are not in this repository. See `data/README.md`.
    """)

GITIGNORE = dedent("""
    __pycache__/
    *.pyc
    data/frames/
    data/placeholder_frames/
    model/weights*.npz
    eval/*.png
    eval/results_latest.csv
    """)

TRIGGER_V1 = dedent("""
    /* TrailNet camera node: trigger loop skeleton.
     * Target: Cortex-M4 class MCU, PIR on EXTI line 3, camera on DCMI.
     */
    #include <stdint.h>
    #include <stdbool.h>

    #include "board.h"

    static volatile bool pir_fired = false;

    void EXTI3_IRQHandler(void) {
        pir_fired = true;
        exti_clear(3);
    }

    int main(void) {
        board_init();
        pir_init();
        for (;;) {
            if (pir_fired) {
                pir_fired = false;
                /* TODO: capture frame, run classifier, transmit count */
            }
        }
    }
    """)

TRIGGER_V2 = dedent("""
    /* TrailNet camera node: trigger loop.
     * Target: Cortex-M4 class MCU, PIR on EXTI line 3, camera on DCMI.
     *
     * Debounce: a PIR pulse shorter than PIR_MIN_PULSE_MS is ignored. Wind on
     * tall grass produces many short pulses; animals produce long ones.
     */
    #include <stdint.h>
    #include <stdbool.h>

    #include "board.h"

    #define PIR_MIN_PULSE_MS 120

    static volatile uint32_t pir_rise_ms = 0;
    static volatile bool pir_fired = false;

    void EXTI3_IRQHandler(void) {
        if (pir_level()) {
            pir_rise_ms = millis();
        } else if (millis() - pir_rise_ms >= PIR_MIN_PULSE_MS) {
            pir_fired = true;
        }
        exti_clear(3);
    }

    int main(void) {
        board_init();
        pir_init();
        for (;;) {
            if (pir_fired) {
                pir_fired = false;
                /* TODO: capture frame, run classifier, transmit count */
            }
        }
    }
    """)

TRIGGER_V3 = dedent("""
    /* TrailNet camera node: trigger loop.
     * Target: Cortex-M4 class MCU, PIR on EXTI line 3, camera on DCMI.
     *
     * Debounce: a PIR pulse shorter than PIR_MIN_PULSE_MS is ignored.
     * Power: the MCU enters STOP mode between triggers. Measured 0.4 mA
     * in STOP vs 11 mA busy-waiting (Oct 26, bench supply, 3.7 V).
     */
    #include <stdint.h>
    #include <stdbool.h>

    #include "board.h"

    #define PIR_MIN_PULSE_MS 120

    static volatile uint32_t pir_rise_ms = 0;
    static volatile bool pir_fired = false;

    void EXTI3_IRQHandler(void) {
        if (pir_level()) {
            pir_rise_ms = millis();
        } else if (millis() - pir_rise_ms >= PIR_MIN_PULSE_MS) {
            pir_fired = true;
        }
        exti_clear(3);
    }

    static void handle_trigger(void) {
        /* TODO: capture frame, run classifier, transmit count */
    }

    int main(void) {
        board_init();
        pir_init();
        for (;;) {
            if (pir_fired) {
                pir_fired = false;
                handle_trigger();
            }
            power_enter_stop();   /* wakes on EXTI3 */
        }
    }
    """)

TRIGGER_V4 = dedent("""
    /* TrailNet camera node: trigger loop.
     * Target: Cortex-M4 class MCU, PIR on EXTI line 3, camera on DCMI.
     *
     * Debounce: a PIR pulse shorter than PIR_MIN_PULSE_MS is ignored.
     * Power: the MCU enters STOP mode between triggers (0.4 mA).
     * Capture: camera_capture() fills a 64x64 grayscale buffer. The ir_cut flag
     * selects the IR-cut filter position on the new modules; on the old modules
     * it is ignored. Night is detected from the ambient light sensor.
     */
    #include <stdint.h>
    #include <stdbool.h>

    #include "board.h"
    #include "camera.h"

    #define PIR_MIN_PULSE_MS 120
    #define FRAME_W 64
    #define FRAME_H 64

    static volatile uint32_t pir_rise_ms = 0;
    static volatile bool pir_fired = false;
    static uint8_t frame[FRAME_W * FRAME_H];

    void EXTI3_IRQHandler(void) {
        if (pir_level()) {
            pir_rise_ms = millis();
        } else if (millis() - pir_rise_ms >= PIR_MIN_PULSE_MS) {
            pir_fired = true;
        }
        exti_clear(3);
    }

    static void handle_trigger(void) {
        bool night = ambient_lux() < NIGHT_LUX;
        camera_capture(frame, FRAME_W, FRAME_H, /*ir_cut=*/!night);
        /* TODO: run classifier on frame, transmit class and count */
    }

    int main(void) {
        board_init();
        pir_init();
        camera_init();
        for (;;) {
            if (pir_fired) {
                pir_fired = false;
                handle_trigger();
            }
            power_enter_stop();   /* wakes on EXTI3 */
        }
    }
    """)

TRIGGER_V5 = TRIGGER_V4.replace(
    "static void handle_trigger(void) {\n    bool night",
    "static void log_trigger(uint32_t t_ms, bool night) {\n"
    "    /* one line per trigger on the SD card: ms since boot, night flag.\n"
    "     * Used to replay trigger logs offline and test debounce rules. */\n"
    "    sd_printf(\"%lu,%d\\n\", (unsigned long)t_ms, night ? 1 : 0);\n"
    "}\n\n"
    "static void handle_trigger(void) {\n    bool night"
).replace(
    "    camera_capture(frame, FRAME_W, FRAME_H, /*ir_cut=*/!night);\n",
    "    log_trigger(millis(), night);\n"
    "    camera_capture(frame, FRAME_W, FRAME_H, /*ir_cut=*/!night);\n"
)
assert TRIGGER_V5 != TRIGGER_V4, "trigger log patch did not apply"

POWER_BUDGET = dedent("""
    state,current_mA,seconds_per_event,events_per_day,mAh_per_day,note
    stop,0.4,86400,1,9.6,MCU in STOP between triggers
    wake_and_capture,45,1.5,200,3.75,old camera module; new module TBD
    inference,60,0.8,200,2.67,int8 classifier on MCU
    radio_tx,120,2.0,60,4.0,only non-empty results are sent
    total,,,,20.0,"2 cells at 2600 mAh each = 260 days at 200 triggers/day; 340 triggers/day at river site = 6 weeks with false-trigger radio"
    """)

FIRMWARE_README = dedent("""
    # TrailNet camera node firmware

    ## Parts

    - MCU board: Cortex-M4 class dev board, 1 MB flash, 256 KB RAM
    - Camera: 64x64 grayscale capture from a module with switchable IR-cut filter
      (new modules arriving; old modules have no IR-cut)
    - PIR motion sensor on EXTI line 3
    - Ambient light sensor on I2C for night detection
    - LoRa radio for class and count uplink
    - SD card for trigger logs

    ## Pin map

    | Signal | Pin |
    | --- | --- |
    | PIR out | PA3 (EXTI3) |
    | Camera DCMI | PA4-PA6, PB6-PB9 |
    | IR-cut control | PC2 |
    | Ambient light SDA/SCL | PB10 / PB11 |
    | LoRa SPI | PA5 / PA6 / PA7, CS PB0 |
    | SD SPI | PC10 / PC11 / PC12, CS PC13 |

    ## Build

    `make` with the vendor toolchain on the path. `make flash` with the board on USB.

    ## Flash budget

    Firmware about 180 KB. Classifier must stay under 250 KB. Both must fit in 512 KB with the bootloader.
    """)

NIGHT_SPLIT = dedent("""
    # Night / day holdout split

    Wei Zhang, Oct 26, 2026

    Night frames are grayscale infrared with a flash. Day frames are color converted
    to grayscale at capture. The two look nothing alike to the model, so every
    accuracy number must be reported for day and night separately.

    Rules:

    1. `night` is a column in the manifest, set from the ambient light reading at
       capture, not from the time of day.
    2. The holdout is stratified so night frames appear in every split in about the
       same proportion as in the full set, except the test site, which should have
       at least 100 night frames so a night number means something.
    3. Never report a night accuracy from fewer than 100 frames without saying so.

    Current night count: about 300 frames, two sites. Domain adaptation experiments
    continue as data arrives from the field.
    """)

LABELING_GUIDELINE = dedent("""
    # TrailNet labeling guideline v1

    Sofia Alvarez, Oct 28, 2026. Reviewed by Maya Chen.

    ## Classes

    Exactly one of: `empty`, `deer`, `elk`, `coyote`, `other`.

    - `empty`: no animal, or an animal too far away to identify at native resolution.
      If you cannot tell the species at 64x64, the node cannot either. Label it empty.
    - `deer`: mule deer and white-tailed deer. Antlers in shadow are still deer; check
      body size and ear shape before calling it elk.
    - `elk`: larger body, darker neck, lighter rump. Calves count as elk.
    - `coyote`: any canid. We have no wolves or dogs at these sites.
    - `other`: everything else that is clearly an animal: birds, raccoons, rabbits, cattle.

    ## Partial flag

    `partial = 1` when less than about half the animal is visible (a leg, a back, a tail).
    Keep the class label. Partial is not a class. If the species cannot be told from
    the visible part, label `empty` with `partial = 0`.

    ## Multiple animals

    Label the closest animal. The count field is a separate project; do not try to
    count in the class label.

    ## Night frames

    Label night frames exactly like day frames. If the flash washed out the frame
    and nothing is identifiable, it is `empty`.
    """)

DATA_README_V1 = dedent("""
    # TrailNet data

    The frames are not in this repository. They live on the lab NAS under
    `trailnet/frames/<site>/`. This folder holds the manifest, the labeling guideline
    and a generator for synthetic placeholder frames so the training script runs
    anywhere.

    Manifest columns: `frame_id, path, site, class, partial, night, split`.

    Sites: river_a, river_b, meadow, creek, bench, ridge.
    """)

DATA_README_V2 = DATA_README_V1 + dedent("""

    ## v0.3 (frozen Oct 28, 2026)

    4,120 frames. empty 2,640, deer 870, elk 260, coyote 110, other 240.
    Splits by site: train river_a, river_b, meadow, creek; val bench; test ridge.
    The test site has 160 night frames.

    Frames labelled after the freeze go to `v0.4_staging/` and are not used in the paper.

    ## Placeholder frames

    `python data/make_placeholder_frames.py` writes 60 synthetic 32x32 PGM frames
    (12 per class, half of them "night") to `data/placeholder_frames/` with a
    manifest. They are shapes, not animals. They exist so `model/train.py` can run
    on a laptop without the NAS.
    """)

MAKE_FRAMES = dedent('''
    #!/usr/bin/env python3
    """Write synthetic placeholder frames so the training script runs without real data.

    Each class is a different shape on a noisy background. Half the frames are
    "night": darker and lower contrast. These are stand-ins, not wildlife.
    """
    import csv
    import os
    import random
    import sys

    CLASSES = ["empty", "deer", "elk", "coyote", "other"]
    W = H = 32


    def draw(cls, rng, night):
        base = 40 if night else 120
        spread = 15 if night else 40
        img = [[max(0, min(255, int(rng.gauss(base, spread)))) for _ in range(W)] for _ in range(H)]
        fg = base + (60 if night else 100)
        x0, y0 = rng.randint(4, 12), rng.randint(4, 12)
        if cls == "deer":          # tall rectangle
            for y in range(y0, y0 + 16):
                for x in range(x0, x0 + 6):
                    img[y][x] = fg
        elif cls == "elk":         # wide rectangle with two "antler" dots
            for y in range(y0 + 4, y0 + 14):
                for x in range(x0, x0 + 14):
                    img[y][x] = fg
            img[y0 + 2][x0 + 2] = 255
            img[y0 + 2][x0 + 11] = 255
        elif cls == "coyote":      # small low rectangle
            for y in range(y0 + 10, y0 + 15):
                for x in range(x0, x0 + 9):
                    img[y][x] = fg
        elif cls == "other":       # circle
            cx, cy, r = x0 + 8, y0 + 8, 6
            for y in range(H):
                for x in range(W):
                    if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                        img[y][x] = fg
        return img


    def main(out_dir):
        rng = random.Random(7)
        os.makedirs(out_dir, exist_ok=True)
        rows = []
        i = 0
        for cls in CLASSES:
            for k in range(12):
                night = 1 if k % 2 else 0
                img = draw(cls, rng, night)
                name = f"p{i:03d}.pgm"
                with open(os.path.join(out_dir, name), "w") as f:
                    f.write(f"P2\\n{W} {H}\\n255\\n")
                    for row in img:
                        f.write(" ".join(str(v) for v in row) + "\\n")
                rows.append([name, cls, night, "test" if k >= 9 else "train"])
                i += 1
        with open(os.path.join(out_dir, "placeholder_manifest.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["file", "class", "night", "split"])
            w.writerows(rows)
        print(f"wrote {i} frames to {out_dir}")


    if __name__ == "__main__":
        main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "placeholder_frames"))
    ''')

TRAIN_V1 = dedent('''
    #!/usr/bin/env python3
    """Train a tiny classifier on the placeholder frames and log accuracy.

    This is the laptop-sized stand-in for the real training run on the NAS frames.
    One hidden layer, numpy only, trains in seconds. Writes:
      model/weights.npz          float32 weights
      eval/results_latest.csv    week, split, day_accuracy, night_accuracy, model_kb
    """
    import csv
    import os
    import sys

    import numpy as np

    HERE = os.path.dirname(os.path.abspath(__file__))
    ROOT = os.path.dirname(HERE)
    CLASSES = ["empty", "deer", "elk", "coyote", "other"]


    def read_pgm(path):
        with open(path) as f:
            tokens = f.read().split()
        assert tokens[0] == "P2"
        w, h = int(tokens[1]), int(tokens[2])
        px = np.array(tokens[4:4 + w * h], dtype=np.float32) / 255.0
        return px


    def load(frames_dir):
        X, y, night, split = [], [], [], []
        with open(os.path.join(frames_dir, "placeholder_manifest.csv")) as f:
            for row in csv.DictReader(f):
                X.append(read_pgm(os.path.join(frames_dir, row["file"])))
                y.append(CLASSES.index(row["class"]))
                night.append(int(row["night"]))
                split.append(row["split"])
        return np.array(X), np.array(y), np.array(night), np.array(split)


    def train(X, y, hidden=32, epochs=600, lr=0.1, seed=0):
        rng = np.random.default_rng(seed)
        n, d = X.shape
        k = len(CLASSES)
        W1 = rng.normal(0, 0.05, (d, hidden)).astype(np.float32)
        b1 = np.zeros(hidden, np.float32)
        W2 = rng.normal(0, 0.05, (hidden, k)).astype(np.float32)
        b2 = np.zeros(k, np.float32)
        Y = np.eye(k, dtype=np.float32)[y]
        for _ in range(epochs):
            h = np.maximum(0, X @ W1 + b1)
            logits = h @ W2 + b2
            p = np.exp(logits - logits.max(1, keepdims=True))
            p /= p.sum(1, keepdims=True)
            g = (p - Y) / n
            gW2, gb2 = h.T @ g, g.sum(0)
            gh = g @ W2.T * (h > 0)
            gW1, gb1 = X.T @ gh, gh.sum(0)
            W1 -= lr * gW1; b1 -= lr * gb1; W2 -= lr * gW2; b2 -= lr * gb2
        return W1, b1, W2, b2


    def predict(params, X):
        W1, b1, W2, b2 = params
        return (np.maximum(0, X @ W1 + b1) @ W2 + b2).argmax(1)


    def accuracy(params, X, y, mask):
        if mask.sum() == 0:
            return float("nan")
        return float((predict(params, X[mask]) == y[mask]).mean())


    def main():
        frames_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "placeholder_frames")
        X, y, night, split = load(frames_dir)
        tr, te = split == "train", split == "test"
        params = train(X[tr], y[tr])
        day = accuracy(params, X, y, te & (night == 0))
        nt = accuracy(params, X, y, te & (night == 1))
        kb = sum(p.nbytes for p in params) / 1024
        print(f"test day accuracy {day:.2f}  night accuracy {nt:.2f}  float32 size {kb:.1f} KB")
        np.savez(os.path.join(HERE, "weights.npz"), W1=params[0], b1=params[1], W2=params[2], b2=params[3])
        os.makedirs(os.path.join(ROOT, "eval"), exist_ok=True)
        with open(os.path.join(ROOT, "eval", "results_latest.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["week", "split", "day_accuracy", "night_accuracy", "model_kb"])
            w.writerow(["placeholder", "test", f"{day:.3f}", f"{nt:.3f}", f"{kb:.1f}"])


    if __name__ == "__main__":
        main()
    ''')

DISTILL_NOTE = dedent("""
    # Knowledge distillation run, Oct 28, 2026

    Priya Nair

    Teacher: server model, 96x96 input, 94.1 percent day accuracy, 2.3 MB.
    Student: same block structure, 64x64 input, width halved, temperature 4, alpha 0.7.

    | model | input | int8 size | day acc | night acc (60 frames) |
    | --- | --- | --- | --- | --- |
    | quantized v0.2 | 96x96 | 310 KB | 89.0 | 71.0 |
    | pruned v0.2 | 96x96 | 262 KB | 87.5 | 66.0 |
    | distilled student | 64x64 | 240 KB | 88.0 | 74.0 |

    The student is under the 250 KB budget. The night number needs the v0.3 test
    split (160 night frames) before anyone quotes it.

    Training on the NAS frames is run with `train_nas.sh` (not in this repo; it needs
    the lab GPU). The numpy `train.py` here is the laptop stand-in on placeholder frames.
    """)

RESULTS_V03 = DISTILL_NOTE + dedent("""

    ## Rerun on v0.3 test split, Oct 30, 2026

    | model | day acc | night acc (160 frames) | coyote recall night |
    | --- | --- | --- | --- |
    | distilled student | 88.3 | 73.1 | 41.0 |

    The 74 held, roughly. Coyote at night is the number to beat.
    """)

QUANTIZE = dedent('''
    #!/usr/bin/env python3
    """Quantize the trained weights to int8 and report the size against the budget."""
    import os
    import sys

    import numpy as np

    HERE = os.path.dirname(os.path.abspath(__file__))
    BUDGET_KB = 250


    def quantize(arr):
        scale = float(np.abs(arr).max() / 127.0) or 1.0
        q = np.clip(np.round(arr / scale), -127, 127).astype(np.int8)
        return q, scale


    def main():
        src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "weights.npz")
        w = np.load(src)
        out, total = {}, 0
        for k in w.files:
            q, s = quantize(w[k])
            out[k] = q
            out[k + "_scale"] = np.float32(s)
            total += q.nbytes + 4
        np.savez(os.path.join(HERE, "weights_int8.npz"), **out)
        kb = total / 1024
        status = "OK" if kb <= BUDGET_KB else "OVER BUDGET"
        print(f"int8 size {kb:.1f} KB of {BUDGET_KB} KB budget: {status}")
        return 0 if kb <= BUDGET_KB else 1


    if __name__ == "__main__":
        sys.exit(main())
    ''')

EVAL_README = dedent("""
    # Evaluation dashboard

    Omar Haddad, Oct 26, 2026

    Three panels, all from CSV files written by the training runs. No screenshots in chat.

    1. Weekly accuracy, day and night as two lines. Source `weekly_accuracy.csv`.
    2. Per-class recall as bars. Source `per_class_recall.csv` (to be added).
    3. Confusion matrix for the latest model. Source `confusion.csv`.

    `weekly_accuracy.csv` columns: `week, split, day_accuracy, night_accuracy, model_kb`.
    `confusion.csv`: rows true class, columns predicted class, in the order empty, deer, elk, coyote, other.

    `python eval/plot_accuracy.py` writes `weekly_accuracy.png` and `confusion.png` here.
    """)

WEEKLY_CSV = dedent("""
    week,split,day_accuracy,night_accuracy,model_kb
    2026-W40,val,0.81,0.63,340
    2026-W41,val,0.84,0.66,340
    2026-W42,val,0.86,0.69,310
    2026-W43,val,0.89,0.71,310
    2026-W44,test,0.883,0.731,240
    """)

CONFUSION_CSV = dedent("""
    true/pred,empty,deer,elk,coyote,other
    empty,412,6,1,2,9
    deer,8,119,14,1,3
    elk,2,11,27,0,1
    coyote,3,2,0,10,3
    other,9,3,0,2,26
    """)

PLOT_ACCURACY = dedent('''
    #!/usr/bin/env python3
    """Plot weekly day/night accuracy and the latest confusion matrix from CSV."""
    import csv
    import os

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    HERE = os.path.dirname(os.path.abspath(__file__))
    CLASSES = ["empty", "deer", "elk", "coyote", "other"]
    DAY, NIGHT = "#2a78d6", "#eb6834"


    def weekly():
        weeks, day, night = [], [], []
        with open(os.path.join(HERE, "weekly_accuracy.csv")) as f:
            for r in csv.DictReader(f):
                weeks.append(r["week"].replace("2026-", ""))
                day.append(float(r["day_accuracy"]) * 100)
                night.append(float(r["night_accuracy"]) * 100)
        fig, ax = plt.subplots(figsize=(6, 3.4), dpi=150)
        ax.plot(weeks, day, color=DAY, lw=2, marker="o", ms=5, label="day")
        ax.plot(weeks, night, color=NIGHT, lw=2, marker="o", ms=5, label="night")
        ax.text(weeks[-1], day[-1] + 1.5, f"{day[-1]:.0f}", color="#52514e", ha="center", fontsize=8)
        ax.text(weeks[-1], night[-1] + 1.5, f"{night[-1]:.0f}", color="#52514e", ha="center", fontsize=8)
        ax.set_ylim(50, 100)
        ax.set_ylabel("accuracy, percent")
        ax.set_title("TrailNet classifier accuracy per week", loc="left", fontsize=10)
        ax.grid(axis="y", color="#e4e3df", lw=0.8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.legend(frameon=False, loc="lower right")
        fig.tight_layout()
        fig.savefig(os.path.join(HERE, "weekly_accuracy.png"))


    def confusion():
        with open(os.path.join(HERE, "confusion.csv")) as f:
            rows = list(csv.reader(f))[1:]
        m = np.array([[int(v) for v in r[1:]] for r in rows], dtype=float)
        recall = m / m.sum(1, keepdims=True)
        fig, ax = plt.subplots(figsize=(4.6, 4), dpi=150)
        ax.imshow(recall, cmap="Blues", vmin=0, vmax=1)
        for i in range(5):
            for j in range(5):
                ax.text(j, i, f"{recall[i, j]:.2f}", ha="center", va="center", fontsize=8,
                        color="white" if recall[i, j] > 0.6 else "#0b0b0b")
        ax.set_xticks(range(5), CLASSES)
        ax.set_yticks(range(5), CLASSES)
        ax.set_xlabel("predicted")
        ax.set_ylabel("true")
        ax.set_title("Row-normalized confusion, latest model", loc="left", fontsize=10)
        fig.tight_layout()
        fig.savefig(os.path.join(HERE, "confusion.png"))


    if __name__ == "__main__":
        weekly()
        confusion()
        print("wrote weekly_accuracy.png and confusion.png")
    ''')

RELATED_WORK = dedent("""
    # Related work notes

    Omar Haddad, Oct 29, 2026. Six entries. Wei adds night and domain adaptation references.

    ## Camera-trap species classification

    1. Norouzzadeh et al., Automatically identifying, counting, and describing wild
       animals in camera-trap images with deep learning (arXiv:1703.05830). Snapshot
       Serengeti, deep networks for species, count and behavior. Our task, at server scale.
    2. A follow-up on transfer across camera-trap projects: accuracy drops hard on new
       sites, which matches our site-split results. (Add citation.)
    3. A study of empty-frame filtering as a first stage before species classification.
       Our two-pulse PIR trigger plus the empty class is the on-device version of this.
       (Add citation.)

    ## On-device inference

    4. Lin et al., MCUNet: Tiny Deep Learning on IoT Devices (arXiv:2007.10319).
       Joint architecture search and inference engine for microcontrollers with
       sub-megabyte flash. Their image classification results are the closest to our budget.
    5. A survey of quantization and pruning for edge deployment. Supports the choice of
       int8 and the observation that pruning hurts rare classes first. (Add citation.)

    ## Class imbalance in wildlife data

    6. A paper on long-tailed species distributions in camera-trap datasets and the
       effect on rare-class recall. Coyote at 2 percent is our long tail. (Add citation.)

    ## To add (Wei)

    - Day to night domain shift in camera-trap and surveillance imagery.
    - Infrared and thermal wildlife classification.
    """)

VALIDATE_MANIFEST = dedent('''
    #!/usr/bin/env python3
    """Validate a manifest before pushing it: classes, flags, no frame in two splits."""
    import csv
    import sys

    CLASSES = {"empty", "deer", "elk", "coyote", "other"}
    SPLITS = {"", "train", "val", "test"}


    def main(path):
        seen, errors = {}, []
        with open(path, newline="") as f:
            for n, r in enumerate(csv.DictReader(f), start=2):
                if r["class"] not in CLASSES:
                    errors.append(f"line {n}: bad class {r['class']!r}")
                if r["partial"] not in ("0", "1"):
                    errors.append(f"line {n}: partial must be 0 or 1")
                if r["class"] == "empty" and r["partial"] == "1":
                    errors.append(f"line {n}: empty frames cannot be partial")
                if r["night"] not in ("0", "1"):
                    errors.append(f"line {n}: night must be 0 or 1")
                if r["split"] not in SPLITS:
                    errors.append(f"line {n}: bad split {r['split']!r}")
                prev = seen.setdefault(r["frame_id"], r["split"])
                if prev != r["split"]:
                    errors.append(f"line {n}: {r['frame_id']} appears in two splits")
        for e in errors[:50]:
            print(e)
        print(f"{len(seen)} frames, {len(errors)} errors")
        return 1 if errors else 0


    if __name__ == "__main__":
        sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "data/manifest.csv"))
    ''')

HARD_NEG_README = dedent("""
    # v0.4 staging

    Frames labelled after the v0.3 freeze. Not used in the workshop paper.

    `hard_negatives.csv`: 200 empty frames from the windy days at the river sites.
    These are the frames that fooled the PIR. If the model learns "grass", the node
    can skip the radio on them and save battery.
    """)


# --------------------------------------------------------------------------
# Commit plan: (author key, date, message, {path: content})
# --------------------------------------------------------------------------

COMMITS = [
    ("priya", "2026-10-26T09:05:00", "Initialize repo with README and project layout",
     {"README.md": README_V1, ".gitignore": GITIGNORE,
      "firmware/.gitkeep": "", "data/.gitkeep": "", "model/.gitkeep": "", "eval/.gitkeep": "", "paper/.gitkeep": ""}),
    ("lucas", "2026-10-26T09:40:00", "firmware: PIR trigger loop skeleton",
     {"firmware/trigger_loop.c": TRIGGER_V1}),
    ("sofia", "2026-10-26T10:15:00", "data: manifest schema and the current 2,900 labelled frames",
     {"data/README.md": DATA_README_V1, "data/manifest.csv": build_manifest(COUNTS_MON, seed=1)}),
    ("wei", "2026-10-26T11:30:00", "model: define night/day holdout split rules",
     {"model/night_split.md": NIGHT_SPLIT}),
    ("lucas", "2026-10-26T13:20:00", "firmware: debounce PIR pulses to cut wind false triggers",
     {"firmware/trigger_loop.c": TRIGGER_V2}),
    ("sofia", "2026-10-26T14:05:00", "data: placeholder frame generator so training runs without the NAS",
     {"data/make_placeholder_frames.py": MAKE_FRAMES}),
    ("lucas", "2026-10-26T16:45:00", "firmware: power budget spreadsheet, first pass",
     {"firmware/power_budget.csv": POWER_BUDGET}),
    ("sofia", "2026-10-27T08:50:00", "data: 200 more frames labelled, manifest v0.2",
     {"data/manifest.csv": build_manifest(COUNTS_TUE, seed=2)}),
    ("lucas", "2026-10-27T09:30:00", "firmware: STOP mode between triggers, 11 mA to 0.4 mA",
     {"firmware/trigger_loop.c": TRIGGER_V3}),
    ("priya", "2026-10-27T10:10:00", "model: tiny classifier training script, writes eval CSV",
     {"model/train.py": TRAIN_V1}),
    ("lucas", "2026-10-27T11:15:00", "firmware: camera capture stub with ir_cut flag for the new modules",
     {"firmware/trigger_loop.c": TRIGGER_V4}),
    ("sofia", "2026-10-27T13:40:00", "data: fix off-by-one that dropped the last frame of each batch",
     {"data/manifest.csv": build_manifest(COUNTS_TUE_FIX, seed=2)}),
    ("lucas", "2026-10-27T15:00:00", "firmware: README with parts list, wiring and pin map",
     {"firmware/README.md": FIRMWARE_README}),
    ("lucas", "2026-10-27T17:30:00", "firmware: log trigger timestamps to SD for offline replay",
     {"firmware/trigger_loop.c": TRIGGER_V5}),
    ("sofia", "2026-10-28T09:00:00", "data: labeling guideline v1 with partial flag",
     {"data/labeling_guideline.md": LABELING_GUIDELINE}),
    ("priya", "2026-10-28T10:30:00", "model: knowledge distillation run, student at 240 KB",
     {"model/results.md": DISTILL_NOTE}),
    ("sofia", "2026-10-28T11:20:00", "data: flag 180 partial frames under the new guideline",
     {"data/manifest.csv": build_manifest(COUNTS_TUE_FIX, seed=2, partial_counts=PARTIALS)}),
    ("omar", "2026-10-28T14:00:00", "eval: weekly accuracy plot and confusion matrix from CSV",
     {"eval/README.md": EVAL_README, "eval/weekly_accuracy.csv": WEEKLY_CSV.replace("2026-W44,test,0.883,0.731,240\n", ""),
      "eval/confusion.csv": CONFUSION_CSV, "eval/plot_accuracy.py": PLOT_ACCURACY}),
    ("sofia", "2026-10-28T16:10:00", "data: freeze dataset v0.3, splits by site, 4,120 frames",
     {"data/manifest.csv": build_manifest(COUNTS_V03, seed=3, partial_counts=PARTIALS, frozen=True, ridge_night=160),
      "data/README.md": DATA_README_V2}),
    ("priya", "2026-10-29T09:15:00", "model: int8 quantize script reports size against the 250 KB budget",
     {"model/quantize.py": QUANTIZE}),
    ("sofia", "2026-10-29T10:40:00", "docs: v0.3 class counts in the README",
     {"README.md": README_V2}),
    ("omar", "2026-10-29T13:30:00", "paper: related work notes, six entries",
     {"paper/related_work.md": RELATED_WORK}),
    ("sofia", "2026-10-29T15:00:00", "data: 200 empty hard negatives from windy days, v0.4 staging",
     {"data/v0.4_staging/README.md": HARD_NEG_README, "data/v0.4_staging/hard_negatives.csv": hard_negatives_csv(seed=4)}),
    ("priya", "2026-10-30T09:30:00", "model: night test rerun on v0.3 split, log results",
     {"model/results.md": RESULTS_V03, "eval/weekly_accuracy.csv": WEEKLY_CSV}),
    ("sofia", "2026-10-30T11:00:00", "data: manifest validation script",
     {"data/validate_manifest.py": VALIDATE_MANIFEST}),
]


def git(repo, *args, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    subprocess.run(["git", *args], cwd=repo, check=True, env=e,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    default_out = Path(__file__).resolve().parent.parent / "trailnet"
    ap.add_argument("--out", default=str(default_out), help="where to create the repo")
    ap.add_argument("--force", action="store_true", help="delete an existing repo at --out first")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        if not args.force:
            print(f"{out} exists. Use --force to rebuild.", file=sys.stderr)
            return 1
        shutil.rmtree(out, onerror=lambda f, p, e: (os.chmod(p, 0o700), f(p)))
    out.mkdir(parents=True)

    git(out, "init", "-q", "-b", "main")
    git(out, "config", "core.autocrlf", "false")

    for key, when, msg, files in COMMITS:
        name, email = PEOPLE[key]
        for rel, content in files.items():
            p = out / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8", newline="\n")
        git(out, "add", "-A")
        stamp = when + TZ
        env = {
            "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email, "GIT_AUTHOR_DATE": stamp,
            "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email, "GIT_COMMITTER_DATE": stamp,
        }
        git(out, "commit", "-q", "-m", msg, env=env)

    print(f"created {out} with {len(COMMITS)} commits")
    print(subprocess.run(["git", "shortlog", "-sn", "--all"], cwd=out, capture_output=True, text=True).stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
