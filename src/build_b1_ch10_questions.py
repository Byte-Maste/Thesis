"""Write the Chapter 10 draft question files.

Questions are original. They are not the textbook review quiz and not the
ManuRAG 1,515-pair set. Split is sha256(id) mod 10: 0-2 dev, 3-9 test.
Status stays draft until a second person reviews them.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "benchmarks" / "b1"


def split_for(question_id: str) -> str:
    bucket = int(hashlib.sha256(question_id.encode("utf-8")).hexdigest(), 16) % 10
    return "dev" if bucket < 3 else "test"


def row(question_id: str, category: str, question: str, gold: str, evidence: list[dict], hop: int, **extra) -> dict:
    item = {
        "id": question_id,
        "benchmark": "b1",
        "category": category,
        "topic": "processes",
        "question": question,
        "gold_answer": gold,
        "gold_evidence": evidence,
        "hop_count": hop,
        "requires_visual": False,
        "split": split_for(question_id),
        "author": "kc",
        "reviewer": "",
        "status": "draft",
    }
    item.update(extra)
    return item


def evidence(page: int, note: str) -> list[dict]:
    return [{"doc": "groover-4th-ch10", "page": page, "note": note}]


def build() -> dict[str, list[dict]]:
    v_base = math.sqrt(2 * 981 * 80)
    pattern_al = 400 * 1.013
    pattern_zn = 150 * 1.026
    heat = 8 * 50 * (0.5 * (1000 - 0) + 200 + 0.6 * (1100 - 1000))
    tts = 0.8 * (450 / 150) ** 2
    va_ratio = 18 / 6
    tts_riser = 2 * (va_ratio ** 2)

    mathq = [
        row(
            "b1-mathq-0101",
            "MathQ",
            "A sprue is 80 cm tall. Take g = 981 cm/s^2. Metal enters the top at zero velocity, friction is ignored, and the stream stays at atmospheric pressure. What is the velocity at the base?",
            f"{v_base:.1f} cm/s",
            evidence(224, "v = sqrt(2gh)"),
            1,
            gold_value=round(v_base, 1),
            gold_units="cm/s",
        ),
        row(
            "b1-mathq-0102",
            "MathQ",
            "Molten metal flows at 200 cm/s through a channel with a cross-sectional area of 3.5 cm^2. What is the volumetric flow rate?",
            "700 cm^3/s",
            evidence(224, "Q = vA"),
            1,
            gold_value=700,
            gold_units="cm^3/s",
        ),
        row(
            "b1-mathq-0103",
            "MathQ",
            "A mold cavity volume is 2800 cm^3 and the gate delivers 700 cm^3/s. Ignoring friction, what is the minimum mold filling time?",
            "4 s",
            evidence(224, "TMF = V/Q"),
            1,
            gold_value=4,
            gold_units="s",
        ),
        row(
            "b1-mathq-0104",
            "MathQ",
            "At the top of a sprue the metal speed is 40 cm/s and the area is 8 cm^2. The base area is 2 cm^2. Using continuity, what is the speed at the base?",
            "160 cm/s",
            evidence(224, "Q = v1 A1 = v2 A2"),
            1,
            gold_value=160,
            gold_units="cm/s",
        ),
        row(
            "b1-mathq-0105",
            "MathQ",
            "An alloy is poured at 1150 C and freezing begins at its liquidus of 1080 C. What is the superheat?",
            "70 C",
            evidence(223, "superheat = pouring temperature minus freezing temperature"),
            1,
            gold_value=70,
            gold_units="C",
        ),
        row(
            "b1-mathq-0106",
            "MathQ",
            "A casting has volume 450 cm^3 and surface area 150 cm^2. The mold constant Cm is 0.8 min/cm^2 and n = 2. What is the total solidification time by Chvorinov's rule?",
            f"{tts:.1f} min",
            evidence(228, "TTS = Cm (V/A)^n"),
            1,
            gold_value=round(tts, 1),
            gold_units="min",
        ),
        row(
            "b1-mathq-0107",
            "MathQ",
            "Fifty cubic centimeters of metal (density 8 g/cm^3) are heated from 0 C to a pouring temperature of 1100 C. Melting point is 1000 C, solid specific heat is 0.5 J/g-C, liquid specific heat is 0.6 J/g-C, and heat of fusion is 200 J/g. Assume no losses and the same density in both states. How much heat must be added?",
            f"{heat:.0f} J",
            evidence(222, "H = rho V [Cs(Tm-To) + Hf + Cl(Tp-Tm)]"),
            1,
            gold_value=round(heat),
            gold_units="J",
        ),
        row(
            "b1-mathq-0108",
            "MathQ",
            "A finished aluminum-alloy casting must be 400 mm long. The linear pattern shrinkage allowance for aluminum alloys is 1.3%. How long should the pattern dimension be?",
            f"{pattern_al:.1f} mm",
            evidence(230, "pattern is oversized by the linear shrinkage allowance"),
            1,
            gold_value=round(pattern_al, 1),
            gold_units="mm",
        ),
        row(
            "b1-mathq-0109",
            "MathQ",
            "A finished zinc casting must be 150 mm long. Zinc's linear shrinkage allowance is 2.6%. How long should the pattern dimension be?",
            f"{pattern_zn:.1f} mm",
            evidence(230, "Table 10.1 zinc linear shrinkage 2.6%"),
            1,
            gold_value=round(pattern_zn, 1),
            gold_units="mm",
        ),
        row(
            "b1-mathq-0110",
            "MathQ",
            "A cylindrical riser has diameter equal to height, and that diameter is 18 cm. Chvorinov's exponent n is 2 and the mold constant is 2 min/cm^2. For this shape the volume-to-area ratio equals D/6. What is the total solidification time?",
            f"{tts_riser:.0f} min",
            evidence(232, "cylinder with D = H has V/A = D/6"),
            2,
            gold_value=round(tts_riser),
            gold_units="min",
        ),
    ]

    mcq = [
        ("b1-mcq-0101", "A shop set up to make molds, melt metal, and clean castings is called a (a) rolling mill (b) foundry (c) machine shop (d) pattern loft", "b", 219),
        ("b1-mcq-0102", "A casting that already has its final geometry and dimensions, with no further shaping, is (a) near net shape (b) an ingot (c) net shape (d) a core", "c", 219),
        ("b1-mcq-0103", "The network of channels that carries molten metal from outside a closed mold into the cavity is the (a) parting line (b) gating system (c) flask (d) chill", "b", 220),
        ("b1-mcq-0104", "The cope and the drag of a sand mold meet at the (a) sprue (b) parting line (c) riser (d) vent", "b", 221),
        ("b1-mcq-0105", "Interior surfaces of a casting are set by a form placed in the cavity called a (a) pattern (b) flask (c) core (d) pouring cup", "c", 221),
        ("b1-mcq-0106", "Which process is the familiar example of permanent-mold casting? (a) sand casting (b) die casting (c) ingot casting (d) boring", "b", 221),
        ("b1-mcq-0107", "Which mold is destroyed to recover the casting? (a) a steel die used for many parts (b) an expendable sand mold (c) a vented permanent mold (d) a reusable ceramic shell that opens", "b", 221),
        ("b1-mcq-0108", "Superheat is the gap between (a) room temperature and the solidus (b) the pouring temperature and the temperature where freezing starts (c) the liquidus and the solidus (d) the mold wall and the pattern", "b", 223),
        ("b1-mcq-0109", "Erosion of mold walls during filling is made worse by (a) laminar flow (b) a blind riser (c) turbulent flow (d) a fine-grained skin", "c", 223),
        ("b1-mcq-0110", "In casting, fluidity is (a) identical to viscosity (b) the inverse of viscosity (c) the heat of fusion (d) the mold constant", "b", 224),
        ("b1-mcq-0111", "In a spiral mold test, greater fluidity shows up as (a) a shorter filled spiral (b) a longer filled spiral (c) a wider sprue (d) a smaller riser", "b", 225),
        ("b1-mcq-0112", "A pure metal freezes (a) across a wide mushy zone (b) at one constant temperature (c) only after an alloy solidus (d) when the riser is open to air", "b", 225),
        ("b1-mcq-0113", "Chvorinov's rule is used to estimate (a) mold filling time (b) total solidification time (c) the pattern shrinkage allowance (d) superheat", "b", 228),
        ("b1-mcq-0114", "Dendrites that still hold pockets of liquid form a region called the (a) pipe (b) mushy zone (c) cope (d) sprue", "b", 227),
        ("b1-mcq-0115", "The lead-tin eutectic freezes at about (a) 327 C (b) 232 C (c) 183 C (d) 1083 C", "c", 228),
        ("b1-mcq-0116", "The void left where the last metal freezes, with no liquid left to feed it, is a (a) chill (b) pipe (c) core (d) runner", "b", 229),
        ("b1-mcq-0117", "High-carbon cast iron can expand late in freezing because of (a) turbulence (b) graphitization (c) a larger flask (d) superheat", "b", 230),
        ("b1-mcq-0118", "An external chill is placed in the mold wall to (a) slow freezing in a thin section (b) pull heat out faster than the surrounding sand (c) vent the cope (d) measure fluidity", "b", 230),
        ("b1-mcq-0119", "An open riser tends to freeze sooner than a blind riser because it (a) never touches the casting (b) loses heat from its exposed top (c) is made only of wax (d) sits in the drag", "b", 232),
        ("b1-mcq-0120", "A side riser joins the casting by (a) the pouring cup (b) a small channel on the side of the casting (c) the pattern (d) an internal chill", "b", 232),
    ]
    mcq_rows = [
        row(
            qid,
            "MCQ",
            text,
            letter,
            evidence(page, "chapter 10"),
            1,
            gold_choice=letter,
        )
        for qid, text, letter, page in mcq
    ]

    rq = [
        row(
            "b1-rq-0101",
            "RQ",
            "Why is a sprue made narrower at the bottom?",
            "The metal speeds up as it falls, from Bernoulli's relation. Continuity then requires a smaller area so the volume flow rate stays constant. If the sprue is not tapered, air is sucked into the stream and carried into the cavity.",
            evidence(224, "tapered sprue") + evidence(224, "Bernoulli and continuity"),
            2,
        ),
        row(
            "b1-rq-0102",
            "RQ",
            "After metal is poured into an open cylindrical mold, what three contractions occur, and what is the pipe?",
            "The liquid shrinks while it cools before freezing, the metal shrinks again as it changes from liquid to solid, and the solid shrinks as it cools to room temperature. A pipe is the cavity left in the last region to freeze when liquid metal cannot feed that spot.",
            evidence(229, "three shrinkage steps and pipe"),
            1,
        ),
        row(
            "b1-rq-0103",
            "RQ",
            "Why give a riser a larger volume-to-surface-area ratio than the casting?",
            "Chvorinov's rule says solidification time grows with the volume-to-area ratio when the mold constant is the same. The riser must freeze after the casting so it can keep feeding liquid metal and offset solidification shrinkage.",
            evidence(228, "Chvorinov") + evidence(229, "riser feeds shrinkage"),
            2,
        ),
        row(
            "b1-rq-0104",
            "RQ",
            "How does freezing of most alloys differ from freezing of a pure metal?",
            "A pure metal freezes at a single temperature. Most alloys freeze from the liquidus down to the solidus. During that range, solid dendrites and trapped liquid coexist in the mushy zone.",
            evidence(225, "pure metal") + evidence(227, "mushy zone"),
            2,
        ),
        row(
            "b1-rq-0105",
            "RQ",
            "A casting has thin ribs far from the riser and a heavy section next to the riser. Which region should freeze first, and why?",
            "The thin ribs should freeze first. Their lower volume-to-area ratio and their distance from the riser make them solidify while the heavy section and the riser are still liquid, which is the directional-solidification pattern that avoids shrinkage voids.",
            evidence(230, "directional solidification") + evidence(228, "V/A and solidification time"),
            2,
        ),
        row(
            "b1-rq-0106",
            "RQ",
            "Why can a blind riser stay liquid longer than an open riser of similar size?",
            "An open riser is exposed at the top of the cope, so heat leaves through that surface and freezing speeds up. A blind riser is enclosed in the mold, so it does not lose heat that way.",
            evidence(232, "open versus blind riser"),
            1,
        ),
        row(
            "b1-rq-0107",
            "RQ",
            "Why do expendable molds allow more complicated shapes than permanent molds?",
            "An expendable mold is broken to remove the casting, so the cavity can lock around the part. A permanent mold must open in sections, which limits the shapes that can be withdrawn.",
            evidence(221, "expendable versus permanent mold geometry"),
            1,
        ),
        row(
            "b1-rq-0108",
            "RQ",
            "What goes wrong if the short channel between a riser and the casting freezes before the casting does?",
            "The casting is cut off from the liquid metal in the riser. Shrinkage in the casting then cannot be fed, so voids form. The channel is kept short and large enough in section so it stays open until the casting has solidified.",
            evidence(231, "riser connection must not freeze first"),
            1,
        ),
        row(
            "b1-rq-0109",
            "RQ",
            "Why are sand-casting patterns made larger than the finished part?",
            "The metal shrinks as it solidifies and then as the solid cools. The pattern shrinkage allowance makes the mold cavity oversized so the cooled casting meets the required dimensions.",
            evidence(221, "pattern oversized") + evidence(230, "pattern shrinkage allowance"),
            2,
        ),
        row(
            "b1-rq-0110",
            "RQ",
            "What does a pouring cup do at the top of the downsprue, and which two defects does turbulent filling encourage?",
            "The pouring cup reduces splash and turbulence as metal enters the sprue. Turbulence promotes oxide films that can be trapped in the casting and it wears away the mold surface, especially in the cavity.",
            evidence(221, "pouring cup") + evidence(223, "turbulence, oxides, erosion"),
            2,
        ),
        row(
            "b1-rq-0111",
            "RQ",
            "Why do pure metals and eutectic alloys usually flow farther in a mold than alloys that freeze over a wide temperature range?",
            "They freeze at one temperature, so partly solid metal does not block the flow. Alloys with a freezing range form solid pieces that interfere with the remaining liquid and lower fluidity. A higher heat of fusion also tends to increase the measured fluidity.",
            evidence(225, "fluidity and freezing range"),
            1,
        ),
        row(
            "b1-rq-0112",
            "RQ",
            "From the mold wall to the center, what grain structure forms when a pure metal solidifies in a casting?",
            "A thin skin at the wall is fine and randomly oriented because the mold chills it. Farther in, grains grow as dendrites toward the center and become coarse columnar grains.",
            evidence(226, "grain structure of a pure-metal casting"),
            1,
        ),
    ]
    return {"MathQ": mathq, "MCQ": mcq_rows, "RQ": rq}


def main() -> None:
    grouped = build()
    OUT.mkdir(parents=True, exist_ok=True)
    legacy = OUT / "questions.jsonl"
    if legacy.exists():
        legacy.unlink()
    counts = {"dev": 0, "test": 0}
    for category, rows in grouped.items():
        path = OUT / f"{category}.jsonl"
        path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in rows), encoding="utf-8")
        for item in rows:
            counts[item["split"]] += 1
        print(f"{path.name} {len(rows)}")
    print(f"dev {counts['dev']} test {counts['test']}")


if __name__ == "__main__":
    main()
