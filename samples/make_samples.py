"""Make made-up test documents for Photo to Table, plus an answer key (expected_*.csv) for each.

Every name, phone number, and amount is invented (phone numbers use the reserved 555-01xx range).
The "handwriting" is simulated by jittering each letter, so it is only a rough stand-in for real handwriting.

    pip install pillow                  # only needed to run this script
    python samples/make_samples.py      # writes the documents next to this script
    python samples/make_samples.py --big   # also writes samples/big/ (a ~4 MB and a ~6 MB photo, git-ignored)
"""
from __future__ import annotations

import argparse
import csv
import io
import random
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
except ImportError:
    sys.exit("This script needs Pillow: pip install pillow")

OUT = Path(__file__).resolve().parent
INK, PRINT, PAPER, GREY = (25, 35, 95), (20, 20, 20), (250, 248, 242), (95, 95, 95)


def font(size, bold=False, italic=False, serif=False):
    names = (["DejaVuSans-Bold.ttf", "arialbd.ttf"] if bold else ["DejaVuSans-Oblique.ttf", "ariali.ttf"] if italic
             else ["DejaVuSerif.ttf", "times.ttf"] if serif else ["DejaVuSans.ttf", "arial.ttf", "Arial.ttf"])
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            pass
    return ImageFont.load_default(size)


def hand(img, xy, text, size=34, wobble=1.0, color=INK):
    """Write text that looks hand-written: every letter gets its own tilt, size, and baseline."""
    x, y = xy
    f = font(size, italic=True)
    for ch in text:
        if ch == " ":
            x += size * 0.35
            continue
        tile = Image.new("RGBA", (int(size * 1.8), int(size * 1.8)), (0, 0, 0, 0))
        ImageDraw.Draw(tile).text((size * 0.4, size * 0.3), ch, font=f, fill=color + (random.randint(185, 255),))
        tile = tile.rotate(random.uniform(-7, 7) * wobble, resample=Image.BICUBIC)
        img.paste(tile, (int(x - size * 0.4), int(y - size * 0.3 + random.uniform(-3, 3) * wobble)), tile)
        x += f.getlength(ch) + random.uniform(-1.5, 2.5) * wobble
    return x


def hand_in_cell(img, box, text, dx=10, size=32, wobble=1.0):
    """Hand-write inside a box; anything that runs past the box is cut off, like a real cramped cell."""
    x0, y0, x1, y1 = box
    tile = img.crop(box)
    hand(tile, (dx, (y1 - y0) / 2 - size * 0.62), text, size, wobble)
    img.paste(tile, (x0, y0))


def scribble(img, box):
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(img)
    pts = [(x0 + 12, (y0 + y1) / 2)]
    for _ in range(14):
        pts.append((pts[-1][0] + random.uniform(4, 11), random.choice([y0 + 14, y1 - 14]) + random.uniform(-4, 4)))
    d.line(pts, fill=INK, width=3)


def photoify(img, angle=0.0, blur=0.8, quality=70, shade=True, noise=0.05):
    """Make a clean page look like a phone photo: tilt, uneven light, grain, slight blur, JPEG."""
    img = img.convert("RGB")
    bg = (72, 66, 60)
    rot = img.rotate(angle, expand=True, resample=Image.BICUBIC, fillcolor=bg)
    canvas = Image.new("RGB", (rot.width + 80, rot.height + 80), bg)
    canvas.paste(rot, (40, 40))
    if shade:
        g = Image.linear_gradient("L").resize(canvas.size).rotate(35, resample=Image.BICUBIC).point(lambda v: 200 + v * 55 // 255)
        canvas = ImageChops.multiply(canvas, Image.merge("RGB", (g, g, g)))
    canvas = Image.blend(canvas, Image.effect_noise(canvas.size, 40).convert("RGB"), noise)
    canvas = canvas.filter(ImageFilter.GaussianBlur(blur))
    buf = io.BytesIO()
    canvas.save(buf, "JPEG", quality=quality)
    return Image.open(io.BytesIO(buf.getvalue()))


# ---------- documents ----------
def table_page(title, sub, cols, widths, rows, hand_style=False, row_h=66, scribbles=(), cutoffs=(), right=()):
    W, H = sum(widths) + 120, 190 + row_h * (len(rows) + 1) + 90
    img = Image.new("RGBA", (W, H), PAPER + (255,))
    d = ImageDraw.Draw(img)
    d.text((60, 44), title, font=font(42, bold=True), fill=PRINT)
    d.text((60, 104), sub, font=font(24), fill=GREY)
    xs = [60]
    for w in widths:
        xs.append(xs[-1] + w)
    y0 = 160
    d.rectangle([xs[0], y0, xs[-1], y0 + row_h], fill=(232, 228, 218))
    for r in range(len(rows) + 2):
        d.line([(xs[0], y0 + r * row_h), (xs[-1], y0 + r * row_h)], fill=(60, 60, 60), width=2)
    for x in xs:
        d.line([(x, y0), (x, y0 + row_h * (len(rows) + 1))], fill=(60, 60, 60), width=2)
    for c, name in enumerate(cols):
        d.text((xs[c] + 12, y0 + 18), name, font=font(27, bold=True), fill=PRINT)
    for r, row in enumerate(rows, start=1):
        for c, text in enumerate(row):
            box = (xs[c] + 3, y0 + r * row_h + 3, xs[c + 1] - 3, y0 + (r + 1) * row_h - 3)
            if (r - 1, c) in scribbles:
                scribble(img, box)
            elif not text:
                continue
            elif hand_style:
                hand_in_cell(img, box, text, dx=(box[2] - box[0] - 46) if (r - 1, c) in cutoffs else 10, wobble=1.35)
            else:
                f = font(27)
                tx = box[2] - 12 - d.textlength(text, font=f) if c in right else box[0] + 9
                d.text((tx, box[1] + 15), text, font=f, fill=PRINT)
    return img


FORM_FIELDS = ["Full name", "Phone", "Date of birth", "Address", "Reason for visit", "Referred by"]


def form_page(values):
    img = Image.new("RGBA", (1000, 960), PAPER + (255,))
    d = ImageDraw.Draw(img)
    d.text((60, 50), "CLIENT INTAKE FORM", font=font(42, bold=True), fill=PRINT)
    d.text((60, 112), "Harbor Street Community Center (sample form)", font=font(24), fill=GREY)
    for i, (label, value) in enumerate(zip(FORM_FIELDS, values)):
        y = 220 + i * 120
        d.text((60, y), label + ":", font=font(28, bold=True), fill=PRINT)
        d.line([(60, y + 66), (940, y + 66)], fill=(80, 80, 80), width=2)
        hand(img, (70, y + 26), value, size=36, wobble=1.2)
    d.text((60, 920), "Office use only: ______", font=font(20), fill=GREY)
    return img


def notes_page():
    img = Image.new("RGBA", (1100, 900), PAPER + (255,))
    d = ImageDraw.Draw(img)
    d.text((60, 50), "Maple Court Neighbors - Meeting Notes", font=font(40, bold=True, serif=False), fill=PRINT)
    d.text((60, 112), "Thursday, October 15, 2026, community room", font=font(26), fill=GREY)
    lines = [
        "Present: Dana Whitfield (chair), Luis Ortega, Priya Nair, Tom Becker.",
        "",
        "1. Block party is set for Saturday, November 7. Dana will confirm the",
        "   street closure with the city by October 23.",
        "2. Budget: $320 for 40 folding chairs and $85 for the sound system.",
        "   Luis to collect quotes and report back.",
        "3. Priya will print 150 flyers. Cost estimate $42.50.",
        "4. Tom asked about the broken light at the corner of Elm and 3rd;",
        "   he will call the city on Monday.",
        "",
        "Next meeting: Thursday, November 12, 2026, 7:00 pm.",
    ]
    for i, t in enumerate(lines):
        d.text((60, 190 + i * 52), t, font=font(27, serif=True), fill=PRINT)
    return img


# ---------- data (all invented) ----------
SIGNIN_PRINTED = [["Maria Lopez", "Greenfield Library", "9:02", "11:30"], ["Jonah Whitfield", "City Parks", "9:15", "10:45"],
                  ["Aisha Khan", "Riverside Clinic", "9:40", "12:00"], ["Peter Novak", "Greenfield Library", "10:05", "11:15"],
                  ["Sofia Reyes", "Harbor Foods", "10:30", "13:10"], ["Dmitri Ivanov", "City Parks", "11:00", "11:50"]]
SIGNIN_MESSY = [["Carol Hendricks", "8:55", "11:40", "C.H."], ["Raymond Ohara", "9:20", "10:35", "R.O."],
                ["Beatriz Santos", "9:48", "11:45", ""], ["Wei Zhang", "10:10", "12:25", "W.Z."], ["Linda Park", "10:42", "13:05", "L.P."]]
FORMS = [["Daniel Okafor", "555-0142", "03/14/1988", "21 Birch Lane", "Housing assistance", "Pastor Ellis"],
         ["Grace Miller", "555-0177", "11/02/1975", "8 Quarry Road", "Food pantry", "Self"],
         ["Tomas Alvarez", "555-0119", "07/30/1992", "415 Mill St, Apt 2", "Job search help", "Maria Lopez"]]
SIGNIN_SCAN = [["Harriet Cole", "8:30", "10:15", "H.C."], ["Mateo Ruiz", "8:41", "9:55", "M.R."], ["Nadia Farouk", "9:02", "11:20", "N.F."],
               ["Oliver Grant", "9:18", "10:40", "O.G."], ["Yuki Tanaka", "9:33", "12:05", "Y.T."],
               ["Ravi Menon", "9:50", "11:10", "R.M."], ["Elena Petrova", "10:07", "12:30", "E.P."], ["Samuel Boateng", "10:25", "11:45", "S.B."],
               ["Ines Duarte", "10:44", "12:15", "I.D."]]
INVOICE = [["Folding chairs (rental)", "40", "$4.00", "$160.00"], ["Sound system (day)", "1", "$85.00", "$85.00"],
           ["Printed flyers", "150", "$0.28", "$42.00"], ["Banner, 6 ft", "2", "$31.50", "$63.00"], ["Delivery", "1", "$25.00", "$25.00"]]


def write_csv(name, header, rows):
    with open(OUT / name, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([header, *rows])


def save(img, name, **kw):
    img.convert("RGB").save(OUT / name, **kw)
    print("wrote", name)


def fit_jpeg(img, name, lo, hi):
    """Save as JPEG at the highest quality that stays under hi bytes; report if it is under lo."""
    for q in range(98, 30, -4):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q)
        if buf.tell() <= hi:
            (OUT / "big").mkdir(exist_ok=True)
            (OUT / "big" / name).write_bytes(buf.getvalue())
            print(f"wrote big/{name}  {buf.tell() / 1e6:.1f} MB (target {lo / 1e6:.0f}-{hi / 1e6:.0f})", "" if buf.tell() >= lo else "  <-- below target")
            return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--big", action="store_true", help="also write a ~4 MB and a ~6 MB photo to samples/big/")
    args = ap.parse_args()

    random.seed(11)
    save(table_page("Visitor Sign-In", "Greenfield Library - Tuesday, Oct 13, 2026", ["Name", "Organization", "Time in", "Time out"],
                    [330, 330, 170, 170], SIGNIN_PRINTED), "01_signin_printed.png")
    write_csv("expected_01_signin_printed.csv", ["Name", "Organization", "Time in", "Time out"], SIGNIN_PRINTED)

    random.seed(12)
    messy = [r[:] for r in SIGNIN_MESSY]
    messy[3][2] = "12:25"
    page = table_page("Volunteer Sign-In", "Riverside Pantry - Oct 14", ["Name", "Time in", "Time out", "Initials"],
                      [360, 190, 190, 190], messy, hand_style=True, scribbles={(2, 3)}, cutoffs={(3, 2)})
    save(photoify(page, angle=-2.2, blur=1.0, quality=62), "02_signin_messy_photo.jpg", quality=62)
    write_csv("expected_02_signin_messy_photo.csv", ["Name", "Time in", "Time out", "Initials"], SIGNIN_MESSY)

    for k, vals in enumerate(FORMS):
        random.seed(20 + k)
        page = form_page(vals)
        if k == 1:
            save(photoify(page, angle=1.6, blur=0.7, quality=75), "04_intake_form_b.jpg", quality=75)
        else:
            save(page, f"0{3 + k}_intake_form_{'abc'[k]}.png")
    write_csv("expected_03-05_intake_forms.csv", FORM_FIELDS, FORMS)

    random.seed(30)
    inv = table_page("INVOICE #2026-0418", "Brightside Print Co. (sample) - billed to Maple Court Neighbors - Oct 16, 2026",
                     ["Description", "Qty", "Unit price", "Amount"], [450, 110, 190, 190], INVOICE, right={1, 2, 3})
    ty = inv.height - 10
    page = Image.new("RGBA", (inv.width, inv.height + 150), PAPER + (255,))  # room for the totals, on paper
    page.paste(inv, (0, 0))
    inv = page
    d = ImageDraw.Draw(inv)
    for i, (k, v) in enumerate([("Subtotal", "$375.00"), ("Tax (8%)", "$30.00"), ("Total due", "$405.00")]):
        d.text((560, ty + i * 44), k, font=font(27, bold=(i == 2)), fill=PRINT)
        d.text((880, ty + i * 44), v, font=font(27, bold=(i == 2)), fill=PRINT)
    save(photoify(inv, angle=0.8, blur=0.5, quality=82, noise=0.03), "06_invoice_photo.jpg", quality=82)
    write_csv("expected_06_invoice_photo.csv", ["Description", "Qty", "Unit price", "Amount"], INVOICE)

    random.seed(40)
    save(notes_page(), "07_meeting_notes.png")
    save(Image.new("RGB", (900, 600), (255, 255, 255)), "08_blank_page.png")

    pages = [Image.open(OUT / f).convert("RGB") for f in ("03_intake_form_a.png", "04_intake_form_b.jpg", "05_intake_form_c.png")]
    pages[0].save(OUT / "09_forms_3pages.pdf", save_all=True, append_images=pages[1:])
    print("wrote 09_forms_3pages.pdf")

    random.seed(60)
    cols = ["Name", "Time in", "Time out", "Initials"]
    scans = []
    for k, chunk in enumerate((SIGNIN_SCAN[:5], SIGNIN_SCAN[5:])):
        pg = table_page(f"Volunteer Sign-In (page {k + 1} of 2)", "Eastside Garden Day - Oct 17", cols, [360, 190, 190, 190], chunk, hand_style=True)
        scans.append(photoify(pg, angle=(-1.1, 1.4)[k], blur=0.6, quality=70).convert("RGB"))
    scans[0].save(OUT / "10_signin_2pages_scan.pdf", save_all=True, append_images=scans[1:])
    write_csv("expected_10_signin_2pages_scan.csv", cols, SIGNIN_SCAN)
    print("wrote 10_signin_2pages_scan.pdf")

    if args.big:
        random.seed(50)
        for name, scale, lo, hi in (("big_photo_4mb.jpg", 2.9, 3_500_000, 4_800_000), ("too_big_6mb.jpg", 3.4, 5_400_000, 9_000_000)):
            base = photoify(table_page("Volunteer Sign-In", "Large photo test", ["Name", "Time in", "Time out", "Initials"],
                                       [360, 190, 190, 190], SIGNIN_MESSY, hand_style=True), angle=-1.5, quality=90)
            base = base.resize((int(base.width * scale), int(base.height * scale)), Image.LANCZOS)
            noise = Image.effect_noise(base.size, 60).convert("RGB")
            fit_jpeg(Image.blend(base.convert("RGB"), noise, 0.10), name, lo, hi)


if __name__ == "__main__":
    main()
