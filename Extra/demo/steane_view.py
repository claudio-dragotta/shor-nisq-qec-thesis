"""Disegno SVG del codice di Steane [[7,1,3]]: 7 qubit dati + 6 "spie" di sindrome (3 Z-type,
3 X-type), con animazione su qubit errato e sindrome accesa — stesso stile di circuit_view.py.
"""

R = 22
GAP = 64
TOP_Y = 40
CHECK_Y = 130
LABEL_GZ = ["gz1", "gz2", "gz3"]
LABEL_GX = ["gx1", "gx2", "gx3"]
PAULI_COLOR = {"X": "#E76F51", "Y": "#9B5DE5", "Z": "#2E86AB"}


def render_steane_svg(result):
    """result: dict da steane_backend.run_injection (o None per lo stato senza errore)."""
    n = 7
    width = GAP * (n - 1) + 2 * R + 40
    height = CHECK_Y + 60

    pauli = result["pauli"] if result else None
    err_qubit = result["qubit"] if result and pauli else None
    sz = result["sz"] if result else (0, 0, 0)
    sx = result["sx"] if result else (0, 0, 0)
    fired = list(sz) + list(sx)
    corrected_qubit = None
    if result and pauli:
        corrected_qubit = result["q_x"] if pauli in ("X", "Y") else result["q_z"]

    def qx(i):
        return 30 + R + i * GAP

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" font-family="Helvetica,Arial,sans-serif">',
        """<style>
        @keyframes pulse-err { 0%{stroke-opacity:0.4;} 50%{stroke-opacity:1;} 100%{stroke-opacity:0.4;} }
        @keyframes pulse-fire { 0%{opacity:0.5;} 50%{opacity:1;} 100%{opacity:0.5;} }
        .err-ring { animation: pulse-err 1s ease-in-out infinite; }
        .fired { animation: pulse-fire 0.9s ease-in-out infinite; }
        .qtext { font-size:11px; fill:white; text-anchor:middle; dominant-baseline:middle; font-weight:600; }
        .qlabel { font-size:9px; fill:#999; text-anchor:middle; }
        .checklabel { font-size:9px; fill:#ccc; text-anchor:middle; }
        </style>""",
    ]

    # 7 qubit dati
    for i in range(n):
        x = qx(i)
        is_err = (i == err_qubit)
        is_corrected = (i == corrected_qubit)
        fill = PAULI_COLOR.get(pauli, "#555") if is_err else "#2A2A3A"
        parts.append(f'<circle cx="{x}" cy="{TOP_Y}" r="{R}" fill="{fill}" stroke="#666" stroke-width="1.5"/>')
        if is_err:
            parts.append(f'<text class="qtext" x="{x}" y="{TOP_Y+1}">{pauli}</text>')
        if is_corrected:
            parts.append(
                f'<circle class="err-ring" cx="{x}" cy="{TOP_Y}" r="{R+5}" fill="none" '
                f'stroke="#2A9D8F" stroke-width="3"/>'
            )
        parts.append(f'<text class="qlabel" x="{x}" y="{TOP_Y+R+16}">q{i}</text>')

    # 6 spie di sindrome
    check_labels = LABEL_GZ + LABEL_GX
    check_xs = [qx(0.5), qx(1.5), qx(2.5), qx(3.8), qx(4.8), qx(5.8)]
    for k, (label, bit) in enumerate(zip(check_labels, fired)):
        x = check_xs[k]
        color = "#E76F51" if bit else "#333"
        cls = "fired" if bit else ""
        parts.append(f'<rect class="{cls}" x="{x-16}" y="{CHECK_Y-14}" width="32" height="28" rx="5" fill="{color}"/>')
        parts.append(f'<text class="checklabel" x="{x}" y="{CHECK_Y+30}">{label}</text>')
        parts.append(f'<text class="qtext" x="{x}" y="{CHECK_Y+1}">{bit}</text>')

    parts.append(
        f'<text x="{qx(1)}" y="{CHECK_Y-24}" font-size="9" fill="#888">← sindrome Z (rileva X)</text>'
    )
    parts.append(
        f'<text x="{qx(4.3)}" y="{CHECK_Y-24}" font-size="9" fill="#888">sindrome X (rileva Z) →</text>'
    )

    parts.append("</svg>")
    return "".join(parts)
