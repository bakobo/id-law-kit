# The @k76mmqlc watermark guard was never run against the PDF that motivated it: aadhaar measured 140 glyph-only lines against 0, but the page-share test and the 1-2 ASCII letter shape are derived from that description rather than fitted to the file. Re-measure against India Code's 2021 Regulations and the 2013 foreign-CA Regulation before trusting the threshold
kind: todo
created: 2026-09-16T21:54Z
closed: 2026-09-16T22:21Z

- 2026-09-16T22:20Z Measured against the real PDFs (this.i @uf4epdvm). The guard fires on the motivating document — AOV-REGS-2021 at 0.966 against a bar of 0.50, and the harm reproduces: 'publication in the Official Gazette' is 1 hit in raw mode and 0 in layout. But it does not separate. PUTTASWAMY-2018-SCR, sound and stored, scores 0.998 on a law report's A-H margin column, above every watermarked document; two watermarked Gazette PDFs score exactly 0.500 and escape. Control max 0.998 > positive min 0.500, so no threshold works. aadhaar/tools/harvest.py:507 extracts judgments on the default layout path, so the next harvest would have refused the Supreme Court Reports. extract's verify_order now defaults to False.
