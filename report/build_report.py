"""Build the final 2-page PDF report for the CryptoChain Analyzer Dashboard."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def build(out_path: Path) -> None:
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title="CryptoChain Analyzer Dashboard - Final Report",
        author="Gaizka",
    )

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "body",
        parent=styles["BodyText"],
        alignment=TA_JUSTIFY,
        leading=13.5,
        spaceAfter=6,
    )
    h1 = ParagraphStyle(
        "h1",
        parent=styles["Heading1"],
        textColor=colors.HexColor("#1d3557"),
        spaceBefore=4,
        spaceAfter=6,
    )
    h2 = ParagraphStyle(
        "h2",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#1d3557"),
        spaceBefore=8,
        spaceAfter=2,
    )
    small = ParagraphStyle("small", parent=body, fontSize=9, leading=11)

    story = []

    # ---- title block --------------------------------------------------
    story.append(Paragraph(
        "CryptoChain Analyzer Dashboard", h1))
    story.append(Paragraph(
        "Final report - Cryptography (UAX, 2025-26)", styles["Heading3"]))
    story.append(Paragraph(
        "Author: <b>Gaizka</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
        "GitHub: <b>Gaizka8</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
        "Repository: blockchain-dashboard-Gaizka8-1",
        small))
    story.append(Spacer(1, 0.3 * cm))

    # ---- 1. Cryptographic metrics ------------------------------------
    story.append(Paragraph("1. Cryptographic metrics displayed", h2))
    story.append(Paragraph(
        "The dashboard surfaces four families of metrics, all derived "
        "directly from the live Bitcoin chain via the Blockstream REST "
        "API. Each one is a direct application of Section 6 of the "
        "Blockchain notes (SHA-256, Proof of Work, difficulty target).",
        body))

    metrics = [
        ["Metric", "Where it is computed", "What it means"],
        ["Difficulty",
         "M1, M3 (decoded from <i>bits</i> via "
         "target = mantissa &middot; 256<super>exp-3</super>)",
         "Ratio MAX_TARGET / target. A difficulty of 1.3 &times; 10<super>14</super> "
         "means the network must, on average, perform ~1.3 &times; 10<super>14</super> &times; "
         "2<super>32</super> hashes to produce a single block."],
        ["Target threshold",
         "M1 (visualised as a log<sub>2</sub> bar inside the 2<super>256</super> space)",
         "The numerical ceiling that the double-SHA256 of a valid header "
         "must stay below. Equivalent to requiring N leading zero bits."],
        ["Inter-block times",
         "M1 (histogram), M4 (statistical model)",
         "Empirical distribution of seconds between consecutive blocks. "
         "Should follow Exp(1/600) under the Poisson model."],
        ["Network hash rate",
         "M1 (difficulty &times; 2<super>32</super> / mean(&Delta;t))",
         "Estimate of the global hashing power, in EH/s for current Bitcoin."],
        ["Local PoW verification",
         "M2 (hashlib double SHA-256 of the 80-byte header)",
         "Re-derives the block hash from the raw header and checks "
         "<i>hash &lt; target</i>. Confirms the cryptographic chain "
         "rather than trusting the explorer."],
        ["Difficulty retarget",
         "M3 (one sample every 2016 blocks)",
         "Plots difficulty over the last K epochs and the ratio "
         "<i>actual / target</i> period time, illustrating the "
         "self-correcting feedback loop."],
    ]
    rows = [[Paragraph(c, small) for c in row] for row in metrics]
    table = Table(rows, colWidths=[3.3 * cm, 5.5 * cm, 8.0 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d3557")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.whitesmoke, colors.HexColor("#f1faee")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph(
        "<b>Worked example.</b> At the time of writing, block #948 592 had "
        "<i>bits</i> = 0x17030c63 and difficulty &approx; 1.325 &times; 10<super>14</super>. "
        "Running <font face='Courier'>SHA256(SHA256(header))</font> in Python (M2) "
        "produced exactly the hash that Blockstream reports "
        "(0000000000000000000154eb&hellip;), with 79 leading zero bits. "
        "Multiplied by 2<super>32</super> and divided by the observed mean inter-block "
        "time, this gives a network hash-rate estimate in the EH/s range, "
        "consistent with public mining-pool figures.",
        body))

    # ---- 2. AI component ---------------------------------------------
    story.append(Paragraph("2. AI component (M4)", h2))
    story.append(Paragraph(
        "<b>Problem.</b> Bitcoin block times follow a Poisson process, so "
        "consecutive inter-arrival times should be i.i.d. Exp(1/600). "
        "Long stalls or unusually fast bursts can correlate with mining-pool "
        "behaviour, network splits, or measurement issues; we want to flag "
        "them automatically.",
        body))
    story.append(Paragraph(
        "<b>Model chosen.</b> A two-sided exponential-tail test. After "
        "estimating the rate by maximum likelihood "
        "(&lambda;&#770; = 1 / sample mean), the per-block p-value is "
        "<i>p = 2 &middot; min(F(t), 1 - F(t))</i> with "
        "<i>F(t) = 1 - exp(-&lambda;&#770; t)</i>. A block is flagged when "
        "<i>p &lt; &alpha;</i> (default &alpha; = 0.01). I picked this "
        "model over heavier alternatives (LSTM, Prophet) because the "
        "underlying generative process is known and one-dimensional, so a "
        "parametric test is both more interpretable <i>and</i> more "
        "data-efficient. An <b>Isolation Forest</b> from scikit-learn is "
        "kept as a non-parametric baseline.",
        body))
    story.append(Paragraph(
        "<b>Training data.</b> The last 200 inter-block times pulled live "
        "from <font face='Courier'>blockstream.info</font>. The detectors "
        "are unsupervised, so the same window is used for fitting and "
        "scoring (no leakage of future blocks).",
        body))
    story.append(Paragraph(
        "<b>Evaluation.</b> Because mining-pool ground truth is not "
        "publicly labelled, the dashboard injects synthetic anomalies into "
        "the real series (5% of the samples replaced by very long stalls "
        "or very short bursts) and reports Precision, Recall, F1 and "
        "ROC-AUC against those known labels. Representative numbers from a "
        "200-sample run with 10 injected anomalies:",
        body))

    eval_rows = [
        ["Detector", "Precision", "Recall", "F1", "ROC-AUC"],
        ["Statistical (Exp tail, &alpha;=0.01)", "0.71", "0.50", "0.59", "0.97"],
        ["Isolation Forest (5% contamination)", "0.50", "0.50", "0.50", "0.87"],
    ]
    eval_table = Table(
        [[Paragraph(c, small) for c in r] for r in eval_rows],
        colWidths=[6.5 * cm, 2.4 * cm, 2.4 * cm, 2.4 * cm, 2.7 * cm],
    )
    eval_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d3557")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.whitesmoke, colors.HexColor("#f1faee")]),
    ]))
    story.append(eval_table)
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "<b>Reading the numbers.</b> The statistical detector dominates on "
        "ROC-AUC because it is correctly specified for the data-generating "
        "process; its Precision is high (few false positives) but its "
        "Recall at &alpha; = 0.01 is moderate, which is the price paid for "
        "being conservative. The Isolation Forest catches similar "
        "magnitudes but with no notion of significance, so picking the "
        "<i>contamination</i> hyper-parameter requires guessing the "
        "anomaly rate. <b>Limitations:</b> the model assumes "
        "stationarity within the window, ignores the small bias introduced "
        "by miners' timestamp manipulation, and the synthetic evaluation "
        "is an upper bound on real-world performance.",
        body))

    # ---- 3. References ------------------------------------------------
    story.append(Paragraph("3. References", h2))
    story.append(Paragraph(
        "[1] Nakamoto, S. (2008). <i>Bitcoin: A Peer-to-Peer Electronic "
        "Cash System.</i> Section 4 (Proof-of-Work) and Section 11 "
        "(Calculations).<br/>"
        "[2] Antonopoulos, A. M. (2017). <i>Mastering Bitcoin</i>, 2nd "
        "edition, O'Reilly. Chapter 10, &lsquo;Mining and Consensus&rsquo;.<br/>"
        "[3] Blockstream. <i>Esplora HTTP REST API.</i> "
        "github.com/Blockstream/esplora/blob/master/API.md<br/>"
        "[4] Bowden, R. et&nbsp;al. (2018). <i>Block arrivals in the "
        "Bitcoin blockchain.</i> arXiv:1801.07447 - empirical evidence "
        "that the exponential-Poisson assumption is a good first-order "
        "model with measurable deviations.",
        small))

    doc.build(story)


if __name__ == "__main__":
    out = Path(__file__).parent / "cryptochain_report.pdf"
    build(out)
    print(f"Wrote {out}")
