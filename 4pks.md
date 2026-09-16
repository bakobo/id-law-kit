# fetch_formex splits an instrument across body and annex_bodies, and a caller reading body alone silently stores a truncated instrument: 7,772 words of 32021D0914 go missing with no error at any layer. Fixing it is an API decision (a loud refusal on a multi-member archive, or removing the truncating attribute) that breaks eu-data-law and eidas-eudi until they are updated, so it is not taken in the same round as the furniture fixes. lawcorpus.textloss.compare is the instrument that makes it visible today: compare the concatenated members against the stored text. this.i @sqxbhlk2
kind: todo
created: 2026-09-16T23:12Z

