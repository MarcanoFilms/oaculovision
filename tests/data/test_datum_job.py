"""Tests for DATUM job/template parsing."""

from __future__ import annotations

from oraculovision.data.datum import _count_coinbaser_outputs, parse_datum_job

_JOB_HTML = """
<table>
  <tr><td class="label">Job ID:</td><td>abc123 (7) @ 1710000000.000</td></tr>
  <tr><td class="label">Block Height:</td><td>900200</td></tr>
  <tr><td class="label">Block Value:</td><td>0.12500000 BTC</td></tr>
  <tr><td class="label">Previous Block:</td><td>00000000000000000000deadbeef</td></tr>
  <tr><td class="label">Block Target:</td><td>0000000000000000001a000000</td></tr>
  <tr><td class="label">Witness Commitment:</td><td>aa51</td></tr>
  <tr><td class="label">Block Difficulty:</td><td>95000000000000.000</td></tr>
  <tr><td class="label">Version:</td><td>536870912 (0x20000000)</td></tr>
  <tr><td class="label">Bits:</td><td>1a05cdbd</td></tr>
  <tr><td class="label">Time:</td><td>Current: 1710000100 / Min: 1709999000</td></tr>
  <tr><td class="label">Limits:</td><td>Size: 4000000, Weight: 4000000, SigOps: 80000</td></tr>
  <tr><td class="label">Size:</td><td>1200000</td></tr>
  <tr><td class="label">Weight:</td><td>3990000</td></tr>
  <tr><td class="label">Sigops:</td><td>1200</td></tr>
  <tr><td class="label">Txn Count:</td><td>2847</td></tr>
</table>
"""

_COINBASER_HTML = """
<TABLE>
<TR><TD><U>Value</U></TD><TD><U>Address</U></TD></TR>
<TR><TD>0.10000000 BTC</TD><TD>bc1qexample1</TD></TR>
<TR><TD>0.02500000 BTC</TD><TD>bc1qexample2</TD></TR>
</TABLE>
"""


def test_parse_datum_job_from_homepage_html() -> None:
    job = parse_datum_job(_JOB_HTML)
    assert job.available
    assert "abc123" in job.job_id
    assert job.height == "900200"
    assert job.coinbase_value_btc == "0.12500000 BTC"
    assert job.tx_count == "2847"
    assert job.weight == "3990000"


def test_count_coinbaser_outputs() -> None:
    assert _count_coinbaser_outputs(_COINBASER_HTML) == 2
    assert _count_coinbaser_outputs("") == 0