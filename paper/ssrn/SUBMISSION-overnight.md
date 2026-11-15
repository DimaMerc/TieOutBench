# SSRN submission package — the overnight ETF report (fourth report in the TieOutBench series)

**POSTED: abstract ID 7688088 — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7688088 — submitted 2026-11-10, listed and given its DOI by 2026-11-13
(public view yes; status APPROVED and not yet DISTRIBUTED on 2026-11-15, when it showed 68 abstract views and 29 downloads).
DOI: 10.2139/ssrn.7688088, registered with Crossref 2026-11-13 15:12 UTC, with the ORCID attached.
Posted under the SUBTITLE as its title ("Sixty Nights of Overnight Trading in Ten US ETFs, Measured Before the Exchanges
Begin Overnight Sessions, With a Frankfurt Control"); the PDF's first line is "After the Close: ...". Crossref carries the
subtitle, so a citation by DOI shows that title.
Threaded on 2026-11-15 into the paper's front matter (now version 1.1; PDF rebuilt, 23 pages), README.md, docs/index.html,
the report's own page docs/overnight-paper.html (preview image docs/og-overnight-paper.png, served PDF
docs/overnight-paper.pdf), docs/sitemap.xml and the driver post's first comment.**

**Version 1.1 differs from the PDF now on SSRN** in the passages listed in the paper's Appendix C: the abstract's
"no indicative value is updated" reads "is required"; Section 2 mentions a vendor's indicative-value service; Finding 8
adds Cboe EDGX's statement on market-maker requirements and 24X's overnight incentive; Section 5 cites Nasdaq's 2012
filing for an order pegged to an indicative value; four references added (24 to 27). **Four figures changed by one unit
in their last digit** (found 2026-11-15; Appendix C item 6): they had been rounded twice, once in the result files and
again in the text. Finding 3: median distance after the Asian sessions 34 bps, not 35. Finding 7: error of the German
estimate before the model's choice 37 bps, not 38; first scoring of the emerging-markets choice 0.16, not 0.17. Finding
8 table: 90th percentile of the IUSA fund 8 bps, not 9. None is in the abstract, the post, the card or the site pages.
The pipeline now stores three more digits (`ovn/util.py: stored`), the pinned commands were rerun, five files under
`prototypes/overnight/data/public/` changed in digits only, and the tie-out passes against the more
precise values. **One statement was given its count** (found 2026-11-15 in the posting-day check of the driver post;
Appendix C item 7): Finding 1 said the overnight prints sat further from a NAV-anchored value than from a close-anchored
one and gave the S&P and bitcoin funds; it now says "in six of the seven funds that start from an official NAV", with
the exception named (the Germany fund, 23 prints), and Appendix A lists all seven medians. The tie-out checks these
too and now covers 259 figures (247 before). PDF rebuilt 2026-11-15 17:23, 23 pages. To bring SSRN in line, in this order:
(1) commit and push the fourth report's files first, because version 1.1 says the result files in the repository keep
three more digits and that is true on GitHub only after the push; (2) on SSRN, My Papers, "Revise" on the paper's row;
remove the current PDF with the X beside it and upload `paper/etf-overnight-reference-value-v1.pdf`; in the abstract
field change one word, "no indicative value is updated" to "no indicative value is required" (a word-by-word comparison
of version 1 and version 1.1 shows no other difference; the series line at the end of the field stays); leave the title,
keywords and date written; "Confirm Revision" (some help pages call the button "Submit Revision"); (3) open the public
page and check that the PDF's first page says "Version 1.1"; (4) then the post. SSRN's support pages say a revision is
"immediately available on the paper's public abstract page", that it overwrites the earlier version and that support
cannot undo it (read on 2026-11-15 as search summaries of elsevier.support/ssrn/answer/the-new-ssrn-revision-process and
.../how-do-i-revise-a-submission; the pages themselves did not open). Left for the author: that upload, the LinkedIn
Publications entry and the Featured card.

Everything to paste into the SSRN submission form. The PDF to upload: `paper/etf-overnight-reference-value-v1.pdf`,
built by `python paper/build_overnight.py` (23 pages, tables only, no figures; current build 2026-11-15, version 1.1).
If the PDF is open in a viewer the build cannot replace it: it prints a NOTE and writes
`etf-overnight-reference-value-v1.rebuilt.pdf` instead. Page 1 of the right file reads "a static band 20%
either side of the close".

**Committed and pushed 2026-11-10: 59330e2 on origin/main** (the report's .md, `paper/build_overnight.py` and
`prototypes/overnight/`; the files are reachable on GitHub). The front matter and the abstract's last line
point there.

## Title
After the Close: What ETF Shares Are Worth When Nobody Can Create or Redeem

(The subtitle, if the form has room for it or you prefer one line: "Sixty nights of overnight trading in ten US
ETFs, measured before the exchanges begin overnight sessions, with a Frankfurt control". The earlier reports
were posted with the title only.)

## Author
Dmitry Krutous — Independent. Contact: welt.management.solutions@gmail.com · site: https://evals.finance ·
ORCID 0009-0003-7594-4671

## Abstract
Paste the Abstract section of `paper/etf-overnight-reference-value-v1.md` word for word (a verbatim copy is at
the end of this file; the paper and the SSRN page must match). Append, as the last line of the abstract field:

    Fourth report in the TieOutBench series (the suite report, DOI 10.2139/ssrn.7243025; the checker report,
    DOI 10.2139/ssrn.7611299; the options-redemption report, DOI 10.2139/ssrn.7655899). The code, the result
    files behind every table and a script that checks the tables against them:
    https://github.com/DimaMerc/TieOutBench (prototypes/overnight/).

## Keywords
exchange-traded funds; ETFs; overnight trading; extended trading hours; 23x5 trading; premium and discount;
net asset value; indicative value; market microstructure; price bands; market makers; quoting obligations;
Xetra; Designated Sponsors; large language models; LLM evaluation; AI in finance

## JEL classification (suggested)
- G14 (Information and Market Efficiency; Event Studies; Insider Trading) — where prices trade against value
- G23 (Non-bank Financial Institutions; Financial Instruments; Institutional Investors) — ETFs
- G15 (International Financial Markets) — the foreign funds and the Frankfurt control
- G28 (Financial Institutions and Services: Government Policy and Regulation) — Rule 6c-11, the overnight price
  bands, the exchanges' rule filings
- C58 (Financial Econometrics) — the reference value and its bands
- C88 (Other Computer Software) — the runnable prototype

## SSRN network / category
This report is about a market, not a bank process, so the first choice differs from the earlier three.
Primary, if the picker offers it: Capital Markets: Market Microstructure eJournal.
Cross-list, as offered: Mutual Funds, Hedge Funds & Investment Industry eJournal; Banking & Financial
Institutions eJournal (where the first three reports sit, so the series stays in one feed); any "Artificial
Intelligence", "Generative AI" or "Financial Technology" eJournal.
If the microstructure eJournal is not offered, keep Banking & Financial Institutions as primary, as before.

## Notes for the form
- Content Type: **Preprint** (as for the last two reports: a working paper not submitted to a journal; never
  "Other").
- ORCID iD connected to the SSRN profile: 0009-0003-7594-4671 (the three earlier reports are listed under
  Works; Crossref's auto-update will add this one when its DOI is assigned).
- "Date written": November 10, 2026.
- Reference URL field: https://evals.finance
- Generative AI: the paper carries a "Declaration on the use of generative AI" section. If the form has an
  AI-use question, answer yes and paste that section's first sentence:

      A generative AI assistant (Anthropic's Claude) was used throughout this work: to draft and refine the
      prototype code and this text, and to act as the news-reading and hedge-proposing models of Findings 6
      and 7, alongside two open-weight models run locally.

- Related papers: link the three earlier abstract pages (7243025, 7611299, 7655899) if the field is offered.
- Funding, if asked: self-funded, as for the earlier reports.
- Declaration of interest, if asked. A draft to confirm before pasting, because only you know whether it is
  complete: "The author has no financial relationship with any exchange, trading venue, data vendor, fund
  issuer or model developer named in the report, other than as a paying subscriber to the data and model
  services used." If you hold any of the ten funds and consider that relevant, add a sentence saying so.
- The paper carries the not-advice note in its front matter; nothing further is needed on the SSRN page.
- Dataset: the Mendeley snapshot (10.17632/m5wfrnhdsp) predates `prototypes/overnight/`; as for the last two
  reports, the abstract's last line cites the GitHub repository. The overnight bars are licensed data and
  are not in the repository; the paper's Section 10 says what a reader can regenerate.
- If a reviewer asks about data: every market price is from a public or subscription feed, NAVs and holdings
  are the issuers' own files, and Appendix A maps each figure to its source; Appendix B lists what was not
  verified.

## Submission checklist
1. [x] Commit and push (`prototypes/overnight`, `paper/etf-overnight-reference-value-v1.md`,
       `paper/build_overnight.py`), so the repository the paper points to contains the code and result files.
2. [ ] Build: `python paper/build_overnight.py` (docx for review, pdf for upload); read the PDF once end to end.
3. [ ] Upload the PDF.
4. [ ] Paste title, abstract (+ the series line), keywords, JEL codes.
5. [ ] Classify: Market Microstructure if offered, plus the cross-lists.
6. [ ] After acceptance: capture the abstract ID (and later the DOI); fill the front-matter placeholder and
       rebuild; add to docs/index.html, a page docs/overnight-paper.html with its preview image, README.md,
       the LinkedIn Publications section and a Featured card; then publish the driver post
       (`content/linkedin-post-overnight-paste.txt`, image `assets/post-overnight-windows.png`) with the SSRN
       link in its first comment.

## Abstract (verbatim copy, generated from the paper on 2026-11-15, version 1.1; 472 words)

On December 6, 2026 five US exchanges are due to begin trading 23 hours a day. Exchange-traded funds already make up most of the small overnight market that exists today, and in those hours the arbitrage that keeps an ETF's price at the value of its holdings does not operate: a creation or redemption placed at night is an order for the next day's net asset value, no indicative value is required, and the only reference the exchanges will supply is a static band 20% either side of the close. This report measures how far prices move from that value in those hours, before the market changes. For ten US ETFs over sixty nights, every five-minute bar of overnight trading on Blue Ocean, the main overnight venue, was compared with a reference value built from the instruments that do trade through the night: index, Treasury and gold futures, bitcoin, and the yen and euro. The liquid funds trade at that value already, the S&P 500 fund within a median 2.4 basis points in every hour of the night, with no creation window open. The funds holding foreign stocks and corporate bonds mostly do not trade: in one five-minute slot in two hundred for Germany and one in eighteen for emerging markets. When the foreign funds do trade, the prints are forty to sixty basis points from the reference, and the evidence indicates that the reference is at fault, not the prints: the deviations predict the next morning's open, and for emerging markets more than two fifths of the distance disappears once the Asian sessions, which a futures-only reference ignores, are added. A reference value with two calibrated bands was built and tested out of sample. The band for where a fund will open covers at close to the promised rate. The band for where it should trade now is about ten times tighter for the liquid funds and holds only while volatility stays where it was calibrated. Four language models reading the night's news for the funds' holdings added no information beyond futures and the tape. A model choosing a fund's hedge instruments, scored on a held-out test, improved the fit for Germany and for investment-grade credit, and its emerging-markets proposal looked wrong only until the author's own measurement of it was corrected. A Frankfurt control, nine Xetra-listed funds on US indices priced every morning while New York is closed, trades within two to six basis points of futures-implied value on every listing, including listings that trade in a third of the quarter-hours. A closed underlying does not move prices away from value where a futures hedge trades. What the thin US funds lack at night is trading, and whether quoting obligations of the kind Frankfurt has would supply it is a question this data cannot answer and the December sessions may.
